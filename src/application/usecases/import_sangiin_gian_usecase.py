"""参議院議案データ（gian.json）インポートユースケース."""

import logging

from typing import Any

from src.application.dtos.smartnews_smri_import_dto import (
    ImportSmartNewsSmriInputDto,
    ImportSmartNewsSmriOutputDto,
)
from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_submitter import ProposalSubmitter
from src.domain.repositories.proposal_repository import ProposalRepository
from src.domain.repositories.proposal_submitter_repository import (
    ProposalSubmitterRepository,
)
from src.infrastructure.importers.smartnews_smri_sangiin_gian_importer import (
    SmartNewsSmriSangiinGianImporter,
)


logger = logging.getLogger(__name__)


class ImportSangiinGianUseCase:
    """参議院議案データのインポートユースケース."""

    def __init__(
        self,
        proposal_repository: ProposalRepository,
        proposal_submitter_repository: ProposalSubmitterRepository | None = None,
    ) -> None:
        self._repo = proposal_repository
        self._submitter_repo = proposal_submitter_repository

    async def execute(
        self,
        input_dto: ImportSmartNewsSmriInputDto,
    ) -> ImportSmartNewsSmriOutputDto:
        """参議院議案データをインポートする."""
        importer = SmartNewsSmriSangiinGianImporter(
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
            output.submitters_created += batch_result.submitters_created

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
            "更新=%d, エラー=%d, 提出者=%d",
            output.total,
            output.created,
            output.skipped,
            output.updated,
            output.errors,
            output.submitters_created,
        )
        return output

    async def _import_batch(
        self,
        importer: SmartNewsSmriSangiinGianImporter,
        records: list[list[Any]],
    ) -> ImportSmartNewsSmriOutputDto:
        result = ImportSmartNewsSmriOutputDto()
        all_submitters: list[ProposalSubmitter] = []
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

                if self._submitter_repo and created_proposal.id is not None:
                    submitter = importer.parse_submitter(record, created_proposal.id)
                    if submitter is not None:
                        all_submitters.append(submitter)
            except Exception:
                logger.exception("レコードのインポートに失敗: %s", record[:5])
                result.errors += 1

        if self._submitter_repo and all_submitters:
            try:
                await self._submitter_repo.bulk_create(all_submitters)
                result.submitters_created = len(all_submitters)
            except Exception:
                logger.exception(
                    "提出者データの保存に失敗 (件数=%d)", len(all_submitters)
                )
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
