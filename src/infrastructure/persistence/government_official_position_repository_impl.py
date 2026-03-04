"""GovernmentOfficialPosition repository implementation."""

from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.government_official_position import GovernmentOfficialPosition
from src.domain.repositories.government_official_position_repository import (
    GovernmentOfficialPositionRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.infrastructure.persistence.sqlalchemy_models import (
    GovernmentOfficialPositionModel,
)


class GovernmentOfficialPositionRepositoryImpl(
    BaseRepositoryImpl[GovernmentOfficialPosition],
    GovernmentOfficialPositionRepository,
):
    """SQLAlchemy ORM実装の政府関係者役職履歴リポジトリ."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(
            session=session,
            entity_class=GovernmentOfficialPosition,
            model_class=GovernmentOfficialPositionModel,
        )

    def _to_entity(
        self, model: GovernmentOfficialPositionModel
    ) -> GovernmentOfficialPosition:
        entity = GovernmentOfficialPosition(
            id=model.id,
            government_official_id=model.government_official_id,
            organization=model.organization,
            position=model.position,
            start_date=model.start_date,
            end_date=model.end_date,
            source_note=model.source_note,
        )
        entity.created_at = model.created_at
        entity.updated_at = model.updated_at
        return entity

    def _to_model(
        self, entity: GovernmentOfficialPosition
    ) -> GovernmentOfficialPositionModel:
        return GovernmentOfficialPositionModel(
            id=entity.id,
            government_official_id=entity.government_official_id,
            organization=entity.organization,
            position=entity.position,
            start_date=entity.start_date,
            end_date=entity.end_date,
            source_note=entity.source_note,
        )

    def _update_model(
        self,
        model: GovernmentOfficialPositionModel,
        entity: GovernmentOfficialPosition,
    ) -> None:
        model.government_official_id = entity.government_official_id
        model.organization = entity.organization
        model.position = entity.position
        model.start_date = entity.start_date
        model.end_date = entity.end_date
        model.source_note = entity.source_note

    async def get_by_official(
        self, government_official_id: int
    ) -> list[GovernmentOfficialPosition]:
        query = select(GovernmentOfficialPositionModel).where(
            GovernmentOfficialPositionModel.government_official_id
            == government_official_id
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_active_by_official(
        self, government_official_id: int, as_of_date: date | None = None
    ) -> list[GovernmentOfficialPosition]:
        query = select(GovernmentOfficialPositionModel).where(
            GovernmentOfficialPositionModel.government_official_id
            == government_official_id
        )
        if as_of_date is not None:
            query = query.where(
                and_(
                    (
                        GovernmentOfficialPositionModel.start_date.is_(None)
                        | (GovernmentOfficialPositionModel.start_date <= as_of_date)
                    ),
                    (
                        GovernmentOfficialPositionModel.end_date.is_(None)
                        | (GovernmentOfficialPositionModel.end_date >= as_of_date)
                    ),
                )
            )
        else:
            query = query.where(GovernmentOfficialPositionModel.end_date.is_(None))

        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def bulk_upsert(
        self, positions: list[GovernmentOfficialPosition]
    ) -> list[GovernmentOfficialPosition]:
        results: list[GovernmentOfficialPosition] = []
        for pos in positions:
            conditions = [
                GovernmentOfficialPositionModel.government_official_id
                == pos.government_official_id,
                GovernmentOfficialPositionModel.organization == pos.organization,
                GovernmentOfficialPositionModel.position == pos.position,
            ]
            if pos.start_date is not None:
                conditions.append(
                    GovernmentOfficialPositionModel.start_date == pos.start_date
                )
            else:
                conditions.append(GovernmentOfficialPositionModel.start_date.is_(None))

            query = select(GovernmentOfficialPositionModel).where(and_(*conditions))
            result = await self.session.execute(query)
            existing = result.scalars().first()

            if existing:
                existing.end_date = pos.end_date
                existing.source_note = pos.source_note
                await self.session.flush()
                await self.session.refresh(existing)
                results.append(self._to_entity(existing))
            else:
                entity = await self.create(pos)
                results.append(entity)

        return results
