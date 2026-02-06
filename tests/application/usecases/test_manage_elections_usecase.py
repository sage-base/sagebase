"""ManageElectionsUseCaseのテスト."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dtos.election_dto import (
    ElectionOutputItem,
    GenerateSeedFileOutputDto,
    ListElectionsOutputDto,
)
from src.application.usecases.manage_elections_usecase import ManageElectionsUseCase
from src.domain.entities import Election
from src.domain.services.interfaces.seed_generator_service import SeedFileResult


class TestListElections:
    """list_electionsメソッドのテスト."""

    @pytest.fixture
    def mock_election_repository(self):
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_election_repository):
        return ManageElectionsUseCase(
            election_repository=mock_election_repository,
        )

    @pytest.mark.asyncio
    async def test_list_elections_success(self, use_case, mock_election_repository):
        """開催主体IDで選挙一覧を取得し、ElectionOutputItemに変換されることを確認."""
        elections = [
            Election(
                id=1,
                governing_body_id=88,
                term_number=21,
                election_date=date(2023, 4, 9),
                election_type="統一地方選挙",
            ),
            Election(
                id=2,
                governing_body_id=88,
                term_number=20,
                election_date=date(2019, 4, 7),
                election_type=None,
            ),
        ]
        mock_election_repository.get_by_governing_body.return_value = elections

        from src.application.dtos.election_dto import ListElectionsInputDto

        result = await use_case.list_elections(
            ListElectionsInputDto(governing_body_id=88)
        )

        assert isinstance(result, ListElectionsOutputDto)
        assert result.success is True
        assert len(result.elections) == 2
        assert isinstance(result.elections[0], ElectionOutputItem)
        assert result.elections[0].id == 1
        assert result.elections[0].term_number == 21
        assert result.elections[1].election_type is None

    @pytest.mark.asyncio
    async def test_list_elections_empty(self, use_case, mock_election_repository):
        """選挙が存在しない場合に空リストを返すことを確認."""
        mock_election_repository.get_by_governing_body.return_value = []

        from src.application.dtos.election_dto import ListElectionsInputDto

        result = await use_case.list_elections(
            ListElectionsInputDto(governing_body_id=99)
        )

        assert result.success is True
        assert result.elections == []

    @pytest.mark.asyncio
    async def test_list_elections_error(self, use_case, mock_election_repository):
        """例外発生時にsuccess=Falseとerror_messageを返すことを確認."""
        mock_election_repository.get_by_governing_body.side_effect = RuntimeError(
            "DB error"
        )

        from src.application.dtos.election_dto import ListElectionsInputDto

        result = await use_case.list_elections(
            ListElectionsInputDto(governing_body_id=88)
        )

        assert result.success is False
        assert result.elections == []
        assert "DB error" in (result.error_message or "")


class TestListAllElections:
    """list_all_electionsメソッドのテスト."""

    @pytest.fixture
    def mock_election_repository(self):
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_election_repository):
        return ManageElectionsUseCase(
            election_repository=mock_election_repository,
        )

    @pytest.mark.asyncio
    async def test_list_all_elections_success(self, use_case, mock_election_repository):
        """全選挙一覧を取得し、ElectionOutputItemに変換されることを確認."""
        elections = [
            Election(
                id=1,
                governing_body_id=88,
                term_number=21,
                election_date=date(2023, 4, 9),
                election_type="統一地方選挙",
            ),
        ]
        mock_election_repository.get_all.return_value = elections

        result = await use_case.list_all_elections()

        assert isinstance(result, ListElectionsOutputDto)
        assert result.success is True
        assert len(result.elections) == 1
        assert isinstance(result.elections[0], ElectionOutputItem)
        assert result.elections[0].governing_body_id == 88

    @pytest.mark.asyncio
    async def test_list_all_elections_empty(self, use_case, mock_election_repository):
        """選挙が存在しない場合に空リストを返すことを確認."""
        mock_election_repository.get_all.return_value = []

        result = await use_case.list_all_elections()

        assert result.success is True
        assert result.elections == []

    @pytest.mark.asyncio
    async def test_list_all_elections_error(self, use_case, mock_election_repository):
        """例外発生時にsuccess=Falseとerror_messageを返すことを確認."""
        mock_election_repository.get_all.side_effect = RuntimeError("Connection lost")

        result = await use_case.list_all_elections()

        assert result.success is False
        assert result.elections == []
        assert "Connection lost" in (result.error_message or "")


class TestGenerateSeedFile:
    """generate_seed_fileメソッドのテスト."""

    @pytest.fixture
    def mock_election_repository(self):
        return AsyncMock()

    @pytest.fixture
    def mock_seed_generator_service(self):
        service = MagicMock()
        service.generate_and_save_elections_seed.return_value = SeedFileResult(
            content="INSERT INTO elections (id) VALUES (1);",
            file_path="database/seed_elections_generated.sql",
        )
        return service

    @pytest.fixture
    def use_case(self, mock_election_repository, mock_seed_generator_service):
        return ManageElectionsUseCase(
            election_repository=mock_election_repository,
            seed_generator_service=mock_seed_generator_service,
        )

    @pytest.mark.asyncio
    async def test_generate_seed_file_success(
        self, use_case, mock_seed_generator_service
    ):
        result = await use_case.generate_seed_file()

        assert isinstance(result, GenerateSeedFileOutputDto)
        assert result.success is True
        assert result.seed_content == "INSERT INTO elections (id) VALUES (1);"
        assert result.file_path == "database/seed_elections_generated.sql"
        mock_seed_generator_service.generate_and_save_elections_seed.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_seed_file_error(
        self, use_case, mock_seed_generator_service
    ):
        mock_seed_generator_service.generate_and_save_elections_seed.side_effect = (
            RuntimeError("DB connection failed")
        )

        result = await use_case.generate_seed_file()

        assert isinstance(result, GenerateSeedFileOutputDto)
        assert result.success is False
        assert "DB connection failed" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_generate_seed_file_without_service(self, mock_election_repository):
        use_case = ManageElectionsUseCase(
            election_repository=mock_election_repository,
        )

        result = await use_case.generate_seed_file()

        assert result.success is False
        assert "設定されていません" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_generate_seed_file_write_error(
        self, use_case, mock_seed_generator_service
    ):
        mock_seed_generator_service.generate_and_save_elections_seed.side_effect = (
            OSError("Permission denied")
        )

        result = await use_case.generate_seed_file()

        assert isinstance(result, GenerateSeedFileOutputDto)
        assert result.success is False
        assert "Permission denied" in (result.error_message or "")
