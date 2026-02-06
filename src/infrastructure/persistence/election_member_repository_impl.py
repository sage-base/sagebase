"""SQLAlchemyを使用した選挙結果メンバーリポジトリの実装."""

import logging

from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.election_member import ElectionMember
from src.domain.repositories.election_member_repository import ElectionMemberRepository
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.exceptions import (
    DatabaseError,
    UpdateError,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


logger = logging.getLogger(__name__)


class ElectionMemberModel(PydanticBaseModel):
    """選挙結果メンバーのデータベースモデル."""

    id: int | None = None
    election_id: int
    politician_id: int
    result: str
    votes: int | None = None
    rank: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        arbitrary_types_allowed = True


class ElectionMemberRepositoryImpl(
    BaseRepositoryImpl[ElectionMember], ElectionMemberRepository
):
    """SQLAlchemyを使用した選挙結果メンバーリポジトリの実装."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """リポジトリを初期化する.

        Args:
            session: データベース操作用のAsyncSession
        """
        super().__init__(
            session=session,
            entity_class=ElectionMember,
            model_class=ElectionMemberModel,
        )

    async def get_by_election_id(self, election_id: int) -> list[ElectionMember]:
        """選挙IDに属する全メンバーを取得.

        Args:
            election_id: 選挙ID

        Returns:
            選挙結果メンバーエンティティのリスト
        """
        try:
            query = text("""
                SELECT
                    id,
                    election_id,
                    politician_id,
                    result,
                    votes,
                    rank,
                    created_at,
                    updated_at
                FROM election_members
                WHERE election_id = :election_id
                ORDER BY rank ASC NULLS LAST, id ASC
            """)

            result = await self.session.execute(query, {"election_id": election_id})
            rows = result.fetchall()

            results = []
            for row in rows:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                results.append(self._dict_to_entity(row_dict))
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error getting election members by election: {e}")
            raise DatabaseError(
                "Failed to get election members by election",
                {"election_id": election_id, "error": str(e)},
            ) from e

    async def get_by_politician_id(self, politician_id: int) -> list[ElectionMember]:
        """政治家IDに紐づく全選挙結果を取得.

        Args:
            politician_id: 政治家ID

        Returns:
            選挙結果メンバーエンティティのリスト
        """
        try:
            query = text("""
                SELECT
                    id,
                    election_id,
                    politician_id,
                    result,
                    votes,
                    rank,
                    created_at,
                    updated_at
                FROM election_members
                WHERE politician_id = :politician_id
                ORDER BY id ASC
            """)

            result = await self.session.execute(query, {"politician_id": politician_id})
            rows = result.fetchall()

            results = []
            for row in rows:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                results.append(self._dict_to_entity(row_dict))
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error getting election members by politician: {e}")
            raise DatabaseError(
                "Failed to get election members by politician",
                {"politician_id": politician_id, "error": str(e)},
            ) from e

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[ElectionMember]:
        """全選挙結果メンバーを取得.

        Args:
            limit: 最大取得件数
            offset: スキップ件数

        Returns:
            選挙結果メンバーエンティティのリスト
        """
        try:
            query_text = """
                SELECT
                    em.id,
                    em.election_id,
                    em.politician_id,
                    em.result,
                    em.votes,
                    em.rank,
                    em.created_at,
                    em.updated_at
                FROM election_members em
                ORDER BY em.election_id, em.rank ASC NULLS LAST, em.id
            """

            params: dict[str, int | None] = {}
            if limit is not None:
                query_text += " LIMIT :limit OFFSET :offset"
                params = {"limit": limit, "offset": offset or 0}

            result = await self.session.execute(text(query_text), params)
            rows = result.fetchall()

            results = []
            for row in rows:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                results.append(self._dict_to_entity(row_dict))
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error getting all election members: {e}")
            raise DatabaseError(
                "Failed to get all election members", {"error": str(e)}
            ) from e

    async def get_by_id(self, entity_id: int) -> ElectionMember | None:
        """IDで選挙結果メンバーを取得.

        Args:
            entity_id: 選挙結果メンバーID

        Returns:
            選挙結果メンバーエンティティ、見つからない場合はNone
        """
        try:
            query = text("""
                SELECT
                    id,
                    election_id,
                    politician_id,
                    result,
                    votes,
                    rank,
                    created_at,
                    updated_at
                FROM election_members
                WHERE id = :id
            """)

            result = await self.session.execute(query, {"id": entity_id})
            row = result.first()

            if row:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)
            return None

        except SQLAlchemyError as e:
            logger.error(f"Database error getting election member by ID: {e}")
            raise DatabaseError(
                "Failed to get election member by ID",
                {"id": entity_id, "error": str(e)},
            ) from e

    async def create(self, entity: ElectionMember) -> ElectionMember:
        """選挙結果メンバーを作成.

        Args:
            entity: 作成する選挙結果メンバーエンティティ

        Returns:
            ID付きの作成済み選挙結果メンバーエンティティ
        """
        try:
            query = text("""
                INSERT INTO election_members (
                    election_id, politician_id,
                    result, votes, rank,
                    created_at, updated_at
                )
                VALUES (
                    :election_id, :politician_id,
                    :result, :votes, :rank,
                    :created_at, :updated_at
                )
                RETURNING *
            """)

            params = {
                "election_id": entity.election_id,
                "politician_id": entity.politician_id,
                "result": entity.result,
                "votes": entity.votes,
                "rank": entity.rank,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

            result = await self.session.execute(query, params)
            await self.session.commit()

            row = result.first()
            if row:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)
            raise RuntimeError("Failed to create election member")

        except SQLAlchemyError as e:
            logger.error(f"Database error creating election member: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to create election member",
                {"entity": str(entity), "error": str(e)},
            ) from e

    async def update(self, entity: ElectionMember) -> ElectionMember:
        """選挙結果メンバーを更新.

        Args:
            entity: 更新する選挙結果メンバーエンティティ

        Returns:
            更新済み選挙結果メンバーエンティティ
        """
        try:
            query = text("""
                UPDATE election_members
                SET election_id = :election_id,
                    politician_id = :politician_id,
                    result = :result,
                    votes = :votes,
                    rank = :rank,
                    updated_at = :updated_at
                WHERE id = :id
                RETURNING *
            """)

            params = {
                "id": entity.id,
                "election_id": entity.election_id,
                "politician_id": entity.politician_id,
                "result": entity.result,
                "votes": entity.votes,
                "rank": entity.rank,
                "updated_at": datetime.now(),
            }

            result = await self.session.execute(query, params)
            await self.session.commit()

            row = result.first()
            if row:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)
            raise UpdateError(f"ElectionMember with ID {entity.id} not found")

        except SQLAlchemyError as e:
            logger.error(f"Database error updating election member: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to update election member",
                {"entity": str(entity), "error": str(e)},
            ) from e

    async def delete(self, entity_id: int) -> bool:
        """IDで選挙結果メンバーを削除.

        Args:
            entity_id: 削除する選挙結果メンバーID

        Returns:
            削除成功時True、対象なし時False
        """
        try:
            query = text("DELETE FROM election_members WHERE id = :id")
            result = await self.session.execute(query, {"id": entity_id})
            await self.session.commit()

            return result.rowcount > 0  # type: ignore[attr-defined]

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting election member: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to delete election member",
                {"id": entity_id, "error": str(e)},
            ) from e

    async def delete_by_election_id(self, election_id: int) -> int:
        """選挙IDに属する全メンバーを削除.

        Args:
            election_id: 選挙ID

        Returns:
            削除件数
        """
        try:
            query = text(
                "DELETE FROM election_members WHERE election_id = :election_id"
            )
            result = await self.session.execute(query, {"election_id": election_id})
            await self.session.commit()

            return result.rowcount  # type: ignore[return-value]

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting election members by election: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to delete election members by election",
                {"election_id": election_id, "error": str(e)},
            ) from e

    async def count(self) -> int:
        """選挙結果メンバーの総件数を取得."""
        query = text("SELECT COUNT(*) FROM election_members")
        result = await self.session.execute(query)
        count = result.scalar()
        return count if count is not None else 0

    def _to_entity(self, model: ElectionMemberModel) -> ElectionMember:
        """データベースモデルをドメインエンティティに変換.

        Args:
            model: データベースモデル

        Returns:
            ドメインエンティティ
        """
        return ElectionMember(
            id=model.id,
            election_id=model.election_id,
            politician_id=model.politician_id,
            result=model.result,
            votes=model.votes,
            rank=model.rank,
        )

    def _to_model(self, entity: ElectionMember) -> ElectionMemberModel:
        """ドメインエンティティをデータベースモデルに変換.

        Args:
            entity: ドメインエンティティ

        Returns:
            データベースモデル
        """
        return ElectionMemberModel(
            id=entity.id,
            election_id=entity.election_id,
            politician_id=entity.politician_id,
            result=entity.result,
            votes=entity.votes,
            rank=entity.rank,
        )

    def _update_model(self, model: ElectionMemberModel, entity: ElectionMember) -> None:
        """エンティティからモデルを更新.

        Args:
            model: 更新対象のデータベースモデル
            entity: ソースエンティティ
        """
        model.election_id = entity.election_id
        model.politician_id = entity.politician_id
        model.result = entity.result
        model.votes = entity.votes
        model.rank = entity.rank

    def _dict_to_entity(self, data: dict[str, Any]) -> ElectionMember:
        """辞書をエンティティに変換.

        Args:
            data: エンティティデータの辞書

        Returns:
            選挙結果メンバーエンティティ
        """
        return ElectionMember(
            id=data.get("id"),
            election_id=data["election_id"],
            politician_id=data["politician_id"],
            result=data["result"],
            votes=data.get("votes"),
            rank=data.get("rank"),
        )
