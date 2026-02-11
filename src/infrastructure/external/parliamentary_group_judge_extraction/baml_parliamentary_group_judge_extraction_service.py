"""BAML-based Parliamentary Group Judge Extraction Service

議会ページのHTMLテキストから会派単位の賛否情報を抽出するサービス。
BAMLを使用して型安全なLLM出力を実現します。
"""

import logging

from baml_client.async_client import b
from baml_client.types import JudgmentType

from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge


logger = logging.getLogger(__name__)

# JudgmentType(BAML) → 日本語表記のマッピング
JUDGMENT_TYPE_TO_JAPANESE: dict[JudgmentType, str] = {
    JudgmentType.FOR: "賛成",
    JudgmentType.AGAINST: "反対",
    JudgmentType.ABSTAIN: "棄権",
    JudgmentType.ABSENT: "欠席",
}


class BAMLParliamentaryGroupJudgeExtractionService:
    """BAML-based 会派賛否抽出サービス

    議会ページのHTMLテキストから会派単位の賛否情報を抽出するクラス。
    BAMLの`ExtractParliamentaryGroupJudges`関数を呼び出し、
    結果をドメインエンティティに変換します。
    """

    async def extract_parliamentary_group_judges(
        self,
        html_text: str | None,
        proposal_id: int = 0,
        source_url: str | None = None,
    ) -> list[ExtractedProposalJudge]:
        """HTMLテキストから会派単位の賛否情報を抽出する

        Args:
            html_text: 議会ページのHTMLテキスト
            proposal_id: 議案ID（Bronze Layerへの保存用）
            source_url: 抽出元URL

        Returns:
            抽出された会派賛否情報のリスト（ExtractedProposalJudgeエンティティ）
        """
        logger.info("=== extract_parliamentary_group_judges started ===")

        if html_text is None or not html_text.strip():
            logger.warning("No HTML text provided (None or empty)")
            return []

        logger.info(f"HTML text length: {len(html_text)}")

        try:
            # テキストが長すぎる場合は切り詰める
            max_length = 100000
            if len(html_text) > max_length:
                logger.warning(
                    f"HTML text too long ({len(html_text)} chars), "
                    f"truncating to {max_length} chars"
                )
                html_text = html_text[:max_length] + "..."

            # BAMLを呼び出し
            logger.info("Calling BAML ExtractParliamentaryGroupJudges")
            baml_results = await b.ExtractParliamentaryGroupJudges(html_text)

            # BAML結果をExtractedProposalJudgeエンティティに変換
            extracted_judges: list[ExtractedProposalJudge] = []
            for result in baml_results:
                judgment_japanese = JUDGMENT_TYPE_TO_JAPANESE.get(
                    result.judgment, "賛成"
                )

                judge = ExtractedProposalJudge(
                    proposal_id=proposal_id,
                    extracted_parliamentary_group_name=result.group_name,
                    extracted_judgment=judgment_japanese,
                    source_url=source_url,
                    additional_data=(
                        f"member_count={result.member_count}"
                        if result.member_count is not None
                        else None
                    ),
                )
                extracted_judges.append(judge)

            logger.info(f"Extracted {len(extracted_judges)} parliamentary group judges")
            for judge in extracted_judges:
                logger.debug(
                    f"  - {judge.extracted_parliamentary_group_name}: "
                    f"{judge.extracted_judgment}"
                )

            return extracted_judges

        except Exception as e:
            logger.error(
                f"BAML extract_parliamentary_group_judges failed: {e}",
                exc_info=True,
            )
            return []
