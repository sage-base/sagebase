import logging

from typing import Any

from src.application.dtos.smartnews_smri_import_dto import (
    ImportSmartNewsSmriInputDto,
    ImportSmartNewsSmriOutputDto,
)
from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.domain.entities.proposal import Proposal
from src.domain.repositories.extracted_proposal_judge_repository import (
    ExtractedProposalJudgeRepository,
)
from src.domain.repositories.proposal_repository import ProposalRepository
from src.infrastructure.importers.smartnews_smri_importer import (
    SmartNewsSmriImporter,
)


logger = logging.getLogger(__name__)


class ImportSmartNewsSmriUseCase:
    def __init__(
        self,
        proposal_repository: ProposalRepository,
        extracted_proposal_judge_repository: ExtractedProposalJudgeRepository
        | None = None,
    ) -> None:
        self._repo = proposal_repository
        self._judge_repo = extracted_proposal_judge_repository

    async def execute(
        self,
        input_dto: ImportSmartNewsSmriInputDto,
    ) -> ImportSmartNewsSmriOutputDto:
        importer = SmartNewsSmriImporter(
            governing_body_id=input_dto.governing_body_id,
            conference_id=input_dto.conference_id,
        )
        records = importer.load_json(input_dto.file_path)
        logger.info("レコード数: %d", len(records))

        output = ImportSmartNewsSmriOutputDto(total=len(records))

        for i in range(0, len(records), input_dto.batch_size):
            batch = records[i : i + input_dto.batch_size]
            batch_result = await self._import_batch(importer, batch)
            output.created += batch_result.created
            output.skipped += batch_result.skipped
            output.updated += batch_result.updated
            output.errors += batch_result.errors
            output.judges_created += batch_result.judges_created

            logger.info(
                "バッチ %d/%d 完了: 作成=%d, スキップ=%d, エラー=%d",
                i // input_dto.batch_size + 1,
                (len(records) + input_dto.batch_size - 1) // input_dto.batch_size,
                batch_result.created,
                batch_result.skipped,
                batch_result.errors,
            )

        logger.info(
            "インポート完了: 合計=%d, 作成=%d, スキップ=%d, "
            "更新=%d, エラー=%d, 賛否=%d",
            output.total,
            output.created,
            output.skipped,
            output.updated,
            output.errors,
            output.judges_created,
        )
        return output

    async def _import_batch(
        self,
        importer: SmartNewsSmriImporter,
        records: list[list[Any]],
    ) -> ImportSmartNewsSmriOutputDto:
        result = ImportSmartNewsSmriOutputDto()
        all_judges: list[ExtractedProposalJudge] = []
        for record in records:
            try:
                proposal = importer.parse_record(record)
                is_duplicate, was_updated = await self._check_duplicate(proposal)
                if is_duplicate:
                    result.skipped += 1
                    if was_updated:
                        result.updated += 1
                    continue
                created_proposal = await self._repo.create(proposal)
                result.created += 1

                if self._judge_repo and created_proposal.id is not None:
                    judges = importer.parse_group_judges(record, created_proposal.id)
                    all_judges.extend(judges)
            except Exception:
                logger.exception("レコードのインポートに失敗: %s", record[:4])
                result.errors += 1

        if self._judge_repo and all_judges:
            try:
                await self._judge_repo.bulk_create(all_judges)
                result.judges_created = len(all_judges)
            except Exception:
                logger.exception("賛否データの保存に失敗 (件数=%d)", len(all_judges))
        return result

    async def _check_duplicate(self, proposal: Proposal) -> tuple[bool, bool]:
        """重複チェックし、既存レコードの日付をバックフィルする.

        Returns:
            (is_duplicate, was_updated) のタプル
        """
        existing: Proposal | None = None

        if proposal.has_business_key:
            assert proposal.governing_body_id is not None
            assert proposal.session_number is not None
            assert proposal.proposal_number is not None
            assert proposal.proposal_type is not None
            existing = await self._repo.find_by_identifier(
                governing_body_id=proposal.governing_body_id,
                session_number=proposal.session_number,
                proposal_number=proposal.proposal_number,
                proposal_type=proposal.proposal_type,
            )
        elif proposal.external_id:
            existing = await self._repo.find_by_url(proposal.external_id)

        if existing is None:
            return (False, False)

        was_updated = await self._backfill_dates(existing, proposal)
        return (True, was_updated)

    async def _backfill_dates(self, existing: Proposal, new_data: Proposal) -> bool:
        """既存レコードの日付がNULLの場合、新データで補完する."""
        needs_update = False

        if existing.submitted_date is None and new_data.submitted_date is not None:
            existing.submitted_date = new_data.submitted_date
            needs_update = True

        if existing.voted_date is None and new_data.voted_date is not None:
            existing.voted_date = new_data.voted_date
            needs_update = True

        if needs_update:
            await self._repo.update(existing)

        return needs_update
