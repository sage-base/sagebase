"""Tests for ElectionMemberRepositoryImpl."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.election_member import ElectionMember
from src.infrastructure.persistence.election_member_repository_impl import (
    ElectionMemberRepositoryImpl,
)
from src.infrastructure.persistence.sqlalchemy_models import (
    ElectionMemberModel,
)


class TestElectionMemberRepositoryImpl:
    """Test cases for ElectionMemberRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.get = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.delete = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> ElectionMemberRepositoryImpl:
        """Create election member repository."""
        return ElectionMemberRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_entity(self) -> ElectionMember:
        """Sample election member entity."""
        return ElectionMember(
            id=1,
            election_id=10,
            politician_id=100,
            result="当選",
            votes=5000,
            rank=1,
        )

    @pytest.fixture
    def sample_model(self) -> MagicMock:
        """Sample SQLAlchemy model mock."""
        model = MagicMock(spec=ElectionMemberModel)
        model.id = 1
        model.election_id = 10
        model.politician_id = 100
        model.result = "当選"
        model.votes = 5000
        model.rank = 1
        return model

    # --- Domain-specific methods ---

    @pytest.mark.asyncio
    async def test_get_by_election_id(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_model: MagicMock,
    ) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_model]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
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
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_election_id(999)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_politician_id(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_model: MagicMock,
    ) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_model]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
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
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_politician_id(999)

        assert result == []

    @pytest.mark.asyncio
    async def test_delete_by_election_id(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result

        result = await repository.delete_by_election_id(10)

        assert result == 3
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_by_election_id_empty(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repository.delete_by_election_id(999)

        assert result == 0

    # --- BaseRepositoryImpl inherited CRUD ---

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_model: MagicMock,
    ) -> None:
        mock_session.get.return_value = sample_model

        result = await repository.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.election_id == 10
        mock_session.get.assert_called_once_with(ElectionMemberModel, 1)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_session.get.return_value = None

        result = await repository.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_model: MagicMock,
    ) -> None:
        model2 = MagicMock(spec=ElectionMemberModel)
        model2.id = 2
        model2.election_id = 10
        model2.politician_id = 101
        model2.result = "落選"
        model2.votes = 3000
        model2.rank = 2

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_model, model2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_create(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_entity: ElectionMember,
    ) -> None:
        async def mock_refresh(model: MagicMock) -> None:
            model.id = 1
            model.election_id = sample_entity.election_id
            model.politician_id = sample_entity.politician_id
            model.result = sample_entity.result
            model.votes = sample_entity.votes
            model.rank = sample_entity.rank

        mock_session.refresh.side_effect = mock_refresh

        result = await repository.create(sample_entity)

        assert result.id == 1
        assert result.result == "当選"
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_entity: ElectionMember,
        sample_model: MagicMock,
    ) -> None:
        mock_session.get.return_value = sample_model

        async def mock_refresh(model: MagicMock) -> None:
            model.result = "落選"
            model.votes = 3000
            model.rank = 2

        mock_session.refresh.side_effect = mock_refresh
        sample_entity.result = "落選"
        sample_entity.votes = 3000
        sample_entity.rank = 2

        result = await repository.update(sample_entity)

        assert result.result == "落選"
        assert result.votes == 3000
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_no_id(
        self,
        repository: ElectionMemberRepositoryImpl,
    ) -> None:
        entity = ElectionMember(election_id=10, politician_id=100, result="当選")

        with pytest.raises(ValueError, match="Entity must have an ID"):
            await repository.update(entity)

    @pytest.mark.asyncio
    async def test_update_not_found(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_entity: ElectionMember,
    ) -> None:
        mock_session.get.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await repository.update(sample_entity)

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_model: MagicMock,
    ) -> None:
        mock_session.get.return_value = sample_model

        result = await repository.delete(1)

        assert result is True
        mock_session.delete.assert_called_once_with(sample_model)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_session.get.return_value = None

        result = await repository.delete(999)

        assert result is False

    @pytest.mark.asyncio
    async def test_count(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalar.return_value = 15
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 15

    @pytest.mark.asyncio
    async def test_count_none_scalar(
        self,
        repository: ElectionMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 0

    # --- Conversion methods ---

    def test_to_entity(self, repository: ElectionMemberRepositoryImpl) -> None:
        model = MagicMock(spec=ElectionMemberModel)
        model.id = 1
        model.election_id = 10
        model.politician_id = 100
        model.result = "当選"
        model.votes = 5000
        model.rank = 1

        entity = repository._to_entity(model)  # type: ignore[reportPrivateUsage]

        assert isinstance(entity, ElectionMember)
        assert entity.id == 1
        assert entity.election_id == 10
        assert entity.result == "当選"

    def test_to_model(
        self,
        repository: ElectionMemberRepositoryImpl,
        sample_entity: ElectionMember,
    ) -> None:
        model = repository._to_model(sample_entity)  # type: ignore[reportPrivateUsage]

        assert isinstance(model, ElectionMemberModel)
        assert model.election_id == 10
        assert model.politician_id == 100
        assert model.result == "当選"

    def test_update_model(
        self,
        repository: ElectionMemberRepositoryImpl,
        sample_entity: ElectionMember,
    ) -> None:
        model = MagicMock(spec=ElectionMemberModel)

        repository._update_model(model, sample_entity)  # type: ignore[reportPrivateUsage]

        assert model.election_id == 10
        assert model.politician_id == 100
        assert model.result == "当選"
        assert model.votes == 5000
        assert model.rank == 1

    # --- Entity tests ---

    def test_election_member_str(self, sample_entity: ElectionMember) -> None:
        result = str(sample_entity)
        assert "election_id=10" in result
        assert "politician_id=100" in result
        assert "result=当選" in result
