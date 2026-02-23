"""政党所属履歴リポジトリ実装."""

from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.party_membership_history import PartyMembershipHistory
from src.domain.repositories.party_membership_history_repository import (
    PartyMembershipHistoryRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.infrastructure.persistence.sqlalchemy_models import (
    PartyMembershipHistoryModel,
)


class PartyMembershipHistoryRepositoryImpl(
    BaseRepositoryImpl[PartyMembershipHistory],
    PartyMembershipHistoryRepository,
):
    """政党所属履歴リポジトリのSQLAlchemy実装."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(
            session=session,
            entity_class=PartyMembershipHistory,
            model_class=PartyMembershipHistoryModel,
        )

    async def get_by_politician(
        self, politician_id: int
    ) -> list[PartyMembershipHistory]:
        query = (
            select(self.model_class)
            .where(self.model_class.politician_id == politician_id)
            .order_by(self.model_class.start_date.desc())
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def get_by_political_party(
        self, political_party_id: int
    ) -> list[PartyMembershipHistory]:
        query = select(self.model_class).where(
            self.model_class.political_party_id == political_party_id
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def get_current_by_politician(
        self, politician_id: int, as_of_date: date | None = None
    ) -> PartyMembershipHistory | None:
        if as_of_date is None:
            as_of_date = date.today()

        query = (
            select(self.model_class)
            .where(
                and_(
                    self.model_class.politician_id == politician_id,
                    self.model_class.start_date <= as_of_date,
                    (
                        self.model_class.end_date.is_(None)
                        | (self.model_class.end_date >= as_of_date)
                    ),
                )
            )
            .order_by(self.model_class.start_date.desc())
        )
        result = await self.session.execute(query)
        model = result.scalars().first()
        if model is None:
            return None
        return self._to_entity(model)

    async def end_membership(
        self, membership_id: int, end_date: date
    ) -> PartyMembershipHistory | None:
        model = await self.session.get(self.model_class, membership_id)
        if not model:
            return None

        model.end_date = end_date
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    def _to_entity(self, model: PartyMembershipHistoryModel) -> PartyMembershipHistory:
        return PartyMembershipHistory(
            id=model.id,
            politician_id=model.politician_id,
            political_party_id=model.political_party_id,
            start_date=model.start_date,
            end_date=model.end_date,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: PartyMembershipHistory) -> PartyMembershipHistoryModel:
        return PartyMembershipHistoryModel(
            id=entity.id or 0,
            politician_id=entity.politician_id,
            political_party_id=entity.political_party_id,
            start_date=entity.start_date,
            end_date=entity.end_date,
        )

    def _update_model(
        self,
        model: PartyMembershipHistoryModel,
        entity: PartyMembershipHistory,
    ) -> None:
        model.politician_id = entity.politician_id
        model.political_party_id = entity.political_party_id
        model.start_date = entity.start_date
        model.end_date = entity.end_date
