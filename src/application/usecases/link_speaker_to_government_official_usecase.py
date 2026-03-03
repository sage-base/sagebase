"""発言者と政府関係者を紐付けるユースケース."""

from src.application.dtos.government_official_dto import (
    LinkSpeakerToGovernmentOfficialInputDto,
    LinkSpeakerToGovernmentOfficialOutputDto,
)
from src.domain.repositories.government_official_repository import (
    GovernmentOfficialRepository,
)
from src.domain.repositories.speaker_repository import SpeakerRepository


class LinkSpeakerToGovernmentOfficialUseCase:
    """発言者と政府関係者を紐付けるユースケース.

    優先度ルール: politician_id設定済みのSpeakerには紐付け不可。
    """

    def __init__(
        self,
        speaker_repository: SpeakerRepository,
        government_official_repository: GovernmentOfficialRepository,
    ):
        self.speaker_repository = speaker_repository
        self.government_official_repository = government_official_repository

    async def execute(
        self, input_dto: LinkSpeakerToGovernmentOfficialInputDto
    ) -> LinkSpeakerToGovernmentOfficialOutputDto:
        speaker = await self.speaker_repository.get_by_id(input_dto.speaker_id)
        if not speaker:
            return LinkSpeakerToGovernmentOfficialOutputDto(
                success=False,
                error_message="発言者が見つかりません",
            )

        if speaker.politician_id is not None:
            return LinkSpeakerToGovernmentOfficialOutputDto(
                success=False,
                error_message="この発言者は既に政治家に紐付けられています",
            )

        official = await self.government_official_repository.get_by_id(
            input_dto.government_official_id
        )
        if not official:
            return LinkSpeakerToGovernmentOfficialOutputDto(
                success=False,
                error_message="政府関係者が見つかりません",
            )

        speaker.government_official_id = input_dto.government_official_id
        speaker.is_politician = False
        speaker.skip_reason = "government_official"

        await self.speaker_repository.update(speaker)

        return LinkSpeakerToGovernmentOfficialOutputDto(success=True)
