"""Tests for ElectionRepositoryImpl."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.election import Election
from src.infrastructure.persistence.election_repository_impl import (
    ElectionRepositoryImpl,
)
from src.infrastructure.persistence.sqlalchemy_models import (
    ElectionModel,
)


class TestElectionRepositoryImpl:
    """Test cases for ElectionRepositoryImpl."""

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
    def repository(self, mock_session: MagicMock) -> ElectionRepositoryImpl:
        """Create election repository."""
        return ElectionRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_entity(self) -> Election:
        """Sample election entity."""
        return Election(
            id=1,
            governing_body_id=88,
            term_number=21,
            election_date=date(2023, 4, 9),
            election_type="統一地方選挙",
        )

    @pytest.fixture
    def sample_model(self) -> MagicMock:
        """Sample SQLAlchemy model mock."""
        model = MagicMock(spec=ElectionModel)
        model.id = 1
        model.governing_body_id = 88
        model.term_number = 21
        model.election_date = date(2023, 4, 9)
        model.election_type = "統一地方選挙"
        return model

    # --- Domain-specific methods ---

    @pytest.mark.asyncio
    async def test_get_by_governing_body(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
        sample_model: MagicMock,
    ) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_model]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
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
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_governing_body(999)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_governing_body_and_term_found(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
        sample_model: MagicMock,
    ) -> None:
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = sample_model
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
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
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_governing_body_and_term(999, 99)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_governing_body_and_term_with_election_type(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
        sample_model: MagicMock,
    ) -> None:
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = sample_model
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_governing_body_and_term(
            88, 21, election_type="衆議院議員総選挙"
        )

        assert result is not None
        assert result.governing_body_id == 88
        assert result.term_number == 21
        mock_session.execute.assert_called_once()

    # --- BaseRepositoryImpl inherited CRUD ---

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
        sample_model: MagicMock,
    ) -> None:
        mock_session.get.return_value = sample_model

        result = await repository.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.governing_body_id == 88
        mock_session.get.assert_called_once_with(ElectionModel, 1)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_session.get.return_value = None

        result = await repository.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
        sample_model: MagicMock,
    ) -> None:
        model2 = MagicMock(spec=ElectionModel)
        model2.id = 2
        model2.governing_body_id = 88
        model2.term_number = 20
        model2.election_date = date(2019, 4, 7)
        model2.election_type = "統一地方選挙"

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
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
        sample_entity: Election,
    ) -> None:
        async def mock_refresh(model: MagicMock) -> None:
            model.id = 1
            model.governing_body_id = sample_entity.governing_body_id
            model.term_number = sample_entity.term_number
            model.election_date = sample_entity.election_date
            model.election_type = sample_entity.election_type

        mock_session.refresh.side_effect = mock_refresh

        result = await repository.create(sample_entity)

        assert result.id == 1
        assert result.term_number == 21
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
        sample_entity: Election,
        sample_model: MagicMock,
    ) -> None:
        mock_session.get.return_value = sample_model

        async def mock_refresh(model: MagicMock) -> None:
            model.term_number = 22
            model.election_date = date(2027, 4, 11)

        mock_session.refresh.side_effect = mock_refresh
        sample_entity.term_number = 22
        sample_entity.election_date = date(2027, 4, 11)

        result = await repository.update(sample_entity)

        assert result.term_number == 22
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_no_id(
        self,
        repository: ElectionRepositoryImpl,
    ) -> None:
        entity = Election(
            governing_body_id=88,
            term_number=21,
            election_date=date(2023, 4, 9),
        )

        with pytest.raises(ValueError, match="Entity must have an ID"):
            await repository.update(entity)

    @pytest.mark.asyncio
    async def test_update_not_found(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
        sample_entity: Election,
    ) -> None:
        mock_session.get.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await repository.update(sample_entity)

    # --- Custom delete (conferences check) ---

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
        sample_model: MagicMock,
    ) -> None:
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_count_result
        mock_session.get.return_value = sample_model

        result = await repository.delete(1)

        assert result is True
        mock_session.delete.assert_called_once_with(sample_model)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_with_related_conferences(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_count_result

        result = await repository.delete(1)

        assert result is False
        mock_session.execute.assert_called_once()
        mock_session.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_count_result
        mock_session.get.return_value = None

        result = await repository.delete(999)

        assert result is False

    @pytest.mark.asyncio
    async def test_count(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 10

    @pytest.mark.asyncio
    async def test_count_none_scalar(
        self,
        repository: ElectionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 0

    # --- Conversion methods ---

    def test_to_entity(self, repository: ElectionRepositoryImpl) -> None:
        model = MagicMock(spec=ElectionModel)
        model.id = 1
        model.governing_body_id = 88
        model.term_number = 21
        model.election_date = date(2023, 4, 9)
        model.election_type = "統一地方選挙"

        entity = repository._to_entity(model)  # type: ignore[reportPrivateUsage]

        assert isinstance(entity, Election)
        assert entity.id == 1
        assert entity.term_number == 21

    def test_to_entity_with_null_optional_fields(
        self, repository: ElectionRepositoryImpl
    ) -> None:
        model = MagicMock(spec=ElectionModel)
        model.id = 1
        model.governing_body_id = 88
        model.term_number = 21
        model.election_date = date(2023, 4, 9)
        model.election_type = None

        entity = repository._to_entity(model)  # type: ignore[reportPrivateUsage]

        assert entity.election_type is None

    def test_to_model(
        self,
        repository: ElectionRepositoryImpl,
        sample_entity: Election,
    ) -> None:
        model = repository._to_model(sample_entity)  # type: ignore[reportPrivateUsage]

        assert isinstance(model, ElectionModel)
        assert model.governing_body_id == 88
        assert model.term_number == 21

    def test_update_model(
        self,
        repository: ElectionRepositoryImpl,
        sample_entity: Election,
    ) -> None:
        model = MagicMock(spec=ElectionModel)

        repository._update_model(model, sample_entity)  # type: ignore[reportPrivateUsage]

        assert model.governing_body_id == 88
        assert model.term_number == 21
        assert model.election_date == date(2023, 4, 9)
        assert model.election_type == "統一地方選挙"

    # --- Entity tests ---

    def test_election_str(self, sample_entity: Election) -> None:
        assert str(sample_entity) == "第21期 (2023-04-09)"
