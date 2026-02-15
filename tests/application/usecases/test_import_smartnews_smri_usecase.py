import json
import tempfile

from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from tests.fixtures.smri_record_factories import make_smri_record_with_judges

from src.application.dtos.smartnews_smri_import_dto import (
    ImportSmartNewsSmriInputDto,
    ImportSmartNewsSmriOutputDto,
)
from src.application.usecases.import_smartnews_smri_usecase import (
    ImportSmartNewsSmriUseCase,
)
from src.domain.entities.proposal import Proposal
from src.domain.repositories.extracted_proposal_judge_repository import (
    ExtractedProposalJudgeRepository,
)
from src.domain.repositories.proposal_repository import ProposalRepository


def _make_record(
    proposal_type: str = "衆法",
    session_number: str = "200",
    proposal_number: str = "42",
    title: str = "テスト法案",
    result: str = "成立",
    url: str = "https://www.shugiin.go.jp/keika/TEST.htm",
    submitted_date: str = "",
    voted_date: str = "",
) -> list[Any]:
    nested_row = [
        "200",  # 0
        result,  # 1
        "経過",  # 2
        url,  # 3
        "",  # 4
        "",  # 5
        proposal_type,  # 6
        "",  # 7
        "",  # 8
        submitted_date,  # 9 (_IDX_NESTED_SUBMITTED_DATE)
        "",  # 10
        "",  # 11
        voted_date,  # 12 (_IDX_NESTED_VOTED_DATE)
        *[""] * 10,  # 13-22
    ]
    return [
        proposal_type,
        session_number,
        proposal_number,
        title,
        "200",
        result,
        "",
        "",
        "",
        "",
        [nested_row],
    ]


def _write_json(records: list[list[Any]]) -> Path:
    f = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
        encoding="utf-8",
    )
    json.dump(records, f, ensure_ascii=False)
    f.flush()
    f.close()
    return Path(f.name)


class TestImportSmartNewsSmriUseCase:
    @pytest.fixture
    def mock_repo(self) -> AsyncMock:
        repo = AsyncMock(spec=ProposalRepository)
        repo.find_by_identifier = AsyncMock(return_value=None)
        repo.find_by_url = AsyncMock(return_value=None)
        repo.create = AsyncMock(side_effect=lambda p: Proposal(title=p.title, id=1))
        return repo

    @pytest.fixture
    def use_case(self, mock_repo: AsyncMock) -> ImportSmartNewsSmriUseCase:
        return ImportSmartNewsSmriUseCase(
            proposal_repository=mock_repo,
        )

    @pytest.mark.asyncio
    async def test_execute_creates_proposals(
        self,
        use_case: ImportSmartNewsSmriUseCase,
        mock_repo: AsyncMock,
    ) -> None:
        records = [
            _make_record(),
            _make_record(title="法案2"),
        ]
        file_path = _write_json(records)

        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=1,
            conference_id=10,
            batch_size=10,
        )
        result = await use_case.execute(input_dto)

        assert result.total == 2
        assert result.created == 2
        assert result.skipped == 0
        assert result.errors == 0
        assert mock_repo.create.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_skips_duplicates_by_identifier(
        self,
        use_case: ImportSmartNewsSmriUseCase,
        mock_repo: AsyncMock,
    ) -> None:
        existing = Proposal(title="既存", id=99)
        mock_repo.find_by_identifier.return_value = existing

        file_path = _write_json([_make_record()])
        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=1,
            conference_id=10,
        )
        result = await use_case.execute(input_dto)

        assert result.skipped == 1
        assert result.created == 0
        mock_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_skips_duplicates_by_url(
        self,
        use_case: ImportSmartNewsSmriUseCase,
        mock_repo: AsyncMock,
    ) -> None:
        existing = Proposal(title="既存", id=99)
        mock_repo.find_by_url.return_value = existing

        record = _make_record(proposal_number="")
        file_path = _write_json([record])
        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=1,
            conference_id=10,
        )
        result = await use_case.execute(input_dto)

        assert result.skipped == 1
        assert result.created == 0

    @pytest.mark.asyncio
    async def test_execute_no_key_no_external_id_always_creates(
        self,
        use_case: ImportSmartNewsSmriUseCase,
        mock_repo: AsyncMock,
    ) -> None:
        record = _make_record(proposal_type="予算", proposal_number="", url="")
        file_path = _write_json([record, record])
        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=1,
            conference_id=10,
        )
        result = await use_case.execute(input_dto)

        assert result.created == 2
        assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_execute_handles_errors(
        self,
        use_case: ImportSmartNewsSmriUseCase,
        mock_repo: AsyncMock,
    ) -> None:
        mock_repo.create.side_effect = Exception("DB error")

        file_path = _write_json([_make_record()])
        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=1,
            conference_id=10,
        )
        result = await use_case.execute(input_dto)

        assert result.errors == 1
        assert result.created == 0

    @pytest.mark.asyncio
    async def test_execute_batch_processing(
        self,
        use_case: ImportSmartNewsSmriUseCase,
        mock_repo: AsyncMock,
    ) -> None:
        records = [_make_record(title=f"法案{i}") for i in range(5)]
        file_path = _write_json(records)
        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=1,
            conference_id=10,
            batch_size=2,
        )
        result = await use_case.execute(input_dto)

        assert result.total == 5
        assert result.created == 5

    @pytest.mark.asyncio
    async def test_execute_empty_records(
        self,
        use_case: ImportSmartNewsSmriUseCase,
    ) -> None:
        file_path = _write_json([])
        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=1,
            conference_id=10,
        )
        result = await use_case.execute(input_dto)

        assert result.total == 0
        assert result.created == 0


class TestImportSmartNewsSmriBackfill:
    """日付バックフィルのテストケース."""

    @pytest.fixture
    def mock_repo(self) -> AsyncMock:
        repo = AsyncMock(spec=ProposalRepository)
        repo.find_by_identifier = AsyncMock(return_value=None)
        repo.find_by_url = AsyncMock(return_value=None)
        repo.create = AsyncMock(side_effect=lambda p: Proposal(title=p.title, id=1))
        repo.update = AsyncMock(side_effect=lambda p: p)
        return repo

    @pytest.mark.asyncio
    async def test_backfill_dates_on_duplicate(
        self,
        mock_repo: AsyncMock,
    ) -> None:
        """既存レコードの日付がNULL→新データの日付で更新."""
        existing = Proposal(
            title="既存",
            id=99,
            governing_body_id=1,
            session_number=200,
            proposal_number=42,
            proposal_type="衆法",
            submitted_date=None,
            voted_date=None,
        )
        mock_repo.find_by_identifier.return_value = existing

        record = _make_record(
            submitted_date="平成10年 1月12日",
            voted_date="平成10年 3月19日",
        )
        file_path = _write_json([record])
        use_case = ImportSmartNewsSmriUseCase(proposal_repository=mock_repo)
        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=1,
            conference_id=10,
        )
        result = await use_case.execute(input_dto)

        assert result.skipped == 1
        assert result.updated == 1
        assert result.created == 0
        mock_repo.update.assert_called_once()
        updated_proposal = mock_repo.update.call_args[0][0]
        assert updated_proposal.submitted_date == date(1998, 1, 12)
        assert updated_proposal.voted_date == date(1998, 3, 19)

    @pytest.mark.asyncio
    async def test_no_backfill_when_existing_has_dates(
        self,
        mock_repo: AsyncMock,
    ) -> None:
        """既存レコードに日付あり→更新しない."""
        existing = Proposal(
            title="既存",
            id=99,
            governing_body_id=1,
            session_number=200,
            proposal_number=42,
            proposal_type="衆法",
            submitted_date=date(1998, 1, 1),
            voted_date=date(1998, 3, 1),
        )
        mock_repo.find_by_identifier.return_value = existing

        record = _make_record(
            submitted_date="平成10年 1月12日",
            voted_date="平成10年 3月19日",
        )
        file_path = _write_json([record])
        use_case = ImportSmartNewsSmriUseCase(proposal_repository=mock_repo)
        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=1,
            conference_id=10,
        )
        result = await use_case.execute(input_dto)

        assert result.skipped == 1
        assert result.updated == 0
        mock_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_backfill_when_new_data_has_no_dates(
        self,
        mock_repo: AsyncMock,
    ) -> None:
        """新データに日付なし→更新しない."""
        existing = Proposal(
            title="既存",
            id=99,
            governing_body_id=1,
            session_number=200,
            proposal_number=42,
            proposal_type="衆法",
            submitted_date=None,
            voted_date=None,
        )
        mock_repo.find_by_identifier.return_value = existing

        record = _make_record()
        file_path = _write_json([record])
        use_case = ImportSmartNewsSmriUseCase(proposal_repository=mock_repo)
        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=1,
            conference_id=10,
        )
        result = await use_case.execute(input_dto)

        assert result.skipped == 1
        assert result.updated == 0
        mock_repo.update.assert_not_called()


class TestImportSmartNewsSmriDtos:
    def test_input_dto_defaults(self) -> None:
        dto = ImportSmartNewsSmriInputDto(
            file_path=Path("/tmp/test.json"),
            governing_body_id=1,
            conference_id=10,
        )
        assert dto.batch_size == 100

    def test_output_dto_defaults(self) -> None:
        dto = ImportSmartNewsSmriOutputDto()
        assert dto.total == 0
        assert dto.created == 0
        assert dto.skipped == 0
        assert dto.updated == 0
        assert dto.errors == 0
        assert dto.judges_created == 0


class TestImportSmartNewsSmriUseCaseWithJudges:
    @pytest.fixture
    def mock_repo(self) -> AsyncMock:
        repo = AsyncMock(spec=ProposalRepository)
        repo.find_by_identifier = AsyncMock(return_value=None)
        repo.find_by_url = AsyncMock(return_value=None)
        repo.create = AsyncMock(side_effect=lambda p: Proposal(title=p.title, id=42))
        return repo

    @pytest.fixture
    def mock_judge_repo(self) -> AsyncMock:
        repo = AsyncMock(spec=ExtractedProposalJudgeRepository)
        repo.bulk_create = AsyncMock(return_value=[])
        return repo

    @pytest.mark.asyncio
    async def test_creates_judges_with_repo(
        self,
        mock_repo: AsyncMock,
        mock_judge_repo: AsyncMock,
    ) -> None:
        use_case = ImportSmartNewsSmriUseCase(
            proposal_repository=mock_repo,
            extracted_proposal_judge_repository=mock_judge_repo,
        )
        records = [make_smri_record_with_judges(sansei="自民党;公明党", hantai="立憲")]
        file_path = _write_json(records)
        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path, governing_body_id=1, conference_id=10
        )
        result = await use_case.execute(input_dto)

        assert result.created == 1
        assert result.judges_created == 3
        mock_judge_repo.bulk_create.assert_called_once()
        judges = mock_judge_repo.bulk_create.call_args[0][0]
        assert len(judges) == 3

    @pytest.mark.asyncio
    async def test_backward_compat_without_judge_repo(
        self,
        mock_repo: AsyncMock,
    ) -> None:
        use_case = ImportSmartNewsSmriUseCase(
            proposal_repository=mock_repo,
        )
        records = [make_smri_record_with_judges(sansei="自民党")]
        file_path = _write_json(records)
        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path, governing_body_id=1, conference_id=10
        )
        result = await use_case.execute(input_dto)

        assert result.created == 1
        assert result.judges_created == 0

    @pytest.mark.asyncio
    async def test_judge_error_does_not_block_proposal_import(
        self,
        mock_repo: AsyncMock,
        mock_judge_repo: AsyncMock,
    ) -> None:
        mock_judge_repo.bulk_create.side_effect = Exception("DB error")
        use_case = ImportSmartNewsSmriUseCase(
            proposal_repository=mock_repo,
            extracted_proposal_judge_repository=mock_judge_repo,
        )
        records = [make_smri_record_with_judges(sansei="自民党")]
        file_path = _write_json(records)
        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path, governing_body_id=1, conference_id=10
        )
        result = await use_case.execute(input_dto)

        assert result.created == 1
        assert result.judges_created == 0
