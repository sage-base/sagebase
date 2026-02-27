"""全Speakerのis_politicianフラグを一括分類設定するユースケース.

非政治家パターン（役職のみ・参考人・証人等）に基づいて、
SpeakerのisPoliticianフラグを一括で分類する。
"""

import logging

from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.speaker_classifier import NON_POLITICIAN_EXACT_NAMES


logger = logging.getLogger(__name__)


class ClassifySpeakersPoliticianUseCase:
    """全Speakerのis_politicianフラグを一括分類設定するユースケース."""

    def __init__(self, speaker_repository: SpeakerRepository):
        """ユースケースを初期化する.

        Args:
            speaker_repository: 発言者リポジトリの実装
        """
        self.speaker_repository = speaker_repository

    async def execute(self) -> dict[str, int]:
        """全Speakerのis_politicianフラグを一括分類設定する.

        Returns:
            分類結果の統計情報
        """
        result = await self.speaker_repository.classify_is_politician_bulk(
            NON_POLITICIAN_EXACT_NAMES
        )
        logger.info(
            "Speaker分類完了: 政治家に設定=%d件, 非政治家に設定=%d件",
            result["total_updated_to_politician"],
            result["total_kept_non_politician"],
        )
        return result
