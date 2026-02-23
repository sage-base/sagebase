"""ManagePartyMembershipHistoryUseCase のテスト."""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dtos.party_membership_history_dto import (
    CreateMembershipInputDto,
    EndMembershipInputDto,
    GetCurrentPartyInputDto,
    GetHistoryByPoliticianInputDto,
)
from src.application.usecases.manage_party_membership_history_usecase import (
    ManagePartyMembershipHistoryUseCase,
)
from src.domain.entities.party_membership_history import PartyMembershipHistory


@pytest.fixture
def mock_repository() -> MagicMock:
    repo = MagicMock()
    repo.get_by_politician = AsyncMock()
    repo.get_current_by_politician = AsyncMock()
    repo.create = AsyncMock()
    repo.end_membership = AsyncMock()
    return repo


@pytest.fixture
def usecase(mock_repository: MagicMock) -> ManagePartyMembershipHistoryUseCase:
    return ManagePartyMembershipHistoryUseCase(repository=mock_repository)


def _make_entity(
    id: int = 1,
    politician_id: int = 10,
    political_party_id: int = 20,
    start_date: date = date(2024, 1, 1),
    end_date: date | None = None,
) -> PartyMembershipHistory:
    return PartyMembershipHistory(
        id=id,
        politician_id=politician_id,
        political_party_id=political_party_id,
        start_date=start_date,
        end_date=end_date,
        created_at=datetime(2024, 1, 1, 10, 0, 0),
        updated_at=datetime(2024, 1, 1, 10, 0, 0),
    )


class TestGetHistoryByPolitician:
    @pytest.mark.asyncio
    async def test_returns_history(
        self,
        usecase: ManagePartyMembershipHistoryUseCase,
        mock_repository: MagicMock,
    ) -> None:
        entities = [
            _make_entity(id=2, start_date=date(2023, 1, 1)),
            _make_entity(
                id=1, start_date=date(2020, 1, 1), end_date=date(2022, 12, 31)
            ),
        ]
        mock_repository.get_by_politician.return_value = entities

        result = await usecase.get_history_by_politician(
            GetHistoryByPoliticianInputDto(politician_id=10)
        )

        assert len(result.items) == 2
        assert result.items[0].id == 2
        assert result.items[1].id == 1
        mock_repository.get_by_politician.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_returns_empty_list(
        self,
        usecase: ManagePartyMembershipHistoryUseCase,
        mock_repository: MagicMock,
    ) -> None:
        mock_repository.get_by_politician.return_value = []

        result = await usecase.get_history_by_politician(
            GetHistoryByPoliticianInputDto(politician_id=999)
        )

        assert result.items == []


class TestGetCurrentParty:
    @pytest.mark.asyncio
    async def test_returns_current(
        self,
        usecase: ManagePartyMembershipHistoryUseCase,
        mock_repository: MagicMock,
    ) -> None:
        entity = _make_entity()
        mock_repository.get_current_by_politician.return_value = entity

        result = await usecase.get_current_party(
            GetCurrentPartyInputDto(politician_id=10)
        )

        assert result.item is not None
        assert result.item.politician_id == 10

    @pytest.mark.asyncio
    async def test_returns_none_when_no_current(
        self,
        usecase: ManagePartyMembershipHistoryUseCase,
        mock_repository: MagicMock,
    ) -> None:
        mock_repository.get_current_by_politician.return_value = None

        result = await usecase.get_current_party(
            GetCurrentPartyInputDto(politician_id=999)
        )

        assert result.item is None

    @pytest.mark.asyncio
    async def test_with_as_of_date(
        self,
        usecase: ManagePartyMembershipHistoryUseCase,
        mock_repository: MagicMock,
    ) -> None:
        entity = _make_entity()
        mock_repository.get_current_by_politician.return_value = entity
        as_of = date(2024, 6, 15)

        await usecase.get_current_party(
            GetCurrentPartyInputDto(politician_id=10, as_of_date=as_of)
        )

        mock_repository.get_current_by_politician.assert_called_once_with(10, as_of)


class TestCreateMembership:
    @pytest.mark.asyncio
    async def test_creates_successfully(
        self,
        usecase: ManagePartyMembershipHistoryUseCase,
        mock_repository: MagicMock,
    ) -> None:
        created_entity = _make_entity()
        mock_repository.create.return_value = created_entity

        result = await usecase.create_membership(
            CreateMembershipInputDto(
                politician_id=10,
                political_party_id=20,
                start_date=date(2024, 1, 1),
            )
        )

        assert result.success is True
        assert result.item is not None
        assert result.item.politician_id == 10

    @pytest.mark.asyncio
    async def test_handles_error(
        self,
        usecase: ManagePartyMembershipHistoryUseCase,
        mock_repository: MagicMock,
    ) -> None:
        mock_repository.create.side_effect = RuntimeError("DB error")

        result = await usecase.create_membership(
            CreateMembershipInputDto(
                politician_id=10,
                political_party_id=20,
                start_date=date(2024, 1, 1),
            )
        )

        assert result.success is False
        assert "エラー" in result.message


class TestEndMembership:
    @pytest.mark.asyncio
    async def test_ends_successfully(
        self,
        usecase: ManagePartyMembershipHistoryUseCase,
        mock_repository: MagicMock,
    ) -> None:
        ended_entity = _make_entity(end_date=date(2024, 12, 31))
        mock_repository.end_membership.return_value = ended_entity

        result = await usecase.end_membership(
            EndMembershipInputDto(membership_id=1, end_date=date(2024, 12, 31))
        )

        assert result.success is True
        assert result.item is not None
        assert result.item.end_date == date(2024, 12, 31)

    @pytest.mark.asyncio
    async def test_not_found(
        self,
        usecase: ManagePartyMembershipHistoryUseCase,
        mock_repository: MagicMock,
    ) -> None:
        mock_repository.end_membership.return_value = None

        result = await usecase.end_membership(
            EndMembershipInputDto(membership_id=999, end_date=date(2024, 12, 31))
        )

        assert result.success is False
        assert "見つかりません" in result.message

    @pytest.mark.asyncio
    async def test_handles_error(
        self,
        usecase: ManagePartyMembershipHistoryUseCase,
        mock_repository: MagicMock,
    ) -> None:
        mock_repository.end_membership.side_effect = RuntimeError("DB error")

        result = await usecase.end_membership(
            EndMembershipInputDto(membership_id=1, end_date=date(2024, 12, 31))
        )

        assert result.success is False
        assert "エラー" in result.message
