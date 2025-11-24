"""A/B test member extractor

PydanticとBAMLの両実装を実行して比較するextractor。
"""

import logging
from typing import Any

from src.domain.dtos.conference_member_dto import ExtractedMemberDTO
from src.domain.interfaces.member_extractor_service import IMemberExtractorService
from src.infrastructure.external.conference_member_extractor.baml_extractor import (
    BAMLMemberExtractor,
)
from src.infrastructure.external.conference_member_extractor.pydantic_extractor import (
    PydanticMemberExtractor,
)

logger = logging.getLogger(__name__)


class ABTestMemberExtractor(IMemberExtractorService):
    """A/B test member extractor

    PydanticとBAMLの両実装を実行し、結果を比較してログに記録します。
    デフォルトではPydanticの結果を返します（安全側）。
    """

    def __init__(self):
        self.pydantic_extractor = PydanticMemberExtractor()
        self.baml_extractor = BAMLMemberExtractor()

    async def extract_members(
        self, html_content: str, conference_name: str
    ) -> list[dict[str, Any]]:
        """両実装を実行して比較

        Args:
            html_content: HTMLコンテンツ
            conference_name: 会議体名

        Returns:
            抽出されたメンバー情報のリスト（Pydantic実装の結果）
        """
        logger.info("=== A/B Test Mode Enabled ===")

        # Pydantic実装
        logger.info("Executing Pydantic implementation...")
        pydantic_result = await self.pydantic_extractor.extract_members(
            html_content, conference_name
        )

        # BAML実装
        logger.info("Executing BAML implementation...")
        baml_result = await self.baml_extractor.extract_members(
            html_content, conference_name
        )

        # 比較ログ
        logger.info("=== Comparison Results ===")
        logger.info(f"Pydantic: {len(pydantic_result)} members")
        logger.info(f"BAML: {len(baml_result)} members")

        # 詳細な差分記録
        self._log_comparison_details(pydantic_result, baml_result)

        # デフォルトはPydantic結果を返す（安全側）
        logger.info("Returning Pydantic results (default in A/B test mode)")
        return pydantic_result

    def _log_comparison_details(
        self, pydantic_result: list[dict[str, Any]], baml_result: list[dict[str, Any]]
    ) -> None:
        """比較の詳細をログに記録

        Args:
            pydantic_result: Pydantic実装の結果
            baml_result: BAML実装の結果
        """
        # 辞書をDTOに変換して名前を取得
        pydantic_names = [
            ExtractedMemberDTO(**m).name for m in pydantic_result if "name" in m
        ]
        baml_names = [ExtractedMemberDTO(**m).name for m in baml_result if "name" in m]

        logger.info("Pydantic names: " + ", ".join(pydantic_names))
        logger.info("BAML names: " + ", ".join(baml_names))

        # 名前の差分を検出
        pydantic_name_set = set(pydantic_names)
        baml_name_set = set(baml_names)

        only_in_pydantic = pydantic_name_set - baml_name_set
        only_in_baml = baml_name_set - pydantic_name_set

        if only_in_pydantic:
            logger.info(f"Only in Pydantic: {only_in_pydantic}")
        if only_in_baml:
            logger.info(f"Only in BAML: {only_in_baml}")

        # TODO: トークン数、レイテンシなどのメトリクスを追加
