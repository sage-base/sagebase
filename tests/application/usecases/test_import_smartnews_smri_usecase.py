import json
import tempfile

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.smartnews_smri_import_dto import (
    ImportSmartNewsSmriInputDto,
    ImportSmartNewsSmriOutputDto,
)
from src.application.usecases.import_smartnews_smri_usecase import (
    ImportSmartNewsSmriUseCase,
)
from src.domain.entities.proposal import Proposal
from src.domain.repositories.proposal_repository import ProposalRepository


def _make_record(
    proposal_type: str = "衆法",
    session_number: str = "200",
    proposal_number: str = "42",
    title: str = "テスト法案",
    result: str = "成立",
    url: str = "https://www.shugiin.go.jp/keika/TEST.htm",
) -> list[Any]:
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
        [["200", result, "経過", url, "", "", proposal_type, *[""] * 16]],
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
        )
        result = await use_case.execute(input_dto)

        assert result.total == 0
        assert result.created == 0


class TestImportSmartNewsSmriDtos:
    def test_input_dto_defaults(self) -> None:
        dto = ImportSmartNewsSmriInputDto(
            file_path=Path("/tmp/test.json"),
            governing_body_id=1,
        )
        assert dto.batch_size == 100

    def test_output_dto_defaults(self) -> None:
        dto = ImportSmartNewsSmriOutputDto()
        assert dto.total == 0
        assert dto.created == 0
        assert dto.skipped == 0
        assert dto.errors == 0
