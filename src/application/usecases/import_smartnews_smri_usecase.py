import logging

from typing import Any

from src.application.dtos.smartnews_smri_import_dto import (
    ImportSmartNewsSmriInputDto,
    ImportSmartNewsSmriOutputDto,
)
from src.domain.entities.proposal import Proposal
from src.domain.repositories.proposal_repository import ProposalRepository
from src.infrastructure.importers.smartnews_smri_importer import (
    SmartNewsSmriImporter,
)


logger = logging.getLogger(__name__)


class ImportSmartNewsSmriUseCase:
    def __init__(
        self,
        proposal_repository: ProposalRepository,
    ) -> None:
        self._repo = proposal_repository

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

            logger.info(
                "バッチ %d/%d 完了: 作成=%d, スキップ=%d, エラー=%d",
                i // input_dto.batch_size + 1,
                (len(records) + input_dto.batch_size - 1) // input_dto.batch_size,
                batch_result.created,
                batch_result.skipped,
                batch_result.errors,
            )

        logger.info(
            "インポート完了: 合計=%d, 作成=%d, スキップ=%d, エラー=%d",
            output.total,
            output.created,
            output.skipped,
            output.errors,
        )
        return output

    async def _import_batch(
        self,
        importer: SmartNewsSmriImporter,
        records: list[list[Any]],
    ) -> ImportSmartNewsSmriOutputDto:
        result = ImportSmartNewsSmriOutputDto()
        for record in records:
            try:
                proposal = importer.parse_record(record)
                if await self._check_duplicate(proposal):
                    result.skipped += 1
                    continue
                await self._repo.create(proposal)
                result.created += 1
            except Exception:
                logger.exception("レコードのインポートに失敗: %s", record[:4])
                result.errors += 1
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
