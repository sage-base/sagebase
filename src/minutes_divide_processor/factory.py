"""MinutesDivider factory

フィーチャーフラグに基づいて適切なMinutesDivider実装を提供します。
Clean Architectureの原則に従い、依存性の注入とファクトリーパターンを使用しています。
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class MinutesDividerFactory:
    """MinutesDivider factory

    フィーチャーフラグに基づいて、Pydantic実装またはBAML実装を提供します。
    """

    @staticmethod
    def create(llm_service: Any | None = None, k: int = 5) -> Any:
        """フィーチャーフラグに基づいてMinutesDividerを作成

        Args:
            llm_service: LLMService instance (Pydantic実装でのみ使用)
            k: Number of sections (default 5)

        Returns:
            MinutesDivider: 適切な実装（MinutesDivider or BAMLMinutesDivider）

        Environment Variables:
            USE_BAML_MINUTES_DIVIDER: "false"でPydantic実装を使用（デフォルトはBAML）
        """
        use_baml = os.getenv("USE_BAML_MINUTES_DIVIDER", "true").lower() == "true"

        if use_baml:
            logger.info("Creating BAML MinutesDivider")
            from src.minutes_divide_processor.baml_minutes_divider import (
                BAMLMinutesDivider,
            )

            return BAMLMinutesDivider(llm_service=llm_service, k=k)

        logger.info("Creating Pydantic MinutesDivider")
        from src.minutes_divide_processor.minutes_divider import MinutesDivider

        return MinutesDivider(llm_service=llm_service, k=k)
