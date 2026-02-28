"""Tests for BaseRepositoryImpl."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.base import BaseEntity
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


# --- ORM用モック ---


class MockEntity(BaseEntity):
    """Mock entity for testing BaseRepositoryImpl."""

    def __init__(self, id: int | None = None, name: str = ""):
        super().__init__(id=id)
        self.name = name


class MockModel:
    """Mock model for testing BaseRepositoryImpl (ORM系)."""

    # ORM判定用属性
    __tablename__ = "mock_model"
    __table__ = True

    def __init__(self, id: int | None = None, name: str = ""):
        self.id = id
        self.name = name


class MockRepositoryImpl(BaseRepositoryImpl[MockEntity]):
    """ORM系テストリポジトリ."""

    def _to_entity(self, model) -> MockEntity:
        return MockEntity(id=model.id, name=model.name)

    def _to_model(self, entity: MockEntity):
        return MockModel(id=entity.id, name=entity.name)

    def _update_model(self, model, entity: MockEntity):
        model.name = entity.name


# --- 非ORM用モック ---


class NonOrmMockModel:
    """非ORMモデル（__table__を持たない）."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class NonOrmMockRepositoryImpl(BaseRepositoryImpl[MockEntity]):
    """非ORMテストリポジトリ（_row_to_entity使用）."""

    @property
    def _table_name(self) -> str:
        return "mock_entities"

    def _to_entity(self, model) -> MockEntity:
        return MockEntity(id=model.id, name=model.name)

    def _row_to_entity(self, row) -> MockEntity:
        if hasattr(row, "_mapping"):
            d = dict(row._mapping)
        else:
            d = {"id": getattr(row, "id", None), "name": getattr(row, "name", "")}
        return MockEntity(id=d.get("id"), name=d.get("name", ""))

    def _to_model(self, entity: MockEntity):
        return NonOrmMockModel(id=entity.id, name=entity.name)

    def _update_model(self, model, entity: MockEntity):
        model.name = entity.name


class NonOrmNoTableNameModel:
    """非ORMモデル（__tablename__も持たない）."""

    pass


class NonOrmNoTableNameRepositoryImpl(BaseRepositoryImpl[MockEntity]):
    """_table_nameをオーバーライドしない非ORMリポジトリ."""

    def _to_entity(self, model) -> MockEntity:
        return MockEntity(id=model.id, name=model.name)

    def _to_model(self, entity: MockEntity):
        return NonOrmNoTableNameModel()

    def _update_model(self, model, entity: MockEntity):
        pass


# --- ORM系テスト ---


class TestBaseRepositoryImplOrm:
    """ORM系BaseRepositoryImplのテスト."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def repository(self, mock_session):
        return MockRepositoryImpl(mock_session, MockEntity, MockModel)

    @pytest.mark.asyncio
    async def test_is_orm_true(self, repository):
        """ORM model_classで_is_ormがTrueになることを確認."""
        assert repository._is_orm is True

    @pytest.mark.asyncio
    async def test_table_name_from_tablename(self, repository):
        """__tablename__属性からテーブル名を取得できることを確認."""
        assert repository._table_name == "mock_model"

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_session):
        mock_model = MockModel(id=1, name="Test")
        mock_session.get.return_value = mock_model

        result = await repository.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.name == "Test"
        mock_session.get.assert_called_once_with(MockModel, 1)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_session):
        mock_session.get.return_value = None

        result = await repository.get_by_id(999)

        assert result is None
        mock_session.get.assert_called_once_with(MockModel, 999)

    @pytest.mark.asyncio
    @patch("src.infrastructure.persistence.base_repository_impl.select")
    async def test_get_all(self, mock_select, repository, mock_session):
        mock_models = [
            MockModel(id=1, name="Test1"),
            MockModel(id=2, name="Test2"),
        ]

        mock_query = MagicMock()
        mock_select.return_value = mock_query

        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = mock_models

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars_result)

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute

        result = await repository.get_all()

        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].name == "Test1"
        assert result[1].id == 2
        assert result[1].name == "Test2"
        mock_select.assert_called_once_with(MockModel)

    @pytest.mark.asyncio
    @patch("src.infrastructure.persistence.base_repository_impl.select")
    async def test_get_all_with_pagination(self, mock_select, repository, mock_session):
        mock_models = [MockModel(id=3, name="Test3")]

        mock_query = MagicMock()
        mock_query.offset = MagicMock(return_value=mock_query)
        mock_query.limit = MagicMock(return_value=mock_query)
        mock_select.return_value = mock_query

        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = mock_models

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars_result)

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute

        result = await repository.get_all(limit=10, offset=20)

        assert len(result) == 1
        assert result[0].id == 3
        assert result[0].name == "Test3"
        mock_select.assert_called_once_with(MockModel)
        mock_query.offset.assert_called_once_with(20)
        mock_query.limit.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_create(self, repository, mock_session):
        entity = MockEntity(name="New Entity")

        async def refresh_side_effect(model):
            model.id = 5

        mock_session.refresh.side_effect = refresh_side_effect

        result = await repository.create(entity)

        assert result.id == 5
        assert result.name == "New Entity"
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_success(self, repository, mock_session):
        entity = MockEntity(id=1, name="Updated Entity")
        existing_model = MockModel(id=1, name="Old Entity")
        mock_session.get.return_value = existing_model

        result = await repository.update(entity)

        assert result.id == 1
        assert result.name == "Updated Entity"
        assert existing_model.name == "Updated Entity"
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_no_id_error(self, repository):
        entity = MockEntity(name="No ID Entity")

        with pytest.raises(ValueError) as exc_info:
            await repository.update(entity)

        assert "Entity must have an ID to update" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_not_found_error(self, repository, mock_session):
        entity = MockEntity(id=999, name="Not Found")
        mock_session.get.return_value = None

        with pytest.raises(ValueError) as exc_info:
            await repository.update(entity)

        assert "Entity with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_success(self, repository, mock_session):
        model = MockModel(id=1, name="To Delete")
        mock_session.get.return_value = model

        result = await repository.delete(1)

        assert result is True
        mock_session.delete.assert_called_once_with(model)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_session):
        mock_session.get.return_value = None

        result = await repository.delete(999)

        assert result is False
        mock_session.delete.assert_not_called()
        mock_session.flush.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.infrastructure.persistence.base_repository_impl.func")
    @patch("src.infrastructure.persistence.base_repository_impl.select")
    async def test_count_orm(self, mock_select, mock_func, repository, mock_session):
        """ORM系のcount()がselect(func.count())を使うことを確認."""
        mock_count_expr = MagicMock()
        mock_func.count.return_value = mock_count_expr
        mock_query = MagicMock()
        mock_count_expr_select = MagicMock()
        mock_select.return_value = mock_count_expr_select
        mock_count_expr_select.select_from.return_value = mock_query

        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=42)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 42
        mock_session.execute.assert_called_once()
        mock_select.assert_called_once_with(mock_count_expr)
        mock_count_expr_select.select_from.assert_called_once_with(MockModel)


# --- 非ORM系テスト ---


class TestBaseRepositoryImplNonOrm:
    """非ORM系BaseRepositoryImplのテスト."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def repository(self, mock_session):
        return NonOrmMockRepositoryImpl(mock_session, MockEntity, NonOrmMockModel)

    @pytest.mark.asyncio
    async def test_is_orm_false(self, repository):
        """非ORM model_classで_is_ormがFalseになることを確認."""
        assert repository._is_orm is False

    @pytest.mark.asyncio
    async def test_table_name_override(self, repository):
        """_table_nameプロパティのオーバーライドからテーブル名を取得できることを確認."""
        assert repository._table_name == "mock_entities"

    @pytest.mark.asyncio
    async def test_table_name_not_implemented(self, mock_session):
        """__tablename__もオーバーライドもない場合にNotImplementedErrorが発生することを確認."""
        repo = NonOrmNoTableNameRepositoryImpl(
            mock_session, MockEntity, NonOrmNoTableNameModel
        )
        with pytest.raises(NotImplementedError):
            _ = repo._table_name

    @pytest.mark.asyncio
    async def test_count_non_orm(self, repository, mock_session):
        """非ORM系のcount()がtext() SQLフォールバックを使うことを確認."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=100)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 100
        mock_session.execute.assert_called_once()
        # text() SQLが呼ばれていることを確認
        call_args = mock_session.execute.call_args
        executed_query = call_args[0][0]
        assert "SELECT COUNT(*) FROM mock_entities" in str(executed_query)

    @pytest.mark.asyncio
    async def test_count_non_orm_none_result(self, repository, mock_session):
        """scalar()がNoneを返す場合に0が返ることを確認."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_by_ids_non_orm(self, repository, mock_session):
        """非ORM系のget_by_ids()がtext() SQLフォールバックを使うことを確認."""
        mock_row1 = MagicMock()
        mock_row1.id = 1
        mock_row1.name = "Entity1"
        mock_row1._mapping = None
        del mock_row1._mapping

        mock_row2 = MagicMock()
        mock_row2.id = 2
        mock_row2.name = "Entity2"
        mock_row2._mapping = None
        del mock_row2._mapping

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row1, mock_row2])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_ids([1, 2])

        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].name == "Entity1"
        assert result[1].id == 2
        assert result[1].name == "Entity2"
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        executed_query = call_args[0][0]
        assert "SELECT * FROM mock_entities WHERE id IN" in str(executed_query)

    @pytest.mark.asyncio
    async def test_get_by_ids_non_orm_empty(self, repository, mock_session):
        """空リスト入力で空リストが返ることを確認."""
        result = await repository.get_by_ids([])

        assert result == []
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_all_non_orm(self, repository, mock_session):
        """非ORM系のget_all()がtext() SQLフォールバックを使うことを確認."""
        mock_row1 = MagicMock()
        mock_row1.id = 1
        mock_row1.name = "Entity1"
        mock_row1._mapping = None
        del mock_row1._mapping

        mock_row2 = MagicMock()
        mock_row2.id = 2
        mock_row2.name = "Entity2"
        mock_row2._mapping = None
        del mock_row2._mapping

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row1, mock_row2])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].name == "Entity1"
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        executed_query = call_args[0][0]
        assert "SELECT * FROM mock_entities" in str(executed_query)

    @pytest.mark.asyncio
    async def test_get_all_non_orm_with_pagination(self, repository, mock_session):
        """非ORM系のget_all()でLIMIT/OFFSETが付与されることを確認."""
        mock_row = MagicMock()
        mock_row.id = 3
        mock_row.name = "Entity3"
        mock_row._mapping = None
        del mock_row._mapping

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all(limit=10, offset=20)

        assert len(result) == 1
        assert result[0].id == 3
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        executed_query = str(call_args[0][0])
        assert "LIMIT" in executed_query
        assert "OFFSET" in executed_query
        # パラメータが渡されていることを確認
        params = call_args[0][1]
        assert params["limit"] == 10
        assert params["offset"] == 20


# --- _raw_row_to_entity委譲テスト ---


class TestRawRowToEntity:
    """_raw_row_to_entityの委譲ロジックのテスト."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)

    def test_delegates_to_row_to_entity(self, mock_session):
        """_row_to_entityが定義されている場合、そちらに委譲されることを確認."""
        repo = NonOrmMockRepositoryImpl(mock_session, MockEntity, NonOrmMockModel)
        mock_row = MagicMock()
        mock_row.id = 5
        mock_row.name = "Test"
        # _mappingを削除してgetattr fallbackを使わせる
        mock_row._mapping = None
        del mock_row._mapping

        result = repo._raw_row_to_entity(mock_row)

        assert result.id == 5
        assert result.name == "Test"

    def test_delegates_to_dict_to_entity(self, mock_session):
        """_dict_to_entityが定義されている場合、Rowをdict化して委譲されることを確認."""

        class DictBasedRepositoryImpl(BaseRepositoryImpl[MockEntity]):
            @property
            def _table_name(self) -> str:
                return "test"

            def _dict_to_entity(self, data: dict) -> MockEntity:
                return MockEntity(id=data.get("id"), name=data.get("name", ""))

            def _to_entity(self, model) -> MockEntity:
                return MockEntity(id=model.id, name=model.name)

            def _to_model(self, entity):
                pass

            def _update_model(self, model, entity):
                pass

        repo = DictBasedRepositoryImpl(mock_session, MockEntity, NonOrmMockModel)
        mock_row = MagicMock()
        mock_row._mapping = {"id": 10, "name": "DictTest"}

        result = repo._raw_row_to_entity(mock_row)

        assert result.id == 10
        assert result.name == "DictTest"

    def test_fallback_to_to_entity(self, mock_session):
        """_row_to_entityも_dict_to_entityもない場合、_to_entityにフォールバックすることを確認."""

        class MinimalRepositoryImpl(BaseRepositoryImpl[MockEntity]):
            @property
            def _table_name(self) -> str:
                return "test"

            def _to_entity(self, model) -> MockEntity:
                return MockEntity(id=model.id, name=model.name)

            def _to_model(self, entity):
                pass

            def _update_model(self, model, entity):
                pass

        repo = MinimalRepositoryImpl(mock_session, MockEntity, NonOrmMockModel)
        mock_row = MagicMock()
        mock_row.id = 7
        mock_row.name = "Fallback"

        result = repo._raw_row_to_entity(mock_row)

        assert result.id == 7
        assert result.name == "Fallback"
