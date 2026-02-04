"""Tests for ElectionRepositoryImpl."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.election import Election
from src.infrastructure.persistence.election_repository_impl import (
    ElectionModel,
    ElectionRepositoryImpl,
)


class TestElectionRepositoryImpl:
    """Test cases for ElectionRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> ElectionRepositoryImpl:
        """Create election repository."""
        return ElectionRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_election_entity(self) -> Election:
        """Sample election entity."""
        return Election(
            id=1,
            governing_body_id=88,
            term_number=21,
            election_date=date(2023, 4, 9),
            election_type="統一地方選挙",
        )

    @pytest.mark.asyncio
    async def test_get_by_governing_body(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_governing_body returns elections for governing body."""
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(
            return_value={
                "id": 1,
                "governing_body_id": 88,
                "term_number": 21,
                "election_date": date(2023, 4, 9),
                "election_type": "統一地方選挙",
                "created_at": None,
                "updated_at": None,
            }
        )

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_governing_body(88)

        assert len(result) == 1
        assert result[0].governing_body_id == 88
        assert result[0].term_number == 21
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_governing_body_empty(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_governing_body returns empty list when no elections."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_governing_body(999)

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_governing_body_and_term_found(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_governing_body_and_term when election is found."""
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(
            return_value={
                "id": 1,
                "governing_body_id": 88,
                "term_number": 21,
                "election_date": date(2023, 4, 9),
                "election_type": "統一地方選挙",
                "created_at": None,
                "updated_at": None,
            }
        )

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_governing_body_and_term(88, 21)

        assert result is not None
        assert result.governing_body_id == 88
        assert result.term_number == 21
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_governing_body_and_term_not_found(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_governing_body_and_term when election is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_governing_body_and_term(999, 99)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_id when election is found."""
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(
            return_value={
                "id": 1,
                "governing_body_id": 88,
                "term_number": 21,
                "election_date": date(2023, 4, 9),
                "election_type": "統一地方選挙",
                "created_at": None,
                "updated_at": None,
            }
        )

        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(1)

        assert result is not None
        assert result.id == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_id when election is not found."""
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(999)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all returns all elections."""
        mock_row1 = MagicMock()
        mock_row1._asdict = MagicMock(
            return_value={
                "id": 1,
                "governing_body_id": 88,
                "term_number": 21,
                "election_date": date(2023, 4, 9),
                "election_type": "統一地方選挙",
                "created_at": None,
                "updated_at": None,
            }
        )

        mock_row2 = MagicMock()
        mock_row2._asdict = MagicMock(
            return_value={
                "id": 2,
                "governing_body_id": 88,
                "term_number": 20,
                "election_date": date(2019, 4, 7),
                "election_type": "統一地方選挙",
                "created_at": None,
                "updated_at": None,
            }
        )

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row1, mock_row2])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert len(result) == 2
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
        sample_election_entity: Election,
    ) -> None:
        """Test create successfully creates election."""
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(
            return_value={
                "id": 1,
                "governing_body_id": 88,
                "term_number": 21,
                "election_date": date(2023, 4, 9),
                "election_type": "統一地方選挙",
                "created_at": None,
                "updated_at": None,
            }
        )

        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.create(sample_election_entity)

        assert result.id == 1
        assert result.term_number == 21
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_failure(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
        sample_election_entity: Election,
    ) -> None:
        """Test create raises RuntimeError when creation fails."""
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        with pytest.raises(RuntimeError, match="Failed to create election"):
            await repository.create(sample_election_entity)

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
        sample_election_entity: Election,
    ) -> None:
        """Test update successfully updates election."""
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(
            return_value={
                "id": 1,
                "governing_body_id": 88,
                "term_number": 22,
                "election_date": date(2027, 4, 11),
                "election_type": "統一地方選挙",
                "created_at": None,
                "updated_at": None,
            }
        )

        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        sample_election_entity.term_number = 22
        sample_election_entity.election_date = date(2027, 4, 11)
        result = await repository.update(sample_election_entity)

        assert result.term_number == 22
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
        sample_election_entity: Election,
    ) -> None:
        """Test update raises UpdateError when election not found."""
        from src.infrastructure.exceptions import UpdateError

        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        with pytest.raises(UpdateError, match="Election with ID 1 not found"):
            await repository.update(sample_election_entity)

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete successfully deletes election."""
        # Mock count check (no related conferences)
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=0)

        # Mock delete result
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 1

        # Setup execute to return different results for check and delete
        mock_session.execute.side_effect = [mock_count_result, mock_delete_result]

        result = await repository.delete(1)

        assert result is True
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_with_related_conferences(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete fails when election has related conferences."""
        # Mock count check (has related conferences)
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=5)
        mock_session.execute.return_value = mock_count_result

        result = await repository.delete(1)

        assert result is False
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_count(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count returns total number."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=10)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 10
        mock_session.execute.assert_called_once()

    def test_to_entity(self, repository: ElectionRepositoryImpl) -> None:
        """Test _to_entity converts model to entity correctly."""
        model = ElectionModel(
            id=1,
            governing_body_id=88,
            term_number=21,
            election_date=date(2023, 4, 9),
            election_type="統一地方選挙",
        )

        entity = repository._to_entity(model)

        assert isinstance(entity, Election)
        assert entity.id == 1
        assert entity.term_number == 21

    def test_to_model(
        self,
        repository: ElectionRepositoryImpl,
        sample_election_entity: Election,
    ) -> None:
        """Test _to_model converts entity to model correctly."""
        model = repository._to_model(sample_election_entity)

        assert isinstance(model, ElectionModel)
        assert model.governing_body_id == 88
        assert model.term_number == 21

    def test_update_model(
        self,
        repository: ElectionRepositoryImpl,
        sample_election_entity: Election,
    ) -> None:
        """Test _update_model updates model fields from entity."""
        model = ElectionModel(
            id=1,
            governing_body_id=1,
            term_number=1,
            election_date=date(2000, 1, 1),
            election_type="旧タイプ",
        )

        repository._update_model(model, sample_election_entity)

        assert model.governing_body_id == 88
        assert model.term_number == 21
        assert model.election_date == date(2023, 4, 9)
        assert model.election_type == "統一地方選挙"

    def test_dict_to_entity(self, repository: ElectionRepositoryImpl) -> None:
        """Test _dict_to_entity converts dict to entity correctly."""
        data = {
            "id": 1,
            "governing_body_id": 88,
            "term_number": 21,
            "election_date": date(2023, 4, 9),
            "election_type": "統一地方選挙",
        }

        entity = repository._dict_to_entity(data)

        assert isinstance(entity, Election)
        assert entity.id == 1
        assert entity.term_number == 21

    def test_election_str(self, sample_election_entity: Election) -> None:
        """Test Election __str__ method."""
        assert str(sample_election_entity) == "第21期 (2023-04-09)"
