"""Tests for ProposalDeliberationRepositoryImpl."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal_deliberation import ProposalDeliberation
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.persistence.proposal_deliberation_repository_impl import (
    ProposalDeliberationRepositoryImpl,
)


class TestProposalDeliberationRepositoryImpl:
    """Test cases for ProposalDeliberationRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> ProposalDeliberationRepositoryImpl:
        return ProposalDeliberationRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_dict(self) -> dict[str, Any]:
        return {
            "id": 1,
            "proposal_id": 10,
            "conference_id": 20,
            "meeting_id": 30,
            "stage": "付託",
            "created_at": None,
            "updated_at": None,
        }

    def _make_mock_row(self, data: dict[str, Any]) -> MagicMock:
        row = MagicMock()
        row._asdict = MagicMock(return_value=data)
        row._mapping = data
        return row

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
        sample_dict: dict[str, Any],
    ) -> None:
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=self._make_mock_row(sample_dict))
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.proposal_id == 10
        assert result.conference_id == 20
        assert result.meeting_id == 30
        assert result.stage == "付託"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_database_error(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_session.execute.side_effect = SQLAlchemyError("DB error")

        with pytest.raises(DatabaseError):
            await repository.get_by_id(1)

    @pytest.mark.asyncio
    async def test_get_all(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
        sample_dict: dict[str, Any],
    ) -> None:
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(
            return_value=[self._make_mock_row(sample_dict)]
        )
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert len(result) == 1
        assert result[0].id == 1

    @pytest.mark.asyncio
    async def test_get_by_ids(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
        sample_dict: dict[str, Any],
    ) -> None:
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(
            return_value=[self._make_mock_row(sample_dict)]
        )
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_ids([1])

        assert len(result) == 1
        assert result[0].id == 1

    @pytest.mark.asyncio
    async def test_get_by_ids_empty(
        self,
        repository: ProposalDeliberationRepositoryImpl,
    ) -> None:
        result = await repository.get_by_ids([])
        assert result == []

    @pytest.mark.asyncio
    async def test_create(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
        sample_dict: dict[str, Any],
    ) -> None:
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=self._make_mock_row(sample_dict))
        mock_session.execute.return_value = mock_result

        entity = ProposalDeliberation(
            proposal_id=10, conference_id=20, meeting_id=30, stage="付託"
        )
        result = await repository.create(entity)

        assert result.id == 1
        assert result.proposal_id == 10
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_database_error(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_session.execute.side_effect = SQLAlchemyError("DB error")

        entity = ProposalDeliberation(proposal_id=10, conference_id=20)

        with pytest.raises(DatabaseError):
            await repository.create(entity)
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
        sample_dict: dict[str, Any],
    ) -> None:
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=self._make_mock_row(sample_dict))
        mock_session.execute.return_value = mock_result

        entity = ProposalDeliberation(
            id=1,
            proposal_id=10,
            conference_id=20,
            meeting_id=30,
            stage="付託",
        )
        result = await repository.update(entity)

        assert result.id == 1
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_without_id_raises(
        self,
        repository: ProposalDeliberationRepositoryImpl,
    ) -> None:
        entity = ProposalDeliberation(proposal_id=10, conference_id=20)

        with pytest.raises(ValueError, match="Entity must have an ID"):
            await repository.update(entity)

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.delete(1)

        assert result is True
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repository.delete(999)

        assert result is False

    @pytest.mark.asyncio
    async def test_count(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=5)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 5

    @pytest.mark.asyncio
    async def test_count_none_returns_zero(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_by_proposal_id(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
        sample_dict: dict[str, Any],
    ) -> None:
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(
            return_value=[self._make_mock_row(sample_dict)]
        )
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_proposal_id(10)

        assert len(result) == 1
        assert result[0].proposal_id == 10

    @pytest.mark.asyncio
    async def test_get_by_conference_id(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
        sample_dict: dict[str, Any],
    ) -> None:
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(
            return_value=[self._make_mock_row(sample_dict)]
        )
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_conference_id(20)

        assert len(result) == 1
        assert result[0].conference_id == 20

    @pytest.mark.asyncio
    async def test_get_by_meeting_id(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
        sample_dict: dict[str, Any],
    ) -> None:
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(
            return_value=[self._make_mock_row(sample_dict)]
        )
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_meeting_id(30)

        assert len(result) == 1
        assert result[0].meeting_id == 30

    @pytest.mark.asyncio
    async def test_find_by_proposal_and_conference_found(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
        sample_dict: dict[str, Any],
    ) -> None:
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=self._make_mock_row(sample_dict))
        mock_session.execute.return_value = mock_result

        result = await repository.find_by_proposal_and_conference(
            proposal_id=10,
            conference_id=20,
            meeting_id=30,
            stage="付託",
        )

        assert result is not None
        assert result.proposal_id == 10
        assert result.conference_id == 20

    @pytest.mark.asyncio
    async def test_find_by_proposal_and_conference_not_found(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.find_by_proposal_and_conference(
            proposal_id=10,
            conference_id=20,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_proposal_and_conference_with_null_meeting_and_stage(
        self,
        repository: ProposalDeliberationRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        await repository.find_by_proposal_and_conference(
            proposal_id=10,
            conference_id=20,
        )

        call_args = mock_session.execute.call_args
        query_str = str(call_args[0][0].text)
        assert "meeting_id IS NULL" in query_str
        assert "stage IS NULL" in query_str
