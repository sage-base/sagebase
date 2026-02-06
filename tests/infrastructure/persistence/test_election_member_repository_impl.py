"""Tests for ElectionMemberRepositoryImpl."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.election_member import ElectionMember
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.persistence.election_member_repository_impl import (
    ElectionMemberModel,
    ElectionMemberRepositoryImpl,
)


class TestElectionMemberRepositoryImpl:
    """Test cases for ElectionMemberRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> ElectionMemberRepositoryImpl:
        """Create election member repository."""
        return ElectionMemberRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_election_member_entity(self) -> ElectionMember:
        """Sample election member entity."""
        return ElectionMember(
            id=1,
            election_id=10,
            politician_id=100,
            result="当選",
            votes=5000,
            rank=1,
        )

    @pytest.mark.asyncio
    async def test_get_by_election_id(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_election_id returns members for election."""
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(
            return_value={
                "id": 1,
                "election_id": 10,
                "politician_id": 100,
                "result": "当選",
                "votes": 5000,
                "rank": 1,
                "created_at": None,
                "updated_at": None,
            }
        )

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_election_id(10)

        assert len(result) == 1
        assert result[0].election_id == 10
        assert result[0].politician_id == 100
        assert result[0].result == "当選"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_election_id_empty(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_election_id returns empty list when no members."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_election_id(999)

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_politician_id(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_politician_id returns election results for politician."""
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(
            return_value={
                "id": 1,
                "election_id": 10,
                "politician_id": 100,
                "result": "当選",
                "votes": 5000,
                "rank": 1,
                "created_at": None,
                "updated_at": None,
            }
        )

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_politician_id(100)

        assert len(result) == 1
        assert result[0].politician_id == 100
        assert result[0].result == "当選"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_politician_id_empty(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_politician_id returns empty list when no results."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_politician_id(999)

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_id when election member is found."""
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(
            return_value={
                "id": 1,
                "election_id": 10,
                "politician_id": 100,
                "result": "当選",
                "votes": 5000,
                "rank": 1,
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
        assert result.election_id == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_id when election member is not found."""
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(999)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all returns all election members."""
        mock_row1 = MagicMock()
        mock_row1._asdict = MagicMock(
            return_value={
                "id": 1,
                "election_id": 10,
                "politician_id": 100,
                "result": "当選",
                "votes": 5000,
                "rank": 1,
                "created_at": None,
                "updated_at": None,
            }
        )

        mock_row2 = MagicMock()
        mock_row2._asdict = MagicMock(
            return_value={
                "id": 2,
                "election_id": 10,
                "politician_id": 101,
                "result": "落選",
                "votes": 3000,
                "rank": 2,
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
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_election_member_entity: ElectionMember,
    ) -> None:
        """Test create successfully creates election member."""
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(
            return_value={
                "id": 1,
                "election_id": 10,
                "politician_id": 100,
                "result": "当選",
                "votes": 5000,
                "rank": 1,
                "created_at": None,
                "updated_at": None,
            }
        )

        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.create(sample_election_member_entity)

        assert result.id == 1
        assert result.result == "当選"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_failure(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_election_member_entity: ElectionMember,
    ) -> None:
        """Test create raises RuntimeError when creation fails."""
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        with pytest.raises(RuntimeError, match="Failed to create election member"):
            await repository.create(sample_election_member_entity)

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_election_member_entity: ElectionMember,
    ) -> None:
        """Test update successfully updates election member."""
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(
            return_value={
                "id": 1,
                "election_id": 10,
                "politician_id": 100,
                "result": "落選",
                "votes": 3000,
                "rank": 2,
                "created_at": None,
                "updated_at": None,
            }
        )

        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        sample_election_member_entity.result = "落選"
        sample_election_member_entity.votes = 3000
        sample_election_member_entity.rank = 2
        result = await repository.update(sample_election_member_entity)

        assert result.result == "落選"
        assert result.votes == 3000
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_election_member_entity: ElectionMember,
    ) -> None:
        """Test update raises UpdateError when election member not found."""
        from src.infrastructure.exceptions import UpdateError

        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        with pytest.raises(UpdateError, match="ElectionMember with ID 1 not found"):
            await repository.update(sample_election_member_entity)

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete successfully deletes election member."""
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 1
        mock_session.execute.return_value = mock_delete_result

        result = await repository.delete(1)

        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete returns False when election member not found."""
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 0
        mock_session.execute.return_value = mock_delete_result

        result = await repository.delete(999)

        assert result is False
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_count(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count returns total number."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=15)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 15
        mock_session.execute.assert_called_once()

    def test_to_entity(self, repository: ElectionMemberRepositoryImpl) -> None:
        """Test _to_entity converts model to entity correctly."""
        model = ElectionMemberModel(
            id=1,
            election_id=10,
            politician_id=100,
            result="当選",
            votes=5000,
            rank=1,
        )

        entity = repository._to_entity(model)

        assert isinstance(entity, ElectionMember)
        assert entity.id == 1
        assert entity.election_id == 10
        assert entity.result == "当選"

    def test_to_model(
        self,
        repository: ElectionMemberRepositoryImpl,
        sample_election_member_entity: ElectionMember,
    ) -> None:
        """Test _to_model converts entity to model correctly."""
        model = repository._to_model(sample_election_member_entity)

        assert isinstance(model, ElectionMemberModel)
        assert model.election_id == 10
        assert model.politician_id == 100
        assert model.result == "当選"

    def test_update_model(
        self,
        repository: ElectionMemberRepositoryImpl,
        sample_election_member_entity: ElectionMember,
    ) -> None:
        """Test _update_model updates model fields from entity."""
        model = ElectionMemberModel(
            id=1,
            election_id=1,
            politician_id=1,
            result="落選",
            votes=100,
            rank=10,
        )

        repository._update_model(model, sample_election_member_entity)

        assert model.election_id == 10
        assert model.politician_id == 100
        assert model.result == "当選"
        assert model.votes == 5000
        assert model.rank == 1

    def test_dict_to_entity(self, repository: ElectionMemberRepositoryImpl) -> None:
        """Test _dict_to_entity converts dict to entity correctly."""
        data = {
            "id": 1,
            "election_id": 10,
            "politician_id": 100,
            "result": "当選",
            "votes": 5000,
            "rank": 1,
        }

        entity = repository._dict_to_entity(data)

        assert isinstance(entity, ElectionMember)
        assert entity.id == 1
        assert entity.election_id == 10
        assert entity.result == "当選"

    def test_election_member_str(
        self, sample_election_member_entity: ElectionMember
    ) -> None:
        """Test ElectionMember __str__ method."""
        result = str(sample_election_member_entity)
        assert "election_id=10" in result
        assert "politician_id=100" in result
        assert "result=当選" in result

    @pytest.mark.asyncio
    async def test_get_by_election_id_database_error(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_election_id raises DatabaseError on SQLAlchemyError."""
        mock_session.execute.side_effect = SQLAlchemyError("connection error")

        with pytest.raises(DatabaseError, match="Failed to get election members"):
            await repository.get_by_election_id(10)

    @pytest.mark.asyncio
    async def test_get_by_politician_id_database_error(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_politician_id raises DatabaseError on SQLAlchemyError."""
        mock_session.execute.side_effect = SQLAlchemyError("connection error")

        with pytest.raises(DatabaseError, match="Failed to get election members"):
            await repository.get_by_politician_id(100)

    @pytest.mark.asyncio
    async def test_create_database_error(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_election_member_entity: ElectionMember,
    ) -> None:
        """Test create raises DatabaseError on SQLAlchemyError."""
        mock_session.execute.side_effect = SQLAlchemyError("insert error")

        with pytest.raises(DatabaseError, match="Failed to create election member"):
            await repository.create(sample_election_member_entity)

        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_by_election_id(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete_by_election_id removes all members for election."""
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result

        result = await repository.delete_by_election_id(10)

        assert result == 3
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_by_election_id_empty(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete_by_election_id when no members exist."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repository.delete_by_election_id(999)

        assert result == 0
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all with limit and offset parameters."""
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(
            return_value={
                "id": 1,
                "election_id": 10,
                "politician_id": 100,
                "result": "当選",
                "votes": 5000,
                "rank": 1,
                "created_at": None,
                "updated_at": None,
            }
        )

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all(limit=10, offset=5)

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_none_scalar(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count returns 0 when scalar returns None."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 0

    @pytest.mark.asyncio
    async def test_delete_by_election_id_database_error(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete_by_election_id raises DatabaseError on SQLAlchemyError."""
        mock_session.execute.side_effect = SQLAlchemyError("delete error")

        with pytest.raises(DatabaseError, match="Failed to delete election members"):
            await repository.delete_by_election_id(10)

        mock_session.rollback.assert_called_once()
