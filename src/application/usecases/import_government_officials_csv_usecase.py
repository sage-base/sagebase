"""政府関係者CSVインポートユースケース."""

import logging

from src.application.dtos.government_official_dto import (
    GovernmentOfficialCsvRow,
    ImportGovernmentOfficialsCsvInputDto,
    ImportGovernmentOfficialsCsvOutputDto,
)
from src.domain.entities.government_official import GovernmentOfficial
from src.domain.entities.government_official_position import GovernmentOfficialPosition
from src.domain.repositories.government_official_position_repository import (
    GovernmentOfficialPositionRepository,
)
from src.domain.repositories.government_official_repository import (
    GovernmentOfficialRepository,
)
from src.domain.repositories.speaker_repository import SpeakerRepository


logger = logging.getLogger(__name__)


class ImportGovernmentOfficialsCsvUseCase:
    """Cowork結果CSVから政府関係者をインポートするユースケース.

    CSVの各行からGovernmentOfficialをfind-or-createし、
    GovernmentOfficialPositionをbulk_upsertする。
    """

    def __init__(
        self,
        government_official_repository: GovernmentOfficialRepository,
        government_official_position_repository: GovernmentOfficialPositionRepository,
        speaker_repository: SpeakerRepository,
    ):
        self._official_repo = government_official_repository
        self._position_repo = government_official_position_repository
        self._speaker_repo = speaker_repository

    async def execute(
        self, input_dto: ImportGovernmentOfficialsCsvInputDto
    ) -> ImportGovernmentOfficialsCsvOutputDto:
        output = ImportGovernmentOfficialsCsvOutputDto()

        for row in input_dto.rows:
            try:
                await self._process_row(row, output, input_dto.dry_run)
            except Exception as e:
                error_msg = f"行処理エラー (speaker={row.speaker_name}): {e}"
                logger.warning(error_msg)
                output.errors.append(error_msg)

        return output

    async def _process_row(
        self,
        row: GovernmentOfficialCsvRow,
        output: ImportGovernmentOfficialsCsvOutputDto,
        dry_run: bool,
    ) -> None:
        if not row.organization and not row.position:
            output.skipped_count += 1
            return

        official = await self._official_repo.get_by_name(row.speaker_name)
        if official is None:
            if dry_run:
                output.created_officials_count += 1
            else:
                official = await self._official_repo.create(
                    GovernmentOfficial(name=row.speaker_name)
                )
                output.created_officials_count += 1

        if official and not dry_run:
            position_entity = GovernmentOfficialPosition(
                government_official_id=official.id or 0,
                organization=row.organization,
                position=row.position,
                source_note=row.notes,
            )
            await self._position_repo.bulk_upsert([position_entity])
            output.created_positions_count += 1

            speaker = await self._speaker_repo.get_by_id(row.representative_speaker_id)
            if speaker and speaker.politician_id is None:
                speaker.government_official_id = official.id
                speaker.is_politician = False
                speaker.skip_reason = "government_official"
                await self._speaker_repo.update(speaker)
                output.linked_speakers_count += 1
        elif dry_run:
            output.created_positions_count += 1
            output.linked_speakers_count += 1
