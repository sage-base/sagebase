"""会派⇔政党の多対多関連リポジトリ実装."""

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.parliamentary_group_party import ParliamentaryGroupParty
from src.domain.repositories.parliamentary_group_party_repository import (
    ParliamentaryGroupPartyRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.infrastructure.persistence.sqlalchemy_models import (
    ParliamentaryGroupPartyModel,
)


class ParliamentaryGroupPartyRepositoryImpl(
    BaseRepositoryImpl[ParliamentaryGroupParty],
    ParliamentaryGroupPartyRepository,
):
    """会派⇔政党の多対多関連リポジトリ実装（SQLAlchemy ORM）."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(
            session=session,
            entity_class=ParliamentaryGroupParty,
            model_class=ParliamentaryGroupPartyModel,
        )

    async def get_by_parliamentary_group_id(
        self, group_id: int
    ) -> list[ParliamentaryGroupParty]:
        query = select(self.model_class).where(
            self.model_class.parliamentary_group_id == group_id
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def get_by_parliamentary_group_ids(
        self, group_ids: list[int]
    ) -> list[ParliamentaryGroupParty]:
        if not group_ids:
            return []
        query = select(self.model_class).where(
            self.model_class.parliamentary_group_id.in_(group_ids)
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def get_by_political_party_id(
        self, party_id: int
    ) -> list[ParliamentaryGroupParty]:
        query = select(self.model_class).where(
            self.model_class.political_party_id == party_id
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def get_primary_party(self, group_id: int) -> ParliamentaryGroupParty | None:
        query = select(self.model_class).where(
            and_(
                self.model_class.parliamentary_group_id == group_id,
                self.model_class.is_primary.is_(True),
            )
        )
        result = await self.session.execute(query)
        model = result.scalars().first()
        if model is None:
            return None
        return self._to_entity(model)

    async def add_party(
        self, group_id: int, party_id: int, is_primary: bool = False
    ) -> ParliamentaryGroupParty:
        existing_query = select(self.model_class).where(
            and_(
                self.model_class.parliamentary_group_id == group_id,
                self.model_class.political_party_id == party_id,
            )
        )
        result = await self.session.execute(existing_query)
        existing_model = result.scalars().first()

        if existing_model:
            return self._to_entity(existing_model)

        new_model = self.model_class(
            parliamentary_group_id=group_id,
            political_party_id=party_id,
            is_primary=is_primary,
        )
        self.session.add(new_model)
        await self.session.flush()
        await self.session.refresh(new_model)
        return self._to_entity(new_model)

    async def remove_party(self, group_id: int, party_id: int) -> bool:
        query = select(self.model_class).where(
            and_(
                self.model_class.parliamentary_group_id == group_id,
                self.model_class.political_party_id == party_id,
            )
        )
        result = await self.session.execute(query)
        model = result.scalars().first()
        if model is None:
            return False
        await self.session.delete(model)
        await self.session.flush()
        return True

    async def set_primary(
        self, group_id: int, party_id: int
    ) -> ParliamentaryGroupParty | None:
        target_query = select(self.model_class).where(
            and_(
                self.model_class.parliamentary_group_id == group_id,
                self.model_class.political_party_id == party_id,
            )
        )
        result = await self.session.execute(target_query)
        target_model = result.scalars().first()
        if target_model is None:
            return None

        current_primary_query = select(self.model_class).where(
            and_(
                self.model_class.parliamentary_group_id == group_id,
                self.model_class.is_primary.is_(True),
            )
        )
        result = await self.session.execute(current_primary_query)
        current_primary = result.scalars().first()
        if current_primary and current_primary.id != target_model.id:
            current_primary.is_primary = False

        target_model.is_primary = True
        await self.session.flush()
        await self.session.refresh(target_model)
        return self._to_entity(target_model)

    def _to_entity(
        self, model: ParliamentaryGroupPartyModel
    ) -> ParliamentaryGroupParty:
        entity = ParliamentaryGroupParty(
            id=model.id,
            parliamentary_group_id=model.parliamentary_group_id,
            political_party_id=model.political_party_id,
            is_primary=model.is_primary,
        )
        entity.created_at = model.created_at
        entity.updated_at = model.updated_at
        return entity

    def _to_model(
        self, entity: ParliamentaryGroupParty
    ) -> ParliamentaryGroupPartyModel:
        return ParliamentaryGroupPartyModel(
            id=entity.id if entity.id is not None else 0,
            parliamentary_group_id=entity.parliamentary_group_id,
            political_party_id=entity.political_party_id,
            is_primary=entity.is_primary,
        )

    def _update_model(
        self,
        model: ParliamentaryGroupPartyModel,
        entity: ParliamentaryGroupParty,
    ) -> None:
        model.parliamentary_group_id = entity.parliamentary_group_id
        model.political_party_id = entity.political_party_id
        model.is_primary = entity.is_primary
