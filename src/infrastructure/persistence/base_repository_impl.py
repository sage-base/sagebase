"""Base repository implementation for infrastructure layer."""

from typing import Any

from sqlalchemy import func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.domain.entities.base import BaseEntity
from src.domain.repositories.base import BaseRepository
from src.domain.repositories.session_adapter import ISessionAdapter


class BaseRepositoryImpl[T: BaseEntity](BaseRepository[T]):
    """Base repository implementation using ISessionAdapter.

    This class provides generic CRUD operations using the ISessionAdapter
    interface, enabling dependency inversion and testability. All operations
    use the session adapter methods, avoiding direct SQLAlchemy dependencies.

    The ISessionAdapter interface allows for flexible session management,
    supporting both async and sync sessions through adapters. This design
    follows the Dependency Inversion Principle, where the domain defines
    the interface and infrastructure provides implementations.

    Type Parameters:
        T: Domain entity type that extends BaseEntity

    Attributes:
        session: Database session (AsyncSession or ISessionAdapter)
        entity_class: Domain entity class for type conversions
        model_class: Database model class for ORM operations

    Note:
        Subclasses must implement the conversion methods:
        _to_entity(), _to_model(), and _update_model()

        非ORMモデル（Pydantic/動的モデル）を使用するリポジトリでは、
        _table_nameプロパティをオーバーライドしてテーブル名を指定すること。
        _raw_row_to_entityは既存の_row_to_entity/_dict_to_entityに自動委譲する。
    """

    def __init__(
        self,
        session: AsyncSession | ISessionAdapter,
        entity_class: type[T],
        model_class: type[Any],
    ):
        self.session = session
        self.entity_class = entity_class
        self.model_class = model_class

    @property
    def _is_orm(self) -> bool:
        """model_classがSQLAlchemy ORMマッピング済みかどうかを判定."""
        return hasattr(self.model_class, "__table__")

    @property
    def _table_name(self) -> str:
        """テーブル名を返す。非ORMの場合はサブクラスでオーバーライドすること."""
        if hasattr(self.model_class, "__tablename__"):
            return self.model_class.__tablename__
        raise NotImplementedError(
            f"{self.__class__.__name__}: model_classに__tablename__がないため、"
            f"_table_nameプロパティをオーバーライドしてください"
        )

    def _raw_row_to_entity(self, row: Any) -> T:
        """text() SQLの結果行からエンティティに変換（非ORMフォールバック用）.

        サブクラスの既存メソッドに以下の優先順位で委譲する:
        1. _row_to_entity(row) — Rowオブジェクトを直接処理
        2. _dict_to_entity(dict) — Rowをdict化して処理
        3. _to_entity(row) — 最終フォールバック
        """
        if hasattr(self, "_row_to_entity"):
            return self._row_to_entity(row)
        if hasattr(self, "_dict_to_entity"):
            if hasattr(row, "_mapping"):
                return self._dict_to_entity(dict(row._mapping))
            elif hasattr(row, "_asdict"):
                return self._dict_to_entity(row._asdict())
            return self._dict_to_entity(dict(row))
        return self._to_entity(row)

    async def get_by_id(self, entity_id: int) -> T | None:
        """Get entity by ID."""
        result = await self.session.get(self.model_class, entity_id)
        if result:
            return self._to_entity(result)
        return None

    async def get_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[T]:
        """Get all entities with optional pagination."""
        if self._is_orm:
            query = select(self.model_class)

            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            result = await self.session.execute(query)
            models = result.scalars().all()
            return [self._to_entity(model) for model in models]
        else:
            sql = f"SELECT * FROM {self._table_name}"
            params: dict[str, Any] = {}
            if limit is not None:
                sql += " LIMIT :limit"
                params["limit"] = limit
            if offset is not None:
                sql += " OFFSET :offset"
                params["offset"] = offset
            result = await self.session.execute(text(sql), params if params else None)
            return [self._raw_row_to_entity(row) for row in result.fetchall()]

    async def get_by_ids(self, entity_ids: list[int]) -> list[T]:
        """Get entities by their IDs."""
        if not entity_ids:
            return []
        if self._is_orm:
            query = select(self.model_class).where(self.model_class.id.in_(entity_ids))
            result = await self.session.execute(query)
            models = result.scalars().all()
            return [self._to_entity(model) for model in models]
        else:
            placeholders = ", ".join(f":id_{i}" for i in range(len(entity_ids)))
            query = text(
                f"SELECT * FROM {self._table_name} WHERE id IN ({placeholders})"
            )
            params = {f"id_{i}": eid for i, eid in enumerate(entity_ids)}
            result = await self.session.execute(query, params)
            return [self._raw_row_to_entity(row) for row in result.fetchall()]

    async def create(self, entity: T) -> T:
        """Create a new entity."""
        model = self._to_model(entity)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        if not entity.id:
            raise ValueError("Entity must have an ID to update")

        # Get existing model
        model = await self.session.get(self.model_class, entity.id)
        if not model:
            raise ValueError(f"Entity with ID {entity.id} not found")

        # Update fields
        self._update_model(model, entity)

        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def delete(self, entity_id: int) -> bool:
        """Delete an entity by ID."""
        model = await self.session.get(self.model_class, entity_id)
        if not model:
            return False

        await self.session.delete(model)
        await self.session.flush()
        return True

    async def count(self) -> int:
        """Count total number of entities."""
        if self._is_orm:
            query = select(func.count()).select_from(self.model_class)
        else:
            query = text(f"SELECT COUNT(*) FROM {self._table_name}")
        result = await self.session.execute(query)
        count = result.scalar()
        return count if count is not None else 0

    def _to_entity(self, model: Any) -> T:
        """Convert database model to domain entity."""
        raise NotImplementedError("Subclass must implement _to_entity")

    def _to_model(self, entity: T) -> Any:
        """Convert domain entity to database model."""
        raise NotImplementedError("Subclass must implement _to_model")

    def _update_model(self, model: Any, entity: T) -> None:
        """Update model fields from entity."""
        raise NotImplementedError("Subclass must implement _update_model")
