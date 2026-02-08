import json
import logging

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.domain.entities.proposal import Proposal
from src.domain.repositories.proposal_repository import ProposalRepository


logger = logging.getLogger(__name__)

CATEGORY_MAP: dict[str, str] = {
    "衆法": "legislation",
    "閣法": "legislation",
    "参法": "legislation",
    "予算": "budget",
    "条約": "treaty",
    "承認": "approval",
    "承諾": "approval",
    "決算": "audit",
    "国有財産": "audit",
    "ＮＨＫ決算": "audit",
    "決議": "other",
    "規程": "other",
    "規則": "other",
    "議決": "other",
    "国庫債務": "other",
    "憲法八条議決案": "other",
}

RESULT_MAP: dict[str, str] = {
    "成立": "passed",
    "本院議了": "passed",
    "両院承認": "passed",
    "両院承諾": "passed",
    "本院可決": "passed",
    "参議院回付案（同意）": "passed",
    "衆議院議決案（可決）": "passed",
    "参議院議了": "passed",
    "両院議決": "passed",
    "衆議院回付案(同意) ": "passed",
    "衆議院回付案（同意）": "passed",
    "本院修正議決": "passed",
    "承認": "passed",
    "修正承諾": "passed",
    "撤回承諾": "passed",
    "議決不要": "passed",
    "未了": "expired",
    "撤回": "withdrawn",
    "衆議院で閉会中審査": "pending",
    "参議院で閉会中審査": "pending",
    "中間報告": "pending",
    "両院の意見が一致しない旨報告": "rejected",
    "参議院回付案（不同意）": "rejected",
    "承諾なし": "rejected",
    "衆議院で併合修正": "other",
}


@dataclass
class ImportResult:
    total: int = 0
    created: int = 0
    skipped: int = 0
    errors: int = 0


class SmartNewsSmriImporter:
    def __init__(
        self,
        proposal_repository: ProposalRepository,
        governing_body_id: int,
    ) -> None:
        self._repo = proposal_repository
        self._governing_body_id = governing_body_id

    def load_json(self, file_path: Path) -> list[list[Any]]:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)

    def parse_record(self, record: list[Any]) -> Proposal:
        proposal_type = record[0] if record[0] else None
        session_number_str = record[1]
        proposal_number_str = record[2]
        title = record[3]
        raw_result = record[5]

        external_id = self._extract_external_id(record)

        session_number = int(session_number_str) if session_number_str else None
        proposal_number = int(proposal_number_str) if proposal_number_str else None

        proposal_category = self._map_category(record[0])
        deliberation_result = self._normalize_result(raw_result)

        return Proposal(
            title=title,
            proposal_type=proposal_type,
            proposal_category=proposal_category,
            session_number=session_number,
            proposal_number=proposal_number,
            governing_body_id=self._governing_body_id,
            external_id=external_id,
            deliberation_result=deliberation_result,
            detail_url=external_id,
        )

    async def import_data(
        self,
        records: list[list[Any]],
        batch_size: int = 100,
    ) -> ImportResult:
        result = ImportResult(total=len(records))

        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            batch_result = await self._import_batch(batch)
            result.created += batch_result.created
            result.skipped += batch_result.skipped
            result.errors += batch_result.errors

            logger.info(
                "バッチ %d/%d 完了: 作成=%d, スキップ=%d, エラー=%d",
                i // batch_size + 1,
                (len(records) + batch_size - 1) // batch_size,
                batch_result.created,
                batch_result.skipped,
                batch_result.errors,
            )

        logger.info(
            "インポート完了: 合計=%d, 作成=%d, スキップ=%d, エラー=%d",
            result.total,
            result.created,
            result.skipped,
            result.errors,
        )
        return result

    async def _import_batch(self, records: list[list[Any]]) -> ImportResult:
        result = ImportResult()
        for record in records:
            try:
                proposal = self.parse_record(record)
                is_duplicate = await self._check_duplicate(proposal)
                if is_duplicate:
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
            existing = await self._repo.find_by_url(proposal.external_id)
            return existing is not None

        return False

    @staticmethod
    def _map_category(raw_type: str) -> str:
        return CATEGORY_MAP.get(raw_type, "other")

    @staticmethod
    def _normalize_result(raw_result: str) -> str | None:
        if not raw_result:
            return None
        return RESULT_MAP.get(raw_result)

    @staticmethod
    def _extract_external_id(record: list[Any]) -> str | None:
        try:
            nested = record[10]
            if nested and nested[0] and len(nested[0]) > 3:
                url = nested[0][3]
                return url if url else None
        except (IndexError, TypeError):
            pass
        return None
