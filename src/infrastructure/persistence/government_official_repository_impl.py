"""GovernmentOfficial repository implementation."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.government_official import GovernmentOfficial
from src.domain.repositories.government_official_repository import (
    GovernmentOfficialRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.infrastructure.persistence.sqlalchemy_models import GovernmentOfficialModel


class GovernmentOfficialRepositoryImpl(
    BaseRepositoryImpl[GovernmentOfficial],
    GovernmentOfficialRepository,
):
    """SQLAlchemy ORM実装の政府関係者リポジトリ."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(
            session=session,
            entity_class=GovernmentOfficial,
            model_class=GovernmentOfficialModel,
        )

    def _to_entity(self, model: GovernmentOfficialModel) -> GovernmentOfficial:
        entity = GovernmentOfficial(
            id=model.id,
            name=model.name,
            name_yomi=model.name_yomi,
        )
        entity.created_at = model.created_at
        entity.updated_at = model.updated_at
        return entity

    def _to_model(self, entity: GovernmentOfficial) -> GovernmentOfficialModel:
        return GovernmentOfficialModel(
            id=entity.id,
            name=entity.name,
            name_yomi=entity.name_yomi,
        )

    def _update_model(
        self, model: GovernmentOfficialModel, entity: GovernmentOfficial
    ) -> None:
        model.name = entity.name
        model.name_yomi = entity.name_yomi

    async def get_by_name(self, name: str) -> GovernmentOfficial | None:
        query = select(GovernmentOfficialModel).where(
            GovernmentOfficialModel.name == name
        )
        result = await self.session.execute(query)
        model = result.scalars().first()
        if model:
            return self._to_entity(model)
        return None

    async def search_by_name(self, name: str) -> list[GovernmentOfficial]:
        query = select(GovernmentOfficialModel).where(
            GovernmentOfficialModel.name.ilike(f"%{name}%")
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]
