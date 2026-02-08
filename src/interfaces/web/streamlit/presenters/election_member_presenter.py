"""選挙結果メンバー管理のプレゼンター."""

from typing import Any

import pandas as pd

from src.application.dtos.election_member_dto import (
    CreateElectionMemberInputDto,
    DeleteElectionMemberInputDto,
    ElectionMemberOutputItem,
    ListElectionMembersByElectionInputDto,
    UpdateElectionMemberInputDto,
)
from src.common.logging import get_logger
from src.domain.entities import Politician
from src.infrastructure.di.container import Container
from src.interfaces.web.streamlit.presenters.base import BasePresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class ElectionMemberPresenter(BasePresenter[list[ElectionMemberOutputItem]]):
    """選挙結果メンバー管理のプレゼンター."""

    def __init__(self, container: Container | None = None):
        """プレゼンターを初期化する."""
        super().__init__(container)
        self.use_case = self.container.use_cases.manage_election_members_usecase()
        self.election_use_case = self.container.use_cases.manage_elections_usecase()
        self.politician_repo = self.container.repositories.politician_repository()
        self.session = SessionManager()
        self.logger = get_logger(__name__)

    def load_data(self) -> list[ElectionMemberOutputItem]:
        """全メンバーを読み込む（デフォルトは空リスト）."""
        return []

    def load_members_by_election(
        self, election_id: int
    ) -> list[ElectionMemberOutputItem]:
        """選挙別メンバー一覧を読み込む."""
        return self._run_async(self._load_members_by_election_async(election_id))

    async def _load_members_by_election_async(
        self, election_id: int
    ) -> list[ElectionMemberOutputItem]:
        """選挙別メンバー一覧を読み込む（非同期実装）."""
        try:
            result = await self.use_case.list_by_election(
                ListElectionMembersByElectionInputDto(election_id=election_id)
            )
            return result.election_members
        except Exception as e:
            self.logger.exception(
                f"Failed to load election members for election {election_id}: {e}"
            )
            return []

    def load_politicians(self) -> list[Politician]:
        """政治家一覧を読み込む."""
        return self._run_async(self._load_politicians_async())

    async def _load_politicians_async(self) -> list[Politician]:
        """政治家一覧を読み込む（非同期実装）."""
        try:
            return await self.politician_repo.get_all()
        except Exception as e:
            self.logger.error(f"Failed to load politicians: {e}")
            return []

    def get_result_options(self) -> list[str]:
        """選挙結果の選択肢を取得する."""
        return self.use_case.get_result_options()

    def create(
        self,
        election_id: int,
        politician_id: int,
        result: str,
        votes: int | None = None,
        rank: int | None = None,
    ) -> tuple[bool, str | None]:
        """選挙結果メンバーを作成する."""
        return self._run_async(
            self._create_async(election_id, politician_id, result, votes, rank)
        )

    async def _create_async(
        self,
        election_id: int,
        politician_id: int,
        result: str,
        votes: int | None = None,
        rank: int | None = None,
    ) -> tuple[bool, str | None]:
        """選挙結果メンバーを作成する（非同期実装）."""
        try:
            result_dto = await self.use_case.create_election_member(
                CreateElectionMemberInputDto(
                    election_id=election_id,
                    politician_id=politician_id,
                    result=result,
                    votes=votes,
                    rank=rank,
                )
            )
            if result_dto.success:
                return True, None
            else:
                return False, result_dto.error_message
        except Exception as e:
            error_msg = f"Failed to create election member: {e}"
            self.logger.exception(error_msg)
            return False, error_msg

    def update(
        self,
        id: int,
        election_id: int,
        politician_id: int,
        result: str,
        votes: int | None = None,
        rank: int | None = None,
    ) -> tuple[bool, str | None]:
        """選挙結果メンバーを更新する."""
        return self._run_async(
            self._update_async(id, election_id, politician_id, result, votes, rank)
        )

    async def _update_async(
        self,
        id: int,
        election_id: int,
        politician_id: int,
        result: str,
        votes: int | None = None,
        rank: int | None = None,
    ) -> tuple[bool, str | None]:
        """選挙結果メンバーを更新する（非同期実装）."""
        try:
            result_dto = await self.use_case.update_election_member(
                UpdateElectionMemberInputDto(
                    id=id,
                    election_id=election_id,
                    politician_id=politician_id,
                    result=result,
                    votes=votes,
                    rank=rank,
                )
            )
            if result_dto.success:
                return True, None
            else:
                return False, result_dto.error_message
        except Exception as e:
            error_msg = f"Failed to update election member: {e}"
            self.logger.exception(error_msg)
            return False, error_msg

    def delete(self, id: int) -> tuple[bool, str | None]:
        """選挙結果メンバーを削除する."""
        return self._run_async(self._delete_async(id))

    async def _delete_async(self, id: int) -> tuple[bool, str | None]:
        """選挙結果メンバーを削除する（非同期実装）."""
        try:
            result = await self.use_case.delete_election_member(
                DeleteElectionMemberInputDto(id=id)
            )
            if result.success:
                return True, None
            else:
                return False, result.error_message
        except Exception as e:
            error_msg = f"Failed to delete election member: {e}"
            self.logger.exception(error_msg)
            return False, error_msg

    def to_dataframe(
        self,
        members: list[ElectionMemberOutputItem],
        politician_map: dict[int, str],
    ) -> pd.DataFrame | None:
        """メンバーリストをDataFrameに変換する."""
        if not members:
            return None

        df_data = []
        for member in members:
            df_data.append(
                {
                    "ID": member.id,
                    "政治家": politician_map.get(
                        member.politician_id, f"ID:{member.politician_id}"
                    ),
                    "結果": member.result,
                    "得票数": member.votes if member.votes is not None else "",
                    "順位": member.rank if member.rank is not None else "",
                }
            )
        return pd.DataFrame(df_data)

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """ユーザーアクションを処理する."""
        if action == "list_by_election":
            election_id = kwargs.get("election_id")
            if election_id is None:
                return []
            return self.load_members_by_election(election_id)
        elif action == "create":
            election_id = kwargs.get("election_id")
            politician_id = kwargs.get("politician_id")
            result = kwargs.get("result")
            if not all([election_id, politician_id, result]):
                return False, "必須パラメータが不足しています"
            assert isinstance(election_id, int)
            assert isinstance(politician_id, int)
            assert isinstance(result, str)
            return self.create(
                election_id,
                politician_id,
                result,
                kwargs.get("votes"),
                kwargs.get("rank"),
            )
        elif action == "update":
            id = kwargs.get("id")
            election_id = kwargs.get("election_id")
            politician_id = kwargs.get("politician_id")
            result = kwargs.get("result")
            if not all([id, election_id, politician_id, result]):
                return False, "必須パラメータが不足しています"
            assert isinstance(id, int)
            assert isinstance(election_id, int)
            assert isinstance(politician_id, int)
            assert isinstance(result, str)
            return self.update(
                id,
                election_id,
                politician_id,
                result,
                kwargs.get("votes"),
                kwargs.get("rank"),
            )
        elif action == "delete":
            id = kwargs.get("id")
            if not id:
                return False, "IDが指定されていません"
            return self.delete(id)
        else:
            raise ValueError(f"Unknown action: {action}")
