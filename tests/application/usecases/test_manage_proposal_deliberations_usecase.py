"""Tests for ManageProposalDeliberationsUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.usecases.manage_proposal_deliberations_usecase import (
    CreateDeliberationInputDto,
    DeleteDeliberationInputDto,
    ListDeliberationsInputDto,
    ManageProposalDeliberationsUseCase,
)
from src.domain.entities.proposal_deliberation import ProposalDeliberation


class TestManageProposalDeliberationsUseCase:
    """Test cases for ManageProposalDeliberationsUseCase."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        repo = MagicMock()
        repo.get_by_proposal_id = AsyncMock()
        repo.get_by_conference_id = AsyncMock()
        repo.get_by_meeting_id = AsyncMock()
        repo.get_all = AsyncMock()
        repo.get_by_id = AsyncMock()
        repo.create = AsyncMock()
        repo.delete = AsyncMock()
        repo.find_by_proposal_and_conference = AsyncMock()
        return repo

    @pytest.fixture
    def usecase(self, mock_repository: MagicMock) -> ManageProposalDeliberationsUseCase:
        return ManageProposalDeliberationsUseCase(repository=mock_repository)

    @pytest.fixture
    def sample_entity(self) -> ProposalDeliberation:
        return ProposalDeliberation(
            id=1,
            proposal_id=10,
            conference_id=20,
            meeting_id=30,
            stage="付託",
        )

    @pytest.mark.asyncio
    async def test_list_by_proposal_id(
        self,
        usecase: ManageProposalDeliberationsUseCase,
        mock_repository: MagicMock,
        sample_entity: ProposalDeliberation,
    ) -> None:
        mock_repository.get_by_proposal_id.return_value = [sample_entity]

        result = await usecase.list_deliberations(
            ListDeliberationsInputDto(proposal_id=10)
        )

        assert result.total_count == 1
        assert result.deliberations[0].proposal_id == 10
        mock_repository.get_by_proposal_id.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_list_by_conference_id(
        self,
        usecase: ManageProposalDeliberationsUseCase,
        mock_repository: MagicMock,
        sample_entity: ProposalDeliberation,
    ) -> None:
        mock_repository.get_by_conference_id.return_value = [sample_entity]

        result = await usecase.list_deliberations(
            ListDeliberationsInputDto(conference_id=20)
        )

        assert result.total_count == 1
        mock_repository.get_by_conference_id.assert_called_once_with(20)

    @pytest.mark.asyncio
    async def test_list_by_meeting_id(
        self,
        usecase: ManageProposalDeliberationsUseCase,
        mock_repository: MagicMock,
        sample_entity: ProposalDeliberation,
    ) -> None:
        mock_repository.get_by_meeting_id.return_value = [sample_entity]

        result = await usecase.list_deliberations(
            ListDeliberationsInputDto(meeting_id=30)
        )

        assert result.total_count == 1
        mock_repository.get_by_meeting_id.assert_called_once_with(30)

    @pytest.mark.asyncio
    async def test_list_all(
        self,
        usecase: ManageProposalDeliberationsUseCase,
        mock_repository: MagicMock,
        sample_entity: ProposalDeliberation,
    ) -> None:
        mock_repository.get_all.return_value = [sample_entity]

        result = await usecase.list_deliberations(ListDeliberationsInputDto())

        assert result.total_count == 1
        mock_repository.get_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        usecase: ManageProposalDeliberationsUseCase,
        mock_repository: MagicMock,
        sample_entity: ProposalDeliberation,
    ) -> None:
        mock_repository.find_by_proposal_and_conference.return_value = None
        mock_repository.create.return_value = sample_entity

        result = await usecase.create_deliberation(
            CreateDeliberationInputDto(
                proposal_id=10,
                conference_id=20,
                meeting_id=30,
                stage="付託",
            )
        )

        assert result.success is True
        assert result.deliberation is not None
        assert result.deliberation.id == 1
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate(
        self,
        usecase: ManageProposalDeliberationsUseCase,
        mock_repository: MagicMock,
        sample_entity: ProposalDeliberation,
    ) -> None:
        mock_repository.find_by_proposal_and_conference.return_value = sample_entity

        result = await usecase.create_deliberation(
            CreateDeliberationInputDto(
                proposal_id=10,
                conference_id=20,
                meeting_id=30,
                stage="付託",
            )
        )

        assert result.success is False
        assert "既に存在" in result.message
        mock_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_error(
        self,
        usecase: ManageProposalDeliberationsUseCase,
        mock_repository: MagicMock,
    ) -> None:
        mock_repository.find_by_proposal_and_conference.return_value = None
        mock_repository.create.side_effect = Exception("DB error")

        result = await usecase.create_deliberation(
            CreateDeliberationInputDto(proposal_id=10, conference_id=20)
        )

        assert result.success is False
        assert "エラー" in result.message

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        usecase: ManageProposalDeliberationsUseCase,
        mock_repository: MagicMock,
        sample_entity: ProposalDeliberation,
    ) -> None:
        mock_repository.get_by_id.return_value = sample_entity
        mock_repository.delete.return_value = True

        result = await usecase.delete_deliberation(
            DeleteDeliberationInputDto(deliberation_id=1)
        )

        assert result.success is True
        mock_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        usecase: ManageProposalDeliberationsUseCase,
        mock_repository: MagicMock,
    ) -> None:
        mock_repository.get_by_id.return_value = None

        result = await usecase.delete_deliberation(
            DeleteDeliberationInputDto(deliberation_id=999)
        )

        assert result.success is False
        assert "見つかりません" in result.message
        mock_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_failed(
        self,
        usecase: ManageProposalDeliberationsUseCase,
        mock_repository: MagicMock,
        sample_entity: ProposalDeliberation,
    ) -> None:
        mock_repository.get_by_id.return_value = sample_entity
        mock_repository.delete.return_value = False

        result = await usecase.delete_deliberation(
            DeleteDeliberationInputDto(deliberation_id=1)
        )

        assert result.success is False
        assert "失敗" in result.message

    @pytest.mark.asyncio
    async def test_delete_error(
        self,
        usecase: ManageProposalDeliberationsUseCase,
        mock_repository: MagicMock,
        sample_entity: ProposalDeliberation,
    ) -> None:
        mock_repository.get_by_id.return_value = sample_entity
        mock_repository.delete.side_effect = Exception("DB error")

        result = await usecase.delete_deliberation(
            DeleteDeliberationInputDto(deliberation_id=1)
        )

        assert result.success is False
        assert "エラー" in result.message
