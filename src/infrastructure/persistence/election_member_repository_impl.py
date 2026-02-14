"""SQLAlchemyを使用した選挙結果メンバーリポジトリの実装."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.election_member import ElectionMember
from src.domain.repositories.election_member_repository import ElectionMemberRepository
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.infrastructure.persistence.sqlalchemy_models import (
    ElectionMemberModel,
)


class ElectionMemberRepositoryImpl(
    BaseRepositoryImpl[ElectionMember], ElectionMemberRepository
):
    """SQLAlchemyを使用した選挙結果メンバーリポジトリの実装."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(
            session=session,
            entity_class=ElectionMember,
            model_class=ElectionMemberModel,
        )

    async def get_by_election_id(self, election_id: int) -> list[ElectionMember]:
        """選挙IDに属する全メンバーを取得."""
        query = (
            select(self.model_class)
            .where(self.model_class.election_id == election_id)
            .order_by(
                self.model_class.rank.asc().nulls_last(),
                self.model_class.id.asc(),
            )
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def get_by_politician_id(self, politician_id: int) -> list[ElectionMember]:
        """政治家IDに紐づく全選挙結果を取得."""
        query = (
            select(self.model_class)
            .where(self.model_class.politician_id == politician_id)
            .order_by(self.model_class.id.asc())
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def delete_by_election_id(self, election_id: int) -> int:
        """選挙IDに属する全メンバーを削除."""
        query = delete(self.model_class).where(
            self.model_class.election_id == election_id
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.rowcount

    async def delete_by_election_id_and_results(
        self, election_id: int, results: list[str]
    ) -> int:
        """選挙IDおよび結果値に一致するメンバーを削除."""
        query = delete(self.model_class).where(
            self.model_class.election_id == election_id,
            self.model_class.result.in_(results),
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.rowcount

    def _to_entity(self, model: ElectionMemberModel) -> ElectionMember:
        return ElectionMember(
            id=model.id,
            election_id=model.election_id,
            politician_id=model.politician_id,
            result=model.result,
            votes=model.votes,
            rank=model.rank,
        )

    def _to_model(self, entity: ElectionMember) -> ElectionMemberModel:
        return ElectionMemberModel(
            election_id=entity.election_id,
            politician_id=entity.politician_id,
            result=entity.result,
            votes=entity.votes,
            rank=entity.rank,
        )

    def _update_model(self, model: ElectionMemberModel, entity: ElectionMember) -> None:
        model.election_id = entity.election_id
        model.politician_id = entity.politician_id
        model.result = entity.result
        model.votes = entity.votes
        model.rank = entity.rank
