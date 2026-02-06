"""Tests for ManageElectionMembersUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.usecases.manage_election_members_usecase import (
    CreateElectionMemberInputDto,
    DeleteElectionMemberInputDto,
    ListElectionMembersByElectionInputDto,
    ListElectionMembersByPoliticianInputDto,
    ManageElectionMembersUseCase,
    UpdateElectionMemberInputDto,
)
from src.domain.entities.election_member import ElectionMember
from src.domain.repositories.election_member_repository import ElectionMemberRepository


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
        assert len(options) == 5
