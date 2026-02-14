"""Tests for ManageElectionMembersUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dtos.election_dto import GenerateSeedFileOutputDto
from src.application.dtos.election_member_dto import (
    CreateElectionMemberInputDto,
    DeleteElectionMemberInputDto,
    ListElectionMembersByElectionInputDto,
    ListElectionMembersByPoliticianInputDto,
    UpdateElectionMemberInputDto,
)
from src.application.usecases.manage_election_members_usecase import (
    ManageElectionMembersUseCase,
)
from src.domain.entities.election_member import ElectionMember
from src.domain.repositories.election_member_repository import ElectionMemberRepository
from src.domain.services.interfaces.seed_generator_service import SeedFileResult


class TestManageElectionMembersUseCase:
    """Test cases for ManageElectionMembersUseCase."""

    @pytest.fixture
    def mock_election_member_repository(self) -> MagicMock:
        """Create mock election member repository."""
        repo = MagicMock(spec=ElectionMemberRepository)
        repo.get_by_election_id = AsyncMock()
        repo.get_by_politician_id = AsyncMock()
        repo.get_by_id = AsyncMock()
        repo.create = AsyncMock()
        repo.update = AsyncMock()
        repo.delete = AsyncMock()
        return repo

    @pytest.fixture
    def use_case(
        self, mock_election_member_repository: MagicMock
    ) -> ManageElectionMembersUseCase:
        """Create use case with mock repository."""
        return ManageElectionMembersUseCase(mock_election_member_repository)

    @pytest.mark.asyncio
    async def test_list_by_election_success(
        self,
        use_case: ManageElectionMembersUseCase,
        mock_election_member_repository: MagicMock,
    ) -> None:
        """Test list_by_election returns members successfully."""
        members = [
            ElectionMember(
                id=1,
                election_id=10,
                politician_id=100,
                result="当選",
                votes=5000,
                rank=1,
            ),
        ]
        mock_election_member_repository.get_by_election_id.return_value = members

        input_dto = ListElectionMembersByElectionInputDto(election_id=10)
        result = await use_case.list_by_election(input_dto)

        assert result.success is True
        assert len(result.election_members) == 1
        assert result.election_members[0].election_id == 10
        mock_election_member_repository.get_by_election_id.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_list_by_election_error(
        self,
        use_case: ManageElectionMembersUseCase,
        mock_election_member_repository: MagicMock,
    ) -> None:
        """Test list_by_election handles errors."""
        mock_election_member_repository.get_by_election_id.side_effect = Exception(
            "DB error"
        )

        input_dto = ListElectionMembersByElectionInputDto(election_id=10)
        result = await use_case.list_by_election(input_dto)

        assert result.success is False
        assert result.error_message == "DB error"
        assert result.election_members == []

    @pytest.mark.asyncio
    async def test_list_by_politician_success(
        self,
        use_case: ManageElectionMembersUseCase,
        mock_election_member_repository: MagicMock,
    ) -> None:
        """Test list_by_politician returns results successfully."""
        members = [
            ElectionMember(
                id=1,
                election_id=10,
                politician_id=100,
                result="当選",
                votes=5000,
                rank=1,
            ),
        ]
        mock_election_member_repository.get_by_politician_id.return_value = members

        input_dto = ListElectionMembersByPoliticianInputDto(politician_id=100)
        result = await use_case.list_by_politician(input_dto)

        assert result.success is True
        assert len(result.election_members) == 1
        mock_election_member_repository.get_by_politician_id.assert_called_once_with(
            100
        )

    @pytest.mark.asyncio
    async def test_create_election_member_success(
        self,
        use_case: ManageElectionMembersUseCase,
        mock_election_member_repository: MagicMock,
    ) -> None:
        """Test create_election_member creates successfully."""
        created_member = ElectionMember(
            id=1,
            election_id=10,
            politician_id=100,
            result="当選",
            votes=5000,
            rank=1,
        )
        mock_election_member_repository.create.return_value = created_member

        input_dto = CreateElectionMemberInputDto(
            election_id=10,
            politician_id=100,
            result="当選",
            votes=5000,
            rank=1,
        )
        result = await use_case.create_election_member(input_dto)

        assert result.success is True
        assert result.election_member_id == 1
        mock_election_member_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_election_member_failure(
        self,
        use_case: ManageElectionMembersUseCase,
        mock_election_member_repository: MagicMock,
    ) -> None:
        """Test create_election_member handles errors."""
        mock_election_member_repository.create.side_effect = Exception("DB error")

        input_dto = CreateElectionMemberInputDto(
            election_id=10,
            politician_id=100,
            result="当選",
        )
        result = await use_case.create_election_member(input_dto)

        assert result.success is False
        assert result.error_message == "DB error"

    @pytest.mark.asyncio
    async def test_update_election_member_success(
        self,
        use_case: ManageElectionMembersUseCase,
        mock_election_member_repository: MagicMock,
    ) -> None:
        """Test update_election_member updates successfully."""
        existing = ElectionMember(
            id=1,
            election_id=10,
            politician_id=100,
            result="当選",
            votes=5000,
            rank=1,
        )
        mock_election_member_repository.get_by_id.return_value = existing
        mock_election_member_repository.update.return_value = existing

        input_dto = UpdateElectionMemberInputDto(
            id=1,
            election_id=10,
            politician_id=100,
            result="落選",
            votes=3000,
            rank=2,
        )
        result = await use_case.update_election_member(input_dto)

        assert result.success is True
        mock_election_member_repository.get_by_id.assert_called_once_with(1)
        mock_election_member_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_election_member_not_found(
        self,
        use_case: ManageElectionMembersUseCase,
        mock_election_member_repository: MagicMock,
    ) -> None:
        """Test update_election_member when member not found."""
        mock_election_member_repository.get_by_id.return_value = None

        input_dto = UpdateElectionMemberInputDto(
            id=999,
            election_id=10,
            politician_id=100,
            result="当選",
        )
        result = await use_case.update_election_member(input_dto)

        assert result.success is False
        assert "見つかりません" in (result.error_message or "")
        mock_election_member_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_election_member_success(
        self,
        use_case: ManageElectionMembersUseCase,
        mock_election_member_repository: MagicMock,
    ) -> None:
        """Test delete_election_member deletes successfully."""
        existing = ElectionMember(
            id=1,
            election_id=10,
            politician_id=100,
            result="当選",
        )
        mock_election_member_repository.get_by_id.return_value = existing
        mock_election_member_repository.delete.return_value = True

        input_dto = DeleteElectionMemberInputDto(id=1)
        result = await use_case.delete_election_member(input_dto)

        assert result.success is True
        mock_election_member_repository.get_by_id.assert_called_once_with(1)
        mock_election_member_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_election_member_not_found(
        self,
        use_case: ManageElectionMembersUseCase,
        mock_election_member_repository: MagicMock,
    ) -> None:
        """Test delete_election_member when member not found."""
        mock_election_member_repository.get_by_id.return_value = None

        input_dto = DeleteElectionMemberInputDto(id=999)
        result = await use_case.delete_election_member(input_dto)

        assert result.success is False
        assert "見つかりません" in (result.error_message or "")
        mock_election_member_repository.delete.assert_not_called()

    def test_get_result_options(
        self,
        use_case: ManageElectionMembersUseCase,
    ) -> None:
        """Test get_result_options returns expected options."""
        options = use_case.get_result_options()

        assert "当選" in options
        assert "落選" in options
        assert "次点" in options
        assert "繰上当選" in options
        assert "無投票当選" in options
        assert "比例当選" in options
        assert "比例復活" in options
        assert len(options) == 7

    @pytest.mark.asyncio
    async def test_list_by_politician_error(
        self,
        use_case: ManageElectionMembersUseCase,
        mock_election_member_repository: MagicMock,
    ) -> None:
        """Test list_by_politician handles errors."""
        mock_election_member_repository.get_by_politician_id.side_effect = Exception(
            "DB error"
        )

        input_dto = ListElectionMembersByPoliticianInputDto(politician_id=100)
        result = await use_case.list_by_politician(input_dto)

        assert result.success is False
        assert result.error_message == "DB error"
        assert result.election_members == []

    @pytest.mark.asyncio
    async def test_delete_election_member_delete_returns_false(
        self,
        use_case: ManageElectionMembersUseCase,
        mock_election_member_repository: MagicMock,
    ) -> None:
        """Test delete_election_member when delete returns False."""
        existing = ElectionMember(
            id=1,
            election_id=10,
            politician_id=100,
            result="当選",
        )
        mock_election_member_repository.get_by_id.return_value = existing
        mock_election_member_repository.delete.return_value = False

        input_dto = DeleteElectionMemberInputDto(id=1)
        result = await use_case.delete_election_member(input_dto)

        assert result.success is False
        assert "削除できませんでした" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_create_election_member_invalid_result(
        self,
        use_case: ManageElectionMembersUseCase,
        mock_election_member_repository: MagicMock,
    ) -> None:
        """Test create_election_member with invalid result value."""
        input_dto = CreateElectionMemberInputDto(
            election_id=10,
            politician_id=100,
            result="不正な値",
        )
        result = await use_case.create_election_member(input_dto)

        assert result.success is False
        assert "無効な選挙結果" in (result.error_message or "")
        mock_election_member_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_election_member_minimal_params(
        self,
        use_case: ManageElectionMembersUseCase,
        mock_election_member_repository: MagicMock,
    ) -> None:
        """Test create_election_member with minimal params (no votes/rank)."""
        created_member = ElectionMember(
            id=1,
            election_id=10,
            politician_id=100,
            result="当選",
        )
        mock_election_member_repository.create.return_value = created_member

        input_dto = CreateElectionMemberInputDto(
            election_id=10,
            politician_id=100,
            result="当選",
        )
        result = await use_case.create_election_member(input_dto)

        assert result.success is True
        assert result.election_member_id == 1
        mock_election_member_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_election_member_invalid_result(
        self,
        use_case: ManageElectionMembersUseCase,
        mock_election_member_repository: MagicMock,
    ) -> None:
        """Test update_election_member with invalid result value."""
        input_dto = UpdateElectionMemberInputDto(
            id=1,
            election_id=10,
            politician_id=100,
            result="不正な値",
        )
        result = await use_case.update_election_member(input_dto)

        assert result.success is False
        assert "無効な選挙結果" in (result.error_message or "")
        mock_election_member_repository.get_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_election_member_exception(
        self,
        use_case: ManageElectionMembersUseCase,
        mock_election_member_repository: MagicMock,
    ) -> None:
        """Test update_election_member handles repository exceptions."""
        mock_election_member_repository.get_by_id.side_effect = Exception("DB error")

        input_dto = UpdateElectionMemberInputDto(
            id=1,
            election_id=10,
            politician_id=100,
            result="当選",
        )
        result = await use_case.update_election_member(input_dto)

        assert result.success is False
        assert result.error_message == "DB error"

    @pytest.mark.asyncio
    async def test_delete_election_member_exception(
        self,
        use_case: ManageElectionMembersUseCase,
        mock_election_member_repository: MagicMock,
    ) -> None:
        """Test delete_election_member handles repository exceptions."""
        mock_election_member_repository.get_by_id.side_effect = Exception("DB error")

        input_dto = DeleteElectionMemberInputDto(id=1)
        result = await use_case.delete_election_member(input_dto)

        assert result.success is False
        assert result.error_message == "DB error"


class TestGenerateSeedFile:
    """generate_seed_fileメソッドのテスト."""

    @pytest.fixture
    def mock_election_member_repository(self):
        return AsyncMock()

    @pytest.fixture
    def mock_seed_generator_service(self):
        service = MagicMock()
        service.generate_and_save_election_members_seed.return_value = SeedFileResult(
            content="INSERT INTO election_members (election_id) VALUES (1);",
            file_path="database/seed_election_members_generated.sql",
        )
        return service

    @pytest.fixture
    def use_case(self, mock_election_member_repository, mock_seed_generator_service):
        return ManageElectionMembersUseCase(
            election_member_repository=mock_election_member_repository,
            seed_generator_service=mock_seed_generator_service,
        )

    @pytest.mark.asyncio
    async def test_generate_seed_file_success(
        self, use_case, mock_seed_generator_service
    ):
        """SEEDファイル生成が成功することを確認."""
        result = await use_case.generate_seed_file()

        assert isinstance(result, GenerateSeedFileOutputDto)
        assert result.success is True
        assert (
            result.seed_content
            == "INSERT INTO election_members (election_id) VALUES (1);"
        )
        assert result.file_path == "database/seed_election_members_generated.sql"
        mock_seed_generator_service.generate_and_save_election_members_seed.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_seed_file_error(
        self, use_case, mock_seed_generator_service
    ):
        """サービスがエラーを返した場合に失敗を返すことを確認."""
        mock = mock_seed_generator_service
        mock.generate_and_save_election_members_seed.side_effect = RuntimeError(
            "DB connection failed"
        )

        result = await use_case.generate_seed_file()

        assert isinstance(result, GenerateSeedFileOutputDto)
        assert result.success is False
        assert "DB connection failed" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_generate_seed_file_without_service(
        self, mock_election_member_repository
    ):
        """seed_generator_serviceがNoneの場合に失敗を返すことを確認."""
        use_case = ManageElectionMembersUseCase(
            election_member_repository=mock_election_member_repository,
        )

        result = await use_case.generate_seed_file()

        assert result.success is False
        assert "設定されていません" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_generate_seed_file_write_error(
        self, use_case, mock_seed_generator_service
    ):
        """ファイル書き込みエラー時に失敗を返すことを確認."""
        mock = mock_seed_generator_service
        mock.generate_and_save_election_members_seed.side_effect = OSError(
            "Permission denied"
        )

        result = await use_case.generate_seed_file()

        assert isinstance(result, GenerateSeedFileOutputDto)
        assert result.success is False
        assert "Permission denied" in (result.error_message or "")


class TestElectionMemberOutputItem:
    """ElectionMemberOutputItemのテスト."""

    def test_from_entity_with_all_fields(self) -> None:
        """全フィールドが正しくマッピングされることを確認."""
        from src.application.dtos.election_member_dto import (
            ElectionMemberOutputItem,
        )

        entity = ElectionMember(
            id=1,
            election_id=10,
            politician_id=100,
            result="当選",
            votes=5000,
            rank=1,
        )
        item = ElectionMemberOutputItem.from_entity(entity)

        assert item.id == 1
        assert item.election_id == 10
        assert item.politician_id == 100
        assert item.result == "当選"
        assert item.votes == 5000
        assert item.rank == 1

    def test_from_entity_with_none_optional_fields(self) -> None:
        """Noneのオプショナルフィールドが正しく変換されることを確認."""
        from src.application.dtos.election_member_dto import (
            ElectionMemberOutputItem,
        )

        entity = ElectionMember(
            id=None,
            election_id=10,
            politician_id=100,
            result="当選",
            votes=None,
            rank=None,
        )
        item = ElectionMemberOutputItem.from_entity(entity)

        assert item.id is None
        assert item.votes is None
        assert item.rank is None


class TestElectionMemberValidResults:
    """ElectionMember.VALID_RESULTSのテスト."""

    def test_valid_results_contains_expected_values(self) -> None:
        """VALID_RESULTSが期待される全値を含むことを確認."""
        expected = [
            "当選",
            "落選",
            "次点",
            "繰上当選",
            "無投票当選",
            "比例当選",
            "比例復活",
        ]
        assert ElectionMember.VALID_RESULTS == expected
