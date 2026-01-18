"""発言者と政治家を紐付けるユースケース.

発言者と政治家の手動紐付けをApplication層で処理し、
View層からドメインエンティティの直接操作を排除します。
"""

from dataclasses import dataclass
from uuid import UUID

from src.application.dtos.speaker_dto import SpeakerMatchingDTO
from src.domain.repositories.speaker_repository import SpeakerRepository


@dataclass
class LinkSpeakerToPoliticianInputDto:
    """発言者-政治家紐付け入力DTO."""

    speaker_id: int
    politician_id: int
    politician_name: str
    user_id: UUID | None = None


@dataclass
class LinkSpeakerToPoliticianOutputDto:
    """発言者-政治家紐付け出力DTO."""

    success: bool
    error_message: str | None = None
    updated_matching_dto: SpeakerMatchingDTO | None = None


class LinkSpeakerToPoliticianUseCase:
    """発言者と政治家を紐付けるユースケース.

    View層からドメインエンティティを直接操作せずに、
    発言者と政治家の紐付けを行います。

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
        self, input_dto: LinkSpeakerToPoliticianInputDto
    ) -> LinkSpeakerToPoliticianOutputDto:
        """発言者と政治家の紐付けを実行する.

        Args:
            input_dto: 紐付け入力DTO

        Returns:
            紐付け結果を含む出力DTO
        """
        # 発言者を取得
        speaker = await self.speaker_repository.get_by_id(input_dto.speaker_id)
        if not speaker:
            return LinkSpeakerToPoliticianOutputDto(
                success=False,
                error_message="発言者が見つかりません",
            )

        # 発言者のpolitician_idとmatched_by_user_idを更新
        speaker.politician_id = input_dto.politician_id
        speaker.matched_by_user_id = input_dto.user_id

        # 更新をリポジトリに反映
        await self.speaker_repository.upsert(speaker)

        # 更新後のマッチングDTOを作成
        updated_dto = SpeakerMatchingDTO(
            speaker_id=input_dto.speaker_id,
            speaker_name=speaker.name,
            matched_politician_id=input_dto.politician_id,
            matched_politician_name=input_dto.politician_name,
            confidence_score=1.0,
            matching_method="manual",
            matching_reason="手動で政治家を作成・紐付け",
        )

        return LinkSpeakerToPoliticianOutputDto(
            success=True,
            updated_matching_dto=updated_dto,
        )
