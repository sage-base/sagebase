"""Presenter for government official management.

政府関係者（官僚）管理のPresenter実装。
"""

from typing import Any

import pandas as pd

from src.application.dtos.government_official_dto import (
    GovernmentOfficialOutputItem,
    GovernmentOfficialPositionOutputItem,
)
from src.application.usecases.batch_link_speakers_to_government_officials_usecase import (  # noqa: E501
    BatchLinkOutputDto,
    BatchLinkSpeakersToGovernmentOfficialsUseCase,
)
from src.common.logging import get_logger
from src.domain.entities.government_official import GovernmentOfficial
from src.domain.entities.government_official_position import GovernmentOfficialPosition
from src.domain.value_objects.speaker_with_conversation_count import (
    SpeakerWithConversationCount,
)
from src.infrastructure.di.container import Container
from src.infrastructure.persistence.government_official_position_repository_impl import (  # noqa: E501
    GovernmentOfficialPositionRepositoryImpl,
)
from src.infrastructure.persistence.government_official_repository_impl import (
    GovernmentOfficialRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.infrastructure.persistence.speaker_repository_impl import (
    SpeakerRepositoryImpl,
)
from src.interfaces.web.streamlit.presenters.base import BasePresenter


class GovernmentOfficialPresenter(BasePresenter[list[GovernmentOfficialOutputItem]]):
    """政府関係者管理のPresenter."""

    def __init__(self, container: Container | None = None):
        super().__init__(container)
        self.official_repo = RepositoryAdapter(GovernmentOfficialRepositoryImpl)
        self.position_repo = RepositoryAdapter(GovernmentOfficialPositionRepositoryImpl)
        self.speaker_repo = RepositoryAdapter(SpeakerRepositoryImpl)
        self.logger = get_logger(__name__)

    def load_data(self) -> list[GovernmentOfficialOutputItem]:
        """全政府関係者を取得する."""
        return self._run_async(self._load_data_async())

    async def _load_data_async(self) -> list[GovernmentOfficialOutputItem]:
        try:
            officials = await self.official_repo.get_all()
            result = []
            for official in officials:
                positions = await self.position_repo.get_by_official(official.id)
                result.append(
                    GovernmentOfficialOutputItem.from_entity(official, positions)
                )
            return result
        except Exception as e:
            self.logger.error(f"政府関係者の読み込みに失敗: {e}")
            return []

    def search(self, name: str) -> list[GovernmentOfficialOutputItem]:
        """名前で検索する."""
        return self._run_async(self._search_async(name))

    async def _search_async(self, name: str) -> list[GovernmentOfficialOutputItem]:
        try:
            officials = await self.official_repo.search_by_name(name)
            result = []
            for official in officials:
                positions = await self.position_repo.get_by_official(official.id)
                result.append(
                    GovernmentOfficialOutputItem.from_entity(official, positions)
                )
            return result
        except Exception as e:
            self.logger.error(f"政府関係者の検索に失敗: {e}")
            return []

    def create(
        self, name: str, name_yomi: str | None = None
    ) -> tuple[bool, GovernmentOfficialOutputItem | None, str | None]:
        """政府関係者を新規作成する."""
        return self._run_async(self._create_async(name, name_yomi))

    async def _create_async(
        self, name: str, name_yomi: str | None = None
    ) -> tuple[bool, GovernmentOfficialOutputItem | None, str | None]:
        try:
            entity = GovernmentOfficial(name=name, name_yomi=name_yomi)
            created = await self.official_repo.create(entity)
            dto = GovernmentOfficialOutputItem.from_entity(created)
            return True, dto, None
        except Exception as e:
            error_msg = f"政府関係者の作成に失敗: {e}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def update(
        self, id: int, name: str, name_yomi: str | None = None
    ) -> tuple[bool, str | None]:
        """政府関係者を更新する."""
        return self._run_async(self._update_async(id, name, name_yomi))

    async def _update_async(
        self, id: int, name: str, name_yomi: str | None = None
    ) -> tuple[bool, str | None]:
        try:
            entity = await self.official_repo.get_by_id(id)
            if entity is None:
                return False, f"ID {id} の政府関係者が見つかりません"
            entity.name = name
            entity.name_yomi = name_yomi
            await self.official_repo.update(entity)
            return True, None
        except Exception as e:
            error_msg = f"政府関係者の更新に失敗: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def delete(self, id: int) -> tuple[bool, str | None]:
        """政府関係者を削除する."""
        return self._run_async(self._delete_async(id))

    async def _delete_async(self, id: int) -> tuple[bool, str | None]:
        try:
            await self.official_repo.delete(id)
            return True, None
        except Exception as e:
            error_msg = f"政府関係者の削除に失敗: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def get_positions(
        self, official_id: int
    ) -> list[GovernmentOfficialPositionOutputItem]:
        """役職履歴を取得する."""
        return self._run_async(self._get_positions_async(official_id))

    async def _get_positions_async(
        self, official_id: int
    ) -> list[GovernmentOfficialPositionOutputItem]:
        try:
            positions = await self.position_repo.get_by_official(official_id)
            return [
                GovernmentOfficialPositionOutputItem.from_entity(p) for p in positions
            ]
        except Exception as e:
            self.logger.error(f"役職履歴の取得に失敗: {e}")
            return []

    def add_position(
        self,
        official_id: int,
        organization: str,
        position: str,
        start_date: Any = None,
        end_date: Any = None,
        source_note: str | None = None,
    ) -> tuple[bool, str | None]:
        """役職を追加する."""
        return self._run_async(
            self._add_position_async(
                official_id, organization, position, start_date, end_date, source_note
            )
        )

    async def _add_position_async(
        self,
        official_id: int,
        organization: str,
        position: str,
        start_date: Any = None,
        end_date: Any = None,
        source_note: str | None = None,
    ) -> tuple[bool, str | None]:
        try:
            entity = GovernmentOfficialPosition(
                government_official_id=official_id,
                organization=organization,
                position=position,
                start_date=start_date,
                end_date=end_date,
                source_note=source_note,
            )
            await self.position_repo.create(entity)
            return True, None
        except Exception as e:
            error_msg = f"役職の追加に失敗: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def delete_position(self, position_id: int) -> tuple[bool, str | None]:
        """役職を削除する."""
        return self._run_async(self._delete_position_async(position_id))

    async def _delete_position_async(self, position_id: int) -> tuple[bool, str | None]:
        try:
            await self.position_repo.delete(position_id)
            return True, None
        except Exception as e:
            error_msg = f"役職の削除に失敗: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def get_linked_speakers(
        self, official_id: int
    ) -> list[SpeakerWithConversationCount]:
        """紐付きSpeakerを取得する."""
        return self._run_async(self._get_linked_speakers_async(official_id))

    async def _get_linked_speakers_async(
        self, official_id: int
    ) -> list[SpeakerWithConversationCount]:
        try:
            # skip_reason="government_official"でフィルタし、Python側でofficial_idを照合
            speakers = await self.speaker_repo.get_speakers_with_conversation_count(
                skip_reason="government_official",
            )
            return [s for s in speakers if s.government_official_id == official_id]
        except Exception as e:
            self.logger.error(f"紐付きSpeakerの取得に失敗: {e}")
            return []

    def batch_link_speakers(self, dry_run: bool = True) -> BatchLinkOutputDto:
        """一括紐付けを実行する."""
        return self._run_async(self._batch_link_speakers_async(dry_run))

    async def _batch_link_speakers_async(
        self, dry_run: bool = True
    ) -> BatchLinkOutputDto:
        try:
            usecase = BatchLinkSpeakersToGovernmentOfficialsUseCase(
                speaker_repository=self.speaker_repo,  # type: ignore[arg-type]
                government_official_repository=self.official_repo,  # type: ignore[arg-type]
            )
            return await usecase.execute(dry_run=dry_run)
        except Exception as e:
            self.logger.error(f"一括紐付けに失敗: {e}")
            return BatchLinkOutputDto(linked_count=0, skipped_count=0, details=[])

    def to_dataframe(
        self, officials: list[GovernmentOfficialOutputItem]
    ) -> pd.DataFrame | None:
        """DataFrameに変換する."""
        if not officials:
            return None

        data = []
        for o in officials:
            data.append(
                {
                    "ID": o.id,
                    "名前": o.name,
                    "読み仮名": o.name_yomi or "-",
                    "役職数": len(o.positions),
                }
            )
        return pd.DataFrame(data)

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """アクションを処理する."""
        if action == "list":
            return self.load_data()
        elif action == "create":
            return self.create(
                name=kwargs.get("name", ""),
                name_yomi=kwargs.get("name_yomi"),
            )
        elif action == "update":
            return self.update(
                id=kwargs.get("id", 0),
                name=kwargs.get("name", ""),
                name_yomi=kwargs.get("name_yomi"),
            )
        elif action == "delete":
            return self.delete(id=kwargs.get("id", 0))
        else:
            raise ValueError(f"Unknown action: {action}")
