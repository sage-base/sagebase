"""Tests for ProposalRepositoryImpl."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal import Proposal
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.persistence.proposal_repository_impl import (
    ProposalModel,
    ProposalRepositoryImpl,
)


class TestProposalRepositoryImpl:
    """Test cases for ProposalRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        # Mock async methods
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.get = AsyncMock()
        session.add = MagicMock()
        session.delete = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> ProposalRepositoryImpl:
        """Create proposal repository."""
        return ProposalRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_proposal_dict(self) -> dict[str, Any]:
        """Sample proposal data as dict."""
        return {
            "id": 1,
            "title": "令和6年度予算案の承認について",
            "detail_url": "https://example.com/proposal/001",
            "status_url": "https://example.com/proposal/status/001",
            "votes_url": "https://example.com/proposal/votes/001",
            "meeting_id": 100,
            "conference_id": 10,
            "proposal_category": None,
            "proposal_type": None,
            "governing_body_id": None,
            "session_number": None,
            "proposal_number": None,
            "external_id": None,
            "deliberation_status": None,
            "deliberation_result": None,
            "created_at": None,
            "updated_at": None,
        }

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
        sample_proposal_dict: dict[str, Any],
    ) -> None:
        """Test get_by_id when proposal is found."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_proposal_dict
        mock_row._asdict = MagicMock(return_value=sample_proposal_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_id(1)

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.title == "令和6年度予算案の承認について"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, repository: ProposalRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_id when proposal is not found."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_id(999)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
        sample_proposal_dict: dict[str, Any],
    ) -> None:
        """Test create proposal."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_proposal_dict
        mock_row._asdict = MagicMock(return_value=sample_proposal_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Create entity
        entity = Proposal(
            title="令和6年度予算案の承認について",
        )

        # Execute
        result = await repository.create(entity)

        # Assert
        assert result.id == 1
        assert result.title == "令和6年度予算案の承認について"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test update proposal."""
        # Setup mock result
        updated_dict = {
            "id": 1,
            "title": "令和6年度予算案の承認について（修正版）",
            "detail_url": None,
            "status_url": None,
            "votes_url": None,
            "meeting_id": None,
            "conference_id": 10,
            "proposal_category": None,
            "proposal_type": None,
            "governing_body_id": None,
            "session_number": None,
            "proposal_number": None,
            "external_id": None,
            "deliberation_status": None,
            "deliberation_result": None,
            "created_at": None,
            "updated_at": None,
        }
        mock_row = MagicMock()
        mock_row._mapping = updated_dict
        mock_row._asdict = MagicMock(return_value=updated_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Create entity with ID
        entity = Proposal(
            id=1,
            title="令和6年度予算案の承認について（修正版）",
            conference_id=10,
        )

        # Execute
        result = await repository.update(entity)

        # Assert
        assert result.id == 1
        assert result.title == "令和6年度予算案の承認について（修正版）"
        assert result.conference_id == 10
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_without_id(
        self, repository: ProposalRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test update proposal without ID raises error."""
        entity = Proposal(title="Test")

        with pytest.raises(ValueError) as exc_info:
            await repository.update(entity)

        assert "Entity must have an ID to update" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_success(
        self, repository: ProposalRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test delete proposal successfully."""
        # Mock count check (no related judges)
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=0)

        # Mock delete result
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 1

        mock_session.execute.side_effect = [mock_count_result, mock_delete_result]

        # Execute
        result = await repository.delete(1)

        # Assert
        assert result is True
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_with_related_records(
        self, repository: ProposalRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test delete proposal with related judges fails."""
        # Mock count check (has related judges)
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=5)
        mock_session.execute.return_value = mock_count_result

        # Execute
        result = await repository.delete(1)

        # Assert
        assert result is False
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_all_with_limit(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
        sample_proposal_dict: dict[str, Any],
    ) -> None:
        """Test get_all with limit."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_proposal_dict
        mock_row._asdict = MagicMock(return_value=sample_proposal_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_all(limit=10, offset=0)

        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        mock_session.execute.assert_called_once()

    def test_to_entity(self, repository: ProposalRepositoryImpl) -> None:
        """Test _to_entity conversion."""
        model = ProposalModel(
            id=1,
            title="Test title",
            detail_url="https://test.detail.url",
            status_url="https://test.status.url",
            votes_url="https://test.votes.url",
            meeting_id=42,
            conference_id=10,
            proposal_category="legislation",
            proposal_type="衆法",
            governing_body_id=5,
            session_number=213,
            proposal_number=7,
            external_id="ext-001",
            deliberation_status="成立",
            deliberation_result="passed",
        )

        entity = repository._to_entity(model)

        assert entity.id == 1
        assert entity.title == "Test title"
        assert entity.detail_url == "https://test.detail.url"
        assert entity.status_url == "https://test.status.url"
        assert entity.votes_url == "https://test.votes.url"
        assert entity.meeting_id == 42
        assert entity.conference_id == 10
        assert entity.proposal_category == "legislation"
        assert entity.proposal_type == "衆法"
        assert entity.governing_body_id == 5
        assert entity.session_number == 213
        assert entity.proposal_number == 7
        assert entity.external_id == "ext-001"
        assert entity.deliberation_status == "成立"
        assert entity.deliberation_result == "passed"

    def test_to_model(self, repository: ProposalRepositoryImpl) -> None:
        """Test _to_model conversion."""
        entity = Proposal(
            id=1,
            title="Test title",
            detail_url="https://test.detail.url",
            status_url="https://test.status.url",
            votes_url="https://test.votes.url",
            meeting_id=42,
            conference_id=10,
            proposal_category="budget",
            proposal_type="閣法",
            governing_body_id=3,
            session_number=214,
            proposal_number=15,
            external_id="ext-002",
            deliberation_status="未了",
            deliberation_result="rejected",
        )

        model = repository._to_model(entity)

        assert model.id == 1
        assert model.title == "Test title"
        assert model.detail_url == "https://test.detail.url"
        assert model.status_url == "https://test.status.url"
        assert model.votes_url == "https://test.votes.url"
        assert model.meeting_id == 42
        assert model.conference_id == 10
        assert model.proposal_category == "budget"
        assert model.proposal_type == "閣法"
        assert model.governing_body_id == 3
        assert model.session_number == 214
        assert model.proposal_number == 15
        assert model.external_id == "ext-002"
        assert model.deliberation_status == "未了"
        assert model.deliberation_result == "rejected"

    def test_update_model(self, repository: ProposalRepositoryImpl) -> None:
        """Test _update_model."""
        model = ProposalModel(
            id=1,
            title="Old title",
            detail_url="https://old.detail.url",
            status_url="https://old.status.url",
            votes_url="https://old.votes.url",
            meeting_id=1,
            conference_id=1,
            proposal_category="legislation",
            proposal_type="衆法",
            governing_body_id=1,
            session_number=213,
            proposal_number=1,
            external_id="old-ext",
            deliberation_status="成立",
            deliberation_result="passed",
        )
        entity = Proposal(
            id=1,
            title="New title",
            detail_url="https://new.detail.url",
            status_url="https://new.status.url",
            votes_url="https://new.votes.url",
            meeting_id=2,
            conference_id=2,
            proposal_category="budget",
            proposal_type="閣法",
            governing_body_id=3,
            session_number=214,
            proposal_number=15,
            external_id="new-ext",
            deliberation_status="未了",
            deliberation_result="rejected",
        )

        repository._update_model(model, entity)

        assert model.title == "New title"
        assert model.detail_url == "https://new.detail.url"
        assert model.status_url == "https://new.status.url"
        assert model.votes_url == "https://new.votes.url"
        assert model.meeting_id == 2
        assert model.conference_id == 2
        assert model.proposal_category == "budget"
        assert model.proposal_type == "閣法"
        assert model.governing_body_id == 3
        assert model.session_number == 214
        assert model.proposal_number == 15
        assert model.external_id == "new-ext"
        assert model.deliberation_status == "未了"
        assert model.deliberation_result == "rejected"

    @pytest.mark.asyncio
    async def test_get_by_meeting_id(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
        sample_proposal_dict: dict[str, Any],
    ) -> None:
        """Test get_by_meeting_id returns list of proposals."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_proposal_dict
        mock_row._asdict = MagicMock(return_value=sample_proposal_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_meeting_id(100)

        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].meeting_id == 100
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_conference_id(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
        sample_proposal_dict: dict[str, Any],
    ) -> None:
        """Test get_by_conference_id returns list of proposals."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_proposal_dict
        mock_row._asdict = MagicMock(return_value=sample_proposal_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_conference_id(10)

        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].conference_id == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_meeting_id_database_error(
        self, repository: ProposalRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_meeting_id database error handling."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_meeting_id(100)
        assert "Failed to get proposals by meeting ID" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_by_conference_id_database_error(
        self, repository: ProposalRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_conference_id database error handling."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_conference_id(10)
        assert "Failed to get proposals by conference ID" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_find_by_identifier_found(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test find_by_identifier when proposal is found."""
        found_dict = {
            "id": 5,
            "title": "テスト議案",
            "detail_url": None,
            "status_url": None,
            "votes_url": None,
            "meeting_id": None,
            "conference_id": None,
            "proposal_category": "legislation",
            "proposal_type": "衆法",
            "governing_body_id": 1,
            "session_number": 213,
            "proposal_number": 42,
            "external_id": None,
            "deliberation_status": "成立",
            "deliberation_result": "passed",
            "created_at": None,
            "updated_at": None,
        }
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(return_value=found_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.find_by_identifier(
            governing_body_id=1,
            session_number=213,
            proposal_number=42,
            proposal_type="衆法",
        )

        assert result is not None
        assert result.id == 5
        assert result.governing_body_id == 1
        assert result.session_number == 213
        assert result.proposal_number == 42
        assert result.proposal_type == "衆法"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_identifier_not_found(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test find_by_identifier when proposal is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.find_by_identifier(
            governing_body_id=999,
            session_number=999,
            proposal_number=999,
            proposal_type="unknown",
        )

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_identifier_database_error(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test find_by_identifier database error handling."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(DatabaseError) as exc_info:
            await repository.find_by_identifier(
                governing_body_id=1,
                session_number=213,
                proposal_number=42,
                proposal_type="衆法",
            )
        assert "Failed to find proposal by identifier" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_bulk_create_success(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test bulk_create with multiple proposals."""
        created_dicts = [
            {
                "id": 10,
                "title": "議案A",
                "detail_url": None,
                "status_url": None,
                "votes_url": None,
                "meeting_id": None,
                "conference_id": None,
                "proposal_category": "legislation",
                "proposal_type": "衆法",
                "governing_body_id": 1,
                "session_number": 213,
                "proposal_number": 1,
                "external_id": None,
                "deliberation_status": None,
                "deliberation_result": None,
                "created_at": None,
                "updated_at": None,
            },
            {
                "id": 11,
                "title": "議案B",
                "detail_url": None,
                "status_url": None,
                "votes_url": None,
                "meeting_id": None,
                "conference_id": None,
                "proposal_category": "budget",
                "proposal_type": "閣法",
                "governing_body_id": 1,
                "session_number": 213,
                "proposal_number": 2,
                "external_id": None,
                "deliberation_status": None,
                "deliberation_result": None,
                "created_at": None,
                "updated_at": None,
            },
        ]

        mock_results = []
        for d in created_dicts:
            mock_row = MagicMock()
            mock_row._asdict = MagicMock(return_value=d)
            mock_result = MagicMock()
            mock_result.fetchone = MagicMock(return_value=mock_row)
            mock_results.append(mock_result)

        mock_session.execute.side_effect = mock_results

        entities = [
            Proposal(
                title="議案A",
                proposal_type="衆法",
                governing_body_id=1,
                session_number=213,
                proposal_number=1,
            ),
            Proposal(
                title="議案B",
                proposal_type="閣法",
                governing_body_id=1,
                session_number=213,
                proposal_number=2,
            ),
        ]

        result = await repository.bulk_create(entities)

        assert len(result) == 2
        assert result[0].id == 10
        assert result[0].title == "議案A"
        assert result[1].id == 11
        assert result[1].title == "議案B"
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create_empty_list(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test bulk_create with empty list returns empty list."""
        result = await repository.bulk_create([])

        assert result == []
        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_bulk_create_database_error(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test bulk_create database error handling."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        entities = [Proposal(title="議案A")]

        with pytest.raises(DatabaseError) as exc_info:
            await repository.bulk_create(entities)
        assert "Failed to bulk create proposals" in str(exc_info.value)
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_url_found(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
        sample_proposal_dict: dict[str, Any],
    ) -> None:
        """Test find_by_url when proposal is found."""
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(return_value=sample_proposal_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.find_by_url("https://example.com/proposal/001")

        assert result is not None
        assert result.id == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_url_not_found(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test find_by_url when proposal is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.find_by_url("https://nonexistent.example.com")

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_url_database_error(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test find_by_url database error handling."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(DatabaseError) as exc_info:
            await repository.find_by_url("https://example.com/proposal/001")
        assert "Failed to find proposal by URL" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_all_without_limit(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
        sample_proposal_dict: dict[str, Any],
    ) -> None:
        """Test get_all without limit."""
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(return_value=sample_proposal_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert len(result) == 1
        assert result[0].id == 1

    @pytest.mark.asyncio
    async def test_get_all_empty_result(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all returns empty list when no proposals exist."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert result == []

    @pytest.mark.asyncio
    async def test_count_success(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count returns total number of proposals."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=42)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 42
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_empty(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count returns 0 when no proposals exist."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=0)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 0

    @pytest.mark.asyncio
    async def test_count_database_error(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count database error handling."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(DatabaseError) as exc_info:
            await repository.count()
        assert "Failed to count proposals" in str(exc_info.value)
