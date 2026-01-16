"""Minutes processing service implementation wrapping MinutesProcessAgent."""

import structlog

from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.services.interfaces.minutes_processing_service import (
    IMinutesProcessingService,
)
from src.domain.value_objects.speaker_speech import SpeakerSpeech
from src.minutes_divide_processor.minutes_process_agent import MinutesProcessAgent


logger = structlog.get_logger(__name__)


class MinutesProcessAgentService(IMinutesProcessingService):
    """Service that wraps MinutesProcessAgent for Clean Architecture compliance.

    This service implements the IMinutesProcessingService interface and delegates
    to the MinutesProcessAgent for the actual processing logic. This allows the
    application layer to depend on a domain interface rather than directly on
    infrastructure code.

    発言者名の正規化処理はLangGraphのnormalize_speaker_namesノードで
    LLMを使用して行われます（Issue #946）。
    """

    def __init__(self, llm_service: ILLMService):
        """Initialize the minutes processing service.

        Args:
            llm_service: LLM service instance to use for processing
        """
        self.llm_service = llm_service
        self.agent = MinutesProcessAgent(llm_service=llm_service)

    async def process_minutes(
        self,
        original_minutes: str,
        role_name_mappings: dict[str, str] | None = None,
    ) -> list[SpeakerSpeech]:
        """Process meeting minutes text and extract speeches.

        This method wraps the MinutesProcessAgent and converts
        infrastructure-specific models to domain value objects.

        発言者名の正規化（役職（人名）パターンからの人名抽出、マッピング参照）は
        LangGraphのnormalize_speaker_namesノードでLLMにより処理されます（Issue #946）。

        Args:
            original_minutes: Raw meeting minutes text content
            role_name_mappings: 役職-人名マッピング辞書（例: {"議長": "伊藤条一"}）
                発言者名が役職のみの場合に実名に変換するために使用（Issue #946）

        Returns:
            List of extracted speeches with speaker information as domain value objects.
            Invalid speeches (role-only without mapping) are filtered out by the LLM.

        Raises:
            ValueError: If processing fails or invalid input is provided
            TypeError: If the result format is invalid
        """
        # マッピング情報をログ出力（デバッグ用）
        if role_name_mappings:
            logger.info(
                "役職-人名マッピングを使用して発言抽出を開始",
                mapping_count=len(role_name_mappings),
            )
            for role, name in role_name_mappings.items():
                logger.info(f"  マッピング: {role} → {name}")
        else:
            logger.info("役職-人名マッピングなしで発言抽出を開始")

        # LangGraphエージェントを実行（役職-人名マッピングを渡す: Issue #946）
        # 発言者名の正規化はLangGraphのnormalize_speaker_namesノードで処理される
        infrastructure_results = await self.agent.run(
            original_minutes,
            role_name_mappings=role_name_mappings,
        )

        # Convert to domain value objects
        # Note: フィルタリングと正規化は既にLangGraph内で行われている
        domain_results: list[SpeakerSpeech] = []
        for result in infrastructure_results:
            # Skip entries with empty speaker or speech_content (safety check)
            if not result.speaker or not result.speaker.strip():
                logger.warning(
                    "Skipping speech with empty speaker",
                    speech_order=result.speech_order,
                    chapter_number=result.chapter_number,
                )
                continue

            if not result.speech_content or not result.speech_content.strip():
                logger.warning(
                    "Skipping speech with empty content",
                    speaker=result.speaker,
                    speech_order=result.speech_order,
                    chapter_number=result.chapter_number,
                )
                continue

            domain_results.append(
                SpeakerSpeech(
                    speaker=result.speaker,
                    speech_content=result.speech_content,
                    chapter_number=result.chapter_number,
                    sub_chapter_number=result.sub_chapter_number,
                    speech_order=result.speech_order,
                )
            )

        logger.info(
            "発言抽出完了（LLMで正規化済み）",
            total_results=len(infrastructure_results),
            valid_count=len(domain_results),
        )

        return domain_results
