"""Tests for ConferenceRepositoryImpl."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.conference import Conference
from src.infrastructure.exceptions import (
    DatabaseError,
)
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceModel,
    ConferenceRepositoryImpl,
)


class TestConferenceRepositoryImpl:
    """Test cases for ConferenceRepositoryImpl."""

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
    def repository(self, mock_session: MagicMock) -> ConferenceRepositoryImpl:
        """Create conference repository."""
        return ConferenceRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_conference_dict(self) -> dict[str, Any]:
        """Sample conference data as dict."""
        return {
            "id": 1,
            "name": "本会議",
            "governing_body_id": 10,
            "prefecture": "東京都",
            "term": None,
            "created_at": None,
            "updated_at": None,
        }

    @pytest.fixture
    def sample_conference_entity(self) -> Conference:
        """Sample conference entity."""
        return Conference(
            id=1,
            name="本会議",
            governing_body_id=10,
            prefecture="東京都",
            term=None,
        )

    @pytest.mark.asyncio
    async def test_get_by_name_and_governing_body_found(
        self,
        repository: ConferenceRepositoryImpl,
        mock_session: MagicMock,
        sample_conference_dict: dict[str, Any],
    ) -> None:
        """Test get_by_name_and_governing_body when conference is found."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_conference_dict
        mock_row._asdict = MagicMock(return_value=sample_conference_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_name_and_governing_body("本会議", 10)

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.name == "本会議"
        assert result.governing_body_id == 10
        assert result.prefecture == "東京都"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_name_and_governing_body_not_found(
        self, repository: ConferenceRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_name_and_governing_body when conference is not found."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_name_and_governing_body("本会議", 10)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_name_and_governing_body_database_error(
        self, repository: ConferenceRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_name_and_governing_body with database error."""
        # Setup mock to raise exception
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Execute and assert
        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_name_and_governing_body("本会議", 10)

        assert "Failed to get conference by name and governing body" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_get_by_governing_body(
        self,
        repository: ConferenceRepositoryImpl,
        mock_session: MagicMock,
        sample_conference_dict: dict[str, Any],
    ) -> None:
        """Test get_by_governing_body returns list of conferences."""
        # Setup mock result with multiple conferences
        mock_row1 = MagicMock()
        mock_row1._mapping = sample_conference_dict
        mock_row1._asdict = MagicMock(return_value=sample_conference_dict)
        mock_row2_dict = {
            **sample_conference_dict,
            "id": 2,
            "name": "予算委員会",
        }
        mock_row2 = MagicMock()
        mock_row2._mapping = mock_row2_dict
        mock_row2._asdict = MagicMock(return_value=mock_row2_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row1, mock_row2])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_governing_body(10)

        # Assert
        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].name == "本会議"
        assert result[1].id == 2
        assert result[1].name == "予算委員会"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_governing_body_empty(
        self, repository: ConferenceRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_governing_body returns empty list when no conferences."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_governing_body(10)

        # Assert
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_limit(
        self,
        repository: ConferenceRepositoryImpl,
        mock_session: MagicMock,
        sample_conference_dict: dict[str, Any],
    ) -> None:
        """Test get_all with limit and offset."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_conference_dict
        mock_row._asdict = MagicMock(return_value=sample_conference_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_all(limit=10, offset=5)

        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        # Check that execute was called with limit and offset params
        call_args = mock_session.execute.call_args
        assert "LIMIT :limit OFFSET :offset" in call_args[0][0].text
        assert call_args[0][1]["limit"] == 10
        assert call_args[0][1]["offset"] == 5

    @pytest.mark.asyncio
    async def test_get_all_without_limit(
        self,
        repository: ConferenceRepositoryImpl,
        mock_session: MagicMock,
        sample_conference_dict: dict[str, Any],
    ) -> None:
        """Test get_all without limit."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_conference_dict
        mock_row._asdict = MagicMock(return_value=sample_conference_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_all()

        # Assert
        assert len(result) == 1
        # Check that execute was called without limit/offset params
        call_args = mock_session.execute.call_args
        assert "LIMIT" not in call_args[0][0].text
        assert call_args[0][1] == {}

    @pytest.mark.asyncio
    async def test_get_all_database_error(
        self, repository: ConferenceRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_all handles database error."""
        # Setup mock to raise exception
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Execute and assert
        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_all()

        assert "Failed to get all conferences" in str(exc_info.value)

    def test_to_entity(self, repository: ConferenceRepositoryImpl) -> None:
        """Test _to_entity converts model to entity correctly."""
        # Create model
        model = ConferenceModel(
            id=1,
            name="本会議",
            governing_body_id=10,
            prefecture="東京都",
        )

        # Convert
        entity = repository._to_entity(model)  # type: ignore[reportPrivateUsage]

        # Assert
        assert isinstance(entity, Conference)
        assert entity.id == 1
        assert entity.name == "本会議"
        assert entity.governing_body_id == 10
        assert entity.prefecture == "東京都"

    def test_to_model(
        self, repository: ConferenceRepositoryImpl, sample_conference_entity: Conference
    ) -> None:
        """Test _to_model converts entity to model correctly."""
        # Convert
        model = repository._to_model(sample_conference_entity)  # type: ignore[reportPrivateUsage]

        # Assert
        assert isinstance(model, ConferenceModel)
        assert model.id == 1
        assert model.name == "本会議"
        assert model.governing_body_id == 10
        assert model.prefecture == "東京都"

    def test_update_model(
        self, repository: ConferenceRepositoryImpl, sample_conference_entity: Conference
    ) -> None:
        """Test _update_model updates model fields from entity."""
        # Create model with different values
        model = ConferenceModel(
            id=1,
            name="旧会議",
            governing_body_id=5,
            prefecture=None,
        )

        # Update model
        repository._update_model(model, sample_conference_entity)  # type: ignore[reportPrivateUsage]

        # Assert
        assert model.name == "本会議"
        assert model.governing_body_id == 10
        assert model.prefecture == "東京都"

    def test_dict_to_entity(
        self,
        repository: ConferenceRepositoryImpl,
        sample_conference_dict: dict[str, Any],
    ) -> None:
        """Test _dict_to_entity converts dictionary to entity correctly."""
        # Convert
        entity = repository._dict_to_entity(sample_conference_dict)  # type: ignore[reportPrivateUsage]

        # Assert
        assert isinstance(entity, Conference)
        assert entity.id == 1
        assert entity.name == "本会議"
        assert entity.governing_body_id == 10
        assert entity.prefecture == "東京都"

    def test_dict_to_entity_with_missing_optional_fields(
        self, repository: ConferenceRepositoryImpl
    ) -> None:
        """Test _dict_to_entity handles missing optional fields."""
        # Dictionary with only required fields
        data: dict[str, Any] = {
            "name": "本会議",
            "governing_body_id": 10,
        }

        # Convert
        entity = repository._dict_to_entity(data)  # type: ignore[reportPrivateUsage]

        # Assert
        assert isinstance(entity, Conference)
        assert entity.id is None
        assert entity.name == "本会議"
        assert entity.governing_body_id == 10
        assert entity.prefecture is None

    def test_dict_to_entity_with_prefecture_zenkoku(
        self, repository: ConferenceRepositoryImpl
    ) -> None:
        """Test _dict_to_entity handles 全国 (national parliament) prefecture."""
        # Dictionary with prefecture set to "全国"
        data: dict[str, Any] = {
            "id": 1,
            "name": "衆議院本会議",
            "governing_body_id": 1,
            "prefecture": "全国",
        }

        # Convert
        entity = repository._dict_to_entity(data)  # type: ignore[reportPrivateUsage]

        # Assert
        assert entity.prefecture == "全国"

    @pytest.mark.asyncio
    async def test_create_conference_with_prefecture(
        self,
        repository: ConferenceRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test creating a conference with prefecture field."""
        # Create entity with prefecture
        entity = Conference(
            name="東京都議会",
            governing_body_id=13,
            prefecture="東京都",
        )

        # Setup mock result for RETURNING *
        created_dict = {
            "id": 1,
            "name": "東京都議会",
            "governing_body_id": 13,
            "prefecture": "東京都",
            "term": None,
            "created_at": None,
            "updated_at": None,
        }
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(return_value=created_dict)
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.create(entity)

        # Assert
        assert result.id == 1
        assert result.prefecture == "東京都"
        mock_session.execute.assert_called()
        # Verify the SQL query includes prefecture
        call_args = mock_session.execute.call_args
        assert "prefecture" in call_args[0][0].text

    @pytest.mark.asyncio
    async def test_update_conference_prefecture(
        self,
        repository: ConferenceRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test updating conference prefecture field."""
        # Create entity with updated prefecture
        entity = Conference(
            id=1,
            name="東京都議会",
            governing_body_id=13,
            prefecture="東京都",
        )

        # Setup mock result for RETURNING *
        updated_dict = {
            "id": 1,
            "name": "東京都議会",
            "governing_body_id": 13,
            "prefecture": "東京都",
            "term": None,
            "created_at": None,
            "updated_at": None,
        }
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(return_value=updated_dict)
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.update(entity)

        # Assert
        assert result.prefecture == "東京都"
        mock_session.execute.assert_called()
        # Verify the SQL query includes prefecture
        call_args = mock_session.execute.call_args
        assert "prefecture" in call_args[0][0].text

    @pytest.mark.asyncio
    async def test_get_by_name_and_governing_body_with_term(
        self,
        repository: ConferenceRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_name_and_governing_body with term parameter."""
        # Setup mock result
        conference_dict = {
            "id": 1,
            "name": "衆議院本会議",
            "governing_body_id": 1,
            "prefecture": "全国",
            "term": "第220回",
            "created_at": None,
            "updated_at": None,
        }
        mock_row = MagicMock()
        mock_row._mapping = conference_dict
        mock_row._asdict = MagicMock(return_value=conference_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute with term
        result = await repository.get_by_name_and_governing_body(
            "衆議院本会議", 1, term="第220回"
        )

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.name == "衆議院本会議"
        assert result.term == "第220回"
        mock_session.execute.assert_called_once()
        # Verify the SQL query includes term condition
        call_args = mock_session.execute.call_args
        assert "term = :term" in call_args[0][0].text
        assert call_args[0][1]["term"] == "第220回"

    @pytest.mark.asyncio
    async def test_get_by_name_and_governing_body_with_term_none(
        self,
        repository: ConferenceRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_name_and_governing_body with term=None searches for NULL term."""
        # Setup mock result
        conference_dict = {
            "id": 1,
            "name": "委員会",
            "governing_body_id": 1,
            "prefecture": "東京都",
            "term": None,
            "created_at": None,
            "updated_at": None,
        }
        mock_row = MagicMock()
        mock_row._mapping = conference_dict
        mock_row._asdict = MagicMock(return_value=conference_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute without term (term=None)
        result = await repository.get_by_name_and_governing_body("委員会", 1)

        # Assert
        assert result is not None
        assert result.term is None
        mock_session.execute.assert_called_once()
        # Verify the SQL query uses term IS NULL condition
        call_args = mock_session.execute.call_args
        assert "term IS NULL" in call_args[0][0].text

    @pytest.mark.asyncio
    async def test_create_conference_with_term(
        self,
        repository: ConferenceRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test creating a conference with term field."""
        # Create entity with term
        entity = Conference(
            name="衆議院本会議",
            governing_body_id=1,
            term="第220回",
        )

        # Setup mock result for RETURNING *
        created_dict = {
            "id": 1,
            "name": "衆議院本会議",
            "governing_body_id": 1,
            "prefecture": None,
            "term": "第220回",
            "created_at": None,
            "updated_at": None,
        }
        mock_row = MagicMock()
        mock_row._asdict = MagicMock(return_value=created_dict)
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.create(entity)

        # Assert
        assert result.id == 1
        assert result.term == "第220回"
        mock_session.execute.assert_called()
        # Verify the SQL query includes term
        call_args = mock_session.execute.call_args
        assert "term" in call_args[0][0].text

    def test_to_entity_with_term(self, repository: ConferenceRepositoryImpl) -> None:
        """Test _to_entity converts model with term to entity correctly."""
        # Create model with term
        model = ConferenceModel(
            id=1,
            name="衆議院本会議",
            governing_body_id=1,
            prefecture="全国",
            term="第220回",
        )

        # Convert
        entity = repository._to_entity(model)  # type: ignore[reportPrivateUsage]

        # Assert
        assert isinstance(entity, Conference)
        assert entity.term == "第220回"

    def test_to_model_with_term(self, repository: ConferenceRepositoryImpl) -> None:
        """Test _to_model converts entity with term to model correctly."""
        # Create entity with term
        entity = Conference(
            id=1,
            name="衆議院本会議",
            governing_body_id=1,
            term="第220回",
        )

        # Convert
        model = repository._to_model(entity)  # type: ignore[reportPrivateUsage]

        # Assert
        assert isinstance(model, ConferenceModel)
        assert model.term == "第220回"

    def test_dict_to_entity_with_term(
        self, repository: ConferenceRepositoryImpl
    ) -> None:
        """Test _dict_to_entity handles term field."""
        # Dictionary with term
        data: dict[str, Any] = {
            "id": 1,
            "name": "衆議院本会議",
            "governing_body_id": 1,
            "prefecture": "全国",
            "term": "第220回",
        }

        # Convert
        entity = repository._dict_to_entity(data)  # type: ignore[reportPrivateUsage]

        # Assert
        assert entity.term == "第220回"

    def test_update_model_with_term(self, repository: ConferenceRepositoryImpl) -> None:
        """Test _update_model updates term field from entity."""
        # Create model without term
        model = ConferenceModel(
            id=1,
            name="衆議院本会議",
            governing_body_id=1,
            prefecture=None,
            term=None,
        )

        # Create entity with term
        entity = Conference(
            id=1,
            name="衆議院本会議",
            governing_body_id=1,
            term="第220回",
        )

        # Update model
        repository._update_model(model, entity)  # type: ignore[reportPrivateUsage]

        # Assert
        assert model.term == "第220回"
