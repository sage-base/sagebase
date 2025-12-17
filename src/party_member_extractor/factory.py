"""Party member extractor factory

フィーチャーフラグに基づいて適切なPartyMemberExtractor実装を提供します。
Clean Architectureの原則に従い、依存性の注入とファクトリーパターンを使用しています。
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class PartyMemberExtractorFactory:
    """Party member extractor factory

    フィーチャーフラグに基づいて、Pydantic実装またはBAML実装を提供します。
    """

    @staticmethod
    def create(
        llm_service: Any | None = None,
        party_id: int | None = None,
        proc_logger: Any = None,
    ) -> Any:
        """フィーチャーフラグに基づいてextractorを作成

        Args:
            llm_service: LLMService instance (Pydantic実装で使用)
            party_id: ID of the party being processed (for history tracking)
            proc_logger: ProcessingLogger instance (optional)

        Returns:
            PartyMemberExtractor: 適切な実装（PydanticまたはBAML）

        Environment Variables:
            USE_BAML_PARTY_MEMBER_EXTRACTOR: "true"でBAML実装を使用
        """
        use_baml = (
            os.getenv("USE_BAML_PARTY_MEMBER_EXTRACTOR", "false").lower() == "true"
        )

        if use_baml:
            logger.info("Creating BAML party member extractor")
            # ruff: noqa: E501
            from src.party_member_extractor.baml_llm_extractor import (
                BAMLPartyMemberExtractor,
            )

            return BAMLPartyMemberExtractor(llm_service, party_id, proc_logger)

        logger.info("Creating Pydantic party member extractor")
        from src.party_member_extractor.extractor import PartyMemberExtractor

        return PartyMemberExtractor(llm_service, party_id, proc_logger)
