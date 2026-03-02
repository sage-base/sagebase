"""発言者を非政治家として分類するユースケース.

個別の発言者に対してSkipReasonを設定し、
非政治家としてマークするApplication層の処理を提供します。
"""

from dataclasses import dataclass

from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.speaker_classifier import SkipReason


@dataclass
class MarkSpeakerAsNonPoliticianInputDto:
    """非政治家分類入力DTO."""

    speaker_id: int
    skip_reason: str


@dataclass
class MarkSpeakerAsNonPoliticianOutputDto:
    """非政治家分類出力DTO."""

    success: bool
    error_message: str | None = None


class MarkSpeakerAsNonPoliticianUseCase:
    """発言者を非政治家として分類するユースケース.

    個別の発言者に対してSkipReasonを設定し、
    is_politician=Falseとpolitician_id=Noneを設定します。

    Attributes:
        speaker_repository: 発言者リポジトリ
    """

    def __init__(self, speaker_repository: SpeakerRepository):
        """ユースケースを初期化する.

        Args:
            speaker_repository: 発言者リポジトリの実装
        """
        self.speaker_repository = speaker_repository

    async def execute(
        self, input_dto: MarkSpeakerAsNonPoliticianInputDto
    ) -> MarkSpeakerAsNonPoliticianOutputDto:
        """非政治家分類を実行する.

        Args:
            input_dto: 非政治家分類入力DTO

        Returns:
            分類結果を含む出力DTO
        """
        # skip_reasonのバリデーション
        try:
            SkipReason(input_dto.skip_reason)
        except ValueError:
            return MarkSpeakerAsNonPoliticianOutputDto(
                success=False,
                error_message=f"無効なスキップ理由: {input_dto.skip_reason}",
            )

        speaker = await self.speaker_repository.get_by_id(input_dto.speaker_id)
        if not speaker:
            return MarkSpeakerAsNonPoliticianOutputDto(
                success=False,
                error_message="発言者が見つかりません",
            )

        speaker.is_politician = False
        speaker.skip_reason = input_dto.skip_reason
        speaker.politician_id = None

        await self.speaker_repository.update(speaker)

        return MarkSpeakerAsNonPoliticianOutputDto(success=True)
