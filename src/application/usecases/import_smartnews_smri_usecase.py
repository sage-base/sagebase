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
        importer = SmartNewsSmriImporter(governing_body_id=input_dto.governing_body_id)
        records = importer.load_json(input_dto.file_path)
        logger.info("レコード数: %d", len(records))

        output = ImportSmartNewsSmriOutputDto(total=len(records))

        for i in range(0, len(records), input_dto.batch_size):
            batch = records[i : i + input_dto.batch_size]
            batch_result = await self._import_batch(importer, batch)
            output.created += batch_result.created
            output.skipped += batch_result.skipped
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
            "インポート完了: 合計=%d, 作成=%d, スキップ=%d, エラー=%d, 賛否=%d",
            output.total,
            output.created,
            output.skipped,
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
                if await self._check_duplicate(proposal):
                    result.skipped += 1
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

    async def _check_duplicate(self, proposal: Proposal) -> bool:
        if proposal.has_business_key:
            # has_business_keyがTrueの時点で全てnon-None（型チェッカー用ガード）
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
            return existing is not None

        if proposal.external_id:
            existing = await self._repo.find_by_url(
                proposal.external_id,
            )
            return existing is not None

        # ビジネスキーもexternal_idもない場合は重複チェック不可
        return False
