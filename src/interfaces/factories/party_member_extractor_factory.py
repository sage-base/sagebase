"""政党メンバー抽出器ファクトリー

フィーチャーフラグに基づいて適切なPartyMemberExtractor実装を提供します。
Clean Architectureの原則に従い、依存性の注入とファクトリーパターンを使用しています。
"""

import logging
import os

from src.domain.interfaces.party_member_extractor_service import (
    IPartyMemberExtractorService,
)
from src.domain.services.interfaces.llm_service import ILLMService

logger = logging.getLogger(__name__)


class PartyMemberExtractorFactory:
    """政党メンバー抽出器ファクトリー

    フィーチャーフラグに基づいて、Pydantic実装またはBAML実装を提供します。
    """

    @staticmethod
    def create(llm_service: ILLMService | None = None) -> IPartyMemberExtractorService:
        """フィーチャーフラグに基づいてextractorを作成

        Args:
            llm_service: LLMService instance (Pydantic実装で使用)

        Returns:
            IPartyMemberExtractorService: 適切な実装（PydanticまたはBAML）

        Environment Variables:
            USE_BAML_PARTY_MEMBER_EXTRACTOR: デフォルトは"true"（BAML実装）
                                            "false"でPydantic実装を使用
        """
        use_baml = (
            os.getenv("USE_BAML_PARTY_MEMBER_EXTRACTOR", "true").lower() == "true"
        )

        if use_baml:
            logger.info("Creating BAML party member extractor")
            # ruff: noqa: E501
            from src.infrastructure.external.party_member_extractor.baml_extractor import (
                BAMLPartyMemberExtractor,
            )

            return BAMLPartyMemberExtractor()

        logger.info("Creating Pydantic party member extractor")
        # ruff: noqa: E501
        from src.infrastructure.external.party_member_extractor.pydantic_extractor import (
            PydanticPartyMemberExtractor,
        )

        if llm_service is None:
            from src.services.llm_factory import LLMServiceFactory

            factory = LLMServiceFactory()
            llm_service = factory.create_advanced()

        return PydanticPartyMemberExtractor(llm_service=llm_service)
