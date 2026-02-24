"""ImportSangiinGianUseCaseのテスト."""

import json
import tempfile

from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.smartnews_smri_import_dto import (
    ImportSmartNewsSmriInputDto,
)
from src.application.usecases.import_sangiin_gian_usecase import (
    ImportSangiinGianUseCase,
)
from src.domain.entities.proposal import Proposal
from src.domain.repositories.proposal_repository import ProposalRepository
from src.domain.repositories.proposal_submitter_repository import (
    ProposalSubmitterRepository,
)


def _make_sangiin_row(
    session_number: str = "153",
    proposal_type: str = "法律案（内閣提出）",
    proposal_number: str = "1",
    title: str = "テスト法案",
    gian_url: str = "https://www.sangiin.go.jp/gian/153/001.htm",
    submitted_date: str = "2001-09-28",
    plenary_vote_date: str = "2001-11-09",
    plenary_result: str = "可決",
    submitter: str = "",
    submitter_type: str = "",
    initiator: str = "",
) -> list[Any]:
    """テスト用参議院gian.jsonデータ行を作成する."""
    return [
        session_number,  # 0: 審議回次
        proposal_type,  # 1: 種類
        session_number,  # 2: 提出回次
        proposal_number,  # 3: 提出番号
        title,  # 4: 件名
        gian_url,  # 5: 議案URL
        "",  # 6: 議案要旨
        "",  # 7: 提出法律案
        submitted_date,  # 8: 提出日
        "",  # 9: 衆議院から受領日
        "",  # 10: 衆議院へ送付日
        "",  # 11: 先議区分
        "",  # 12: 継続区分
        initiator,  # 13: 発議者
        submitter,  # 14: 提出者
        submitter_type,  # 15: 提出者区分
        "",  # 16-19: 参議院委員会経過
        "",
        "",
        "",
        plenary_vote_date,  # 20: 参議院本会議議決日
        plenary_result,  # 21: 参議院本会議議決
        "",  # 22-25: 参議院本会議残りフィールド
        "",
        "",
        "",
        "",  # 26-34: 衆議院経過
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",  # 35-38: その他情報
        "",
        "",
        "",
    ]


# ヘッダー行
_HEADER = ["審議回次", "種類", "提出回次", "提出番号", "件名"] + [""] * 34


def _write_json(records: list[list[Any]]) -> Path:
    """ヘッダー行 + データ行をJSONファイルに書き込む."""
    data = [_HEADER] + records
    f = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
        encoding="utf-8",
    )
    json.dump(data, f, ensure_ascii=False)
    f.flush()
    f.close()
    return Path(f.name)


class TestImportSangiinGianUseCase:
    @pytest.fixture
    def mock_repo(self) -> AsyncMock:
        repo = AsyncMock(spec=ProposalRepository)
        repo.find_by_identifier = AsyncMock(return_value=None)
        repo.find_by_url = AsyncMock(return_value=None)
        repo.create = AsyncMock(side_effect=lambda p: Proposal(title=p.title, id=1))
        return repo

    @pytest.fixture
    def mock_submitter_repo(self) -> AsyncMock:
        repo = AsyncMock(spec=ProposalSubmitterRepository)
        repo.bulk_create = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def use_case(
        self, mock_repo: AsyncMock, mock_submitter_repo: AsyncMock
    ) -> ImportSangiinGianUseCase:
        return ImportSangiinGianUseCase(
            proposal_repository=mock_repo,
            proposal_submitter_repository=mock_submitter_repo,
        )

    @pytest.mark.asyncio
    async def test_execute_creates_proposals(
        self,
        use_case: ImportSangiinGianUseCase,
        mock_repo: AsyncMock,
    ) -> None:
        records = [
            _make_sangiin_row(),
            _make_sangiin_row(title="法案2", proposal_number="2"),
        ]
        file_path = _write_json(records)

        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=1,
            conference_id=10,
        )
        result = await use_case.execute(input_dto)

        assert result.total == 2
        assert result.created == 2
        assert result.skipped == 0
        assert result.errors == 0

    @pytest.mark.asyncio
    async def test_execute_skips_duplicates(
        self,
        use_case: ImportSangiinGianUseCase,
        mock_repo: AsyncMock,
    ) -> None:
        mock_repo.find_by_identifier = AsyncMock(
            return_value=Proposal(title="既存法案", id=99)
        )
        records = [_make_sangiin_row()]
        file_path = _write_json(records)

        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=1,
            conference_id=10,
        )
        result = await use_case.execute(input_dto)

        assert result.total == 1
        assert result.created == 0
        assert result.skipped == 1

    @pytest.mark.asyncio
    async def test_execute_creates_submitters(
        self,
        use_case: ImportSangiinGianUseCase,
        mock_repo: AsyncMock,
        mock_submitter_repo: AsyncMock,
    ) -> None:
        records = [
            _make_sangiin_row(submitter="山田太郎", submitter_type="議員"),
        ]
        file_path = _write_json(records)

        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=1,
            conference_id=10,
        )
        result = await use_case.execute(input_dto)

        assert result.created == 1
        assert result.submitters_created == 1
        mock_submitter_repo.bulk_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_backfill_dates(
        self,
        use_case: ImportSangiinGianUseCase,
        mock_repo: AsyncMock,
    ) -> None:
        existing = Proposal(
            title="既存法案",
            id=99,
            submitted_date=None,
            voted_date=None,
        )
        mock_repo.find_by_identifier = AsyncMock(return_value=existing)

        records = [
            _make_sangiin_row(
                submitted_date="2001-09-28",
                plenary_vote_date="2001-11-09",
            ),
        ]
        file_path = _write_json(records)

        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=1,
            conference_id=10,
        )
        result = await use_case.execute(input_dto)

        assert result.skipped == 1
        assert result.updated == 1
        mock_repo.update.assert_called_once()
        assert existing.submitted_date == date(2001, 9, 28)
        assert existing.voted_date == date(2001, 11, 9)

    @pytest.mark.asyncio
    async def test_execute_handles_errors(
        self,
        use_case: ImportSangiinGianUseCase,
        mock_repo: AsyncMock,
    ) -> None:
        mock_repo.create = AsyncMock(side_effect=RuntimeError("DB error"))
        records = [_make_sangiin_row()]
        file_path = _write_json(records)

        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=1,
            conference_id=10,
        )
        result = await use_case.execute(input_dto)

        assert result.total == 1
        assert result.errors == 1
        assert result.created == 0

    @pytest.mark.asyncio
    async def test_execute_without_submitter_repo(
        self,
        mock_repo: AsyncMock,
    ) -> None:
        """提出者リポジトリなしでも正常動作することを確認."""
        use_case = ImportSangiinGianUseCase(
            proposal_repository=mock_repo,
            proposal_submitter_repository=None,
        )
        records = [
            _make_sangiin_row(submitter="山田太郎", submitter_type="議員"),
        ]
        file_path = _write_json(records)

        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=1,
            conference_id=10,
        )
        result = await use_case.execute(input_dto)

        assert result.created == 1
        assert result.submitters_created == 0
