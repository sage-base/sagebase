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

        # 1. GovernmentOfficial の find-or-create
        official = await self._official_repo.get_by_name(row.speaker_name)
        is_new_official = official is None
        if is_new_official:
            if not dry_run:
                official = await self._official_repo.create(
                    GovernmentOfficial(name=row.speaker_name)
                )
            output.created_officials_count += 1

        # 2. GovernmentOfficialPosition の upsert
        if official and not dry_run:
            assert official.id is not None, "作成済みのofficialにIDが必要です"
            position_entity = GovernmentOfficialPosition(
                government_official_id=official.id,
                organization=row.organization,
                position=row.position,
                source_note=row.notes,
            )
            await self._position_repo.bulk_upsert([position_entity])
        output.created_positions_count += 1

        # 3. 同名Speaker全件を紐付け
        same_name_speakers = await self._speaker_repo.search_by_name(row.speaker_name)
        for speaker in same_name_speakers:
            if speaker.name != row.speaker_name:
                continue
            if speaker.politician_id is not None:
                continue
            if not dry_run and official:
                assert official.id is not None
                speaker.link_to_government_official(official.id)
                await self._speaker_repo.update(speaker)
            output.linked_speakers_count += 1
