"""Speaker repository interface."""

from abc import abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.entities.speaker import Speaker
from src.domain.repositories.base import BaseRepository
from src.domain.value_objects.speaker_with_conversation_count import (
    SpeakerWithConversationCount,
)
from src.domain.value_objects.speaker_with_politician import SpeakerWithPolitician


class SpeakerRepository(BaseRepository[Speaker]):
    """Repository interface for speakers."""

    @abstractmethod
    async def get_by_name_party_position(
        self,
        name: str,
        political_party_name: str | None = None,
        position: str | None = None,
    ) -> Speaker | None:
        """Get speaker by name, party, and position."""
        pass

    @abstractmethod
    async def get_politicians(self) -> list[Speaker]:
        """Get all speakers who are politicians."""
        pass

    @abstractmethod
    async def search_by_name(self, name_pattern: str) -> list[Speaker]:
        """Search speakers by name pattern."""
        pass

    @abstractmethod
    async def upsert(self, speaker: Speaker) -> Speaker:
        """Insert or update speaker (upsert)."""
        pass

    @abstractmethod
    async def get_speakers_with_conversation_count(
        self,
        limit: int | None = None,
        offset: int | None = None,
        speaker_type: str | None = None,
        is_politician: bool | None = None,
        name_search: str | None = None,
        skip_reason: str | None = None,
        has_politician_id: bool | None = None,
        order_by: str = "conversation_count",
    ) -> list[SpeakerWithConversationCount]:
        """Get speakers with their conversation count.

        Args:
            limit: 取得件数上限
            offset: オフセット
            speaker_type: 発言者タイプフィルタ
            is_politician: 政治家フラグフィルタ
            name_search: 名前検索（部分一致）
            skip_reason: スキップ理由フィルタ
            has_politician_id: マッチ状態フィルタ（True=マッチ済み、False=未マッチ）
            order_by: ソートカラム（"conversation_count" or "name"）
        """
        pass

    @abstractmethod
    async def find_by_name(self, name: str) -> Speaker | None:
        """Find speaker by name."""
        pass

    @abstractmethod
    async def get_speakers_not_linked_to_politicians(self) -> list[Speaker]:
        """Get speakers who are not linked to politicians (is_politician=False)."""
        pass

    @abstractmethod
    async def get_speakers_with_politician_info(self) -> list[dict[str, Any]]:
        """Get speakers with linked politician information."""
        pass

    @abstractmethod
    async def get_speaker_politician_stats(self) -> dict[str, Any]:
        """Get statistics of speaker-politician linkage."""
        pass

    @abstractmethod
    async def get_all_for_matching(self) -> list[dict[str, Any]]:
        """Get all speakers for matching purposes.

        Returns:
            List of dicts with id and name keys
        """
        pass

    @abstractmethod
    async def get_affiliated_speakers(
        self, meeting_date: str, conference_id: int
    ) -> list[dict[str, Any]]:
        """Get speakers affiliated with a conference at a specific date.

        Args:
            meeting_date: Meeting date in YYYY-MM-DD format
            conference_id: Conference ID

        Returns:
            List of dicts with speaker and politician info
        """
        pass

    @abstractmethod
    async def find_by_matched_user(
        self, user_id: "UUID | None" = None
    ) -> list[SpeakerWithPolitician]:
        """指定されたユーザーIDによってマッチングされた発言者と政治家情報を取得する

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）

        Returns:
            発言者と紐付けられた政治家情報を含むValue Objectのリスト
        """
        pass

    @abstractmethod
    async def get_speaker_matching_statistics_by_user(
        self,
        user_id: "UUID | None" = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[UUID, int]:
        """ユーザー別の発言者紐付け件数を集計する（データベースレベルで集計）

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            start_date: 開始日時（この日時以降の作業を集計）
            end_date: 終了日時（この日時以前の作業を集計）

        Returns:
            ユーザーIDと件数のマッピング（例: {UUID('...'): 10, UUID('...'): 5}）
        """
        pass

    @abstractmethod
    async def get_speaker_matching_timeline_statistics(
        self,
        user_id: "UUID | None" = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        interval: str = "day",
    ) -> list[dict[str, Any]]:
        """時系列の発言者紐付け件数を集計する（データベースレベルで集計）

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            start_date: 開始日時
            end_date: 終了日時
            interval: 集計間隔（"day", "week", "month"）

        Returns:
            時系列データのリスト（例: [{"date": "2024-01-01", "count": 5}, ...]）
        """
        pass

    @abstractmethod
    async def get_by_politician_id(self, politician_id: int) -> list[Speaker]:
        """指定された政治家IDに紐づく発言者を取得する.

        Args:
            politician_id: 政治家ID

        Returns:
            紐づいている発言者のリスト
        """
        pass

    @abstractmethod
    async def unlink_from_politician(self, politician_id: int) -> int:
        """指定された政治家IDとの紐づきを解除する.

        発言者のpolitician_idをNULLに設定します。

        Args:
            politician_id: 政治家ID

        Returns:
            解除された発言者の数
        """
        pass

    @abstractmethod
    async def get_speakers_pending_review(
        self,
        min_confidence: float = 0.7,
        max_confidence: float = 0.9,
    ) -> list[Speaker]:
        """手動検証待ちの発言者を取得する.

        指定された信頼度範囲でマッチされた発言者のうち、
        まだ手動検証されていないものを返す。

        Args:
            min_confidence: 最低信頼度（この値以上）
            max_confidence: 最高信頼度（この値未満）

        Returns:
            手動検証待ちの発言者リスト
        """
        pass

    @abstractmethod
    async def classify_is_politician_bulk(
        self,
        non_politician_names: frozenset[str],
        non_politician_prefixes: frozenset[str] | None = None,
        skip_reason_patterns: (
            list[tuple[str, frozenset[str], frozenset[str]]] | None
        ) = None,
    ) -> dict[str, int]:
        """全Speakerのis_politicianフラグを一括分類設定する.

        1. 全件をis_politician=Trueに設定（skip_reasonもNULLにリセット）
        2. non_politician_namesに完全一致、またはnon_politician_prefixesで
           始まる名前で、politician_idがNULLかつis_manually_verified=Falseの
           ものをFalseに戻す
        3. skip_reason_patternsが指定された場合、カテゴリ別にskip_reasonも設定

        Args:
            non_politician_names: 非政治家として扱う名前の完全一致パターン
            non_politician_prefixes: 非政治家として扱う名前のプレフィックスパターン
            skip_reason_patterns: カテゴリ別の
                (skip_reason値, 完全一致名, プレフィックス)リスト

        Returns:
            {"total_updated_to_politician": int,
             "total_kept_non_politician": int}
        """
        pass
