"""SQLAlchemyを使用した選挙リポジトリの実装."""

import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.election import Election
from src.domain.repositories.election_repository import ElectionRepository
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.infrastructure.persistence.sqlalchemy_models import (
    ElectionModel,
)


logger = logging.getLogger(__name__)


class ElectionRepositoryImpl(BaseRepositoryImpl[Election], ElectionRepository):
    """SQLAlchemyを使用した選挙リポジトリの実装."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(
            session=session,
            entity_class=Election,
            model_class=ElectionModel,
        )

    async def get_by_governing_body(self, governing_body_id: int) -> list[Election]:
        """開催主体に属する全選挙を取得."""
        query = (
            select(self.model_class)
            .where(self.model_class.governing_body_id == governing_body_id)
            .order_by(self.model_class.election_date.desc())
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def get_by_governing_body_and_term(
        self, governing_body_id: int, term_number: int
    ) -> Election | None:
        """開催主体と期番号で選挙を取得."""
        query = select(self.model_class).where(
            self.model_class.governing_body_id == governing_body_id,
            self.model_class.term_number == term_number,
        )
        result = await self.session.execute(query)
        model = result.scalars().first()
        if model:
            return self._to_entity(model)
        return None

    async def delete(self, entity_id: int) -> bool:
        """選挙を削除（関連する会議体がある場合は削除不可）."""
        check_query = text(
            "SELECT COUNT(*) FROM conferences WHERE election_id = :election_id"
        )
        result = await self.session.execute(check_query, {"election_id": entity_id})
        conferences_count = result.scalar()

        if conferences_count and conferences_count > 0:
            return False

        model = await self.session.get(self.model_class, entity_id)
        if not model:
            return False

        await self.session.delete(model)
        await self.session.flush()
        return True

    def _to_entity(self, model: ElectionModel) -> Election:
        return Election(
            id=model.id,
            governing_body_id=model.governing_body_id,
            term_number=model.term_number,
            election_date=model.election_date,
            election_type=model.election_type,
        )

    def _to_model(self, entity: Election) -> ElectionModel:
        return ElectionModel(
            id=entity.id,
            governing_body_id=entity.governing_body_id,
            term_number=entity.term_number,
            election_date=entity.election_date,
            election_type=entity.election_type,
        )

    def _update_model(self, model: ElectionModel, entity: Election) -> None:
        model.governing_body_id = entity.governing_body_id
        model.term_number = entity.term_number
        model.election_date = entity.election_date
        model.election_type = entity.election_type
