import json
import logging

from pathlib import Path
from typing import Any

from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.domain.entities.proposal import Proposal


logger = logging.getLogger(__name__)

# gian_summary.json のフィールドインデックス
_IDX_PROPOSAL_TYPE = 0
_IDX_SESSION_NUMBER = 1
_IDX_PROPOSAL_NUMBER = 2
_IDX_TITLE = 3
_IDX_RESULT = 5
_IDX_NESTED_DATA = 10
_IDX_NESTED_URL = 3
_IDX_NESTED_SANSEI_KAIHA = 14
_IDX_NESTED_HANTAI_KAIHA = 15

_SOURCE_URL = "smartnews-smri/house-of-representatives"


class SmartNewsSmriImporter:
    def __init__(self, governing_body_id: int, conference_id: int) -> None:
        self._governing_body_id = governing_body_id
        self._conference_id = conference_id

    def load_json(self, file_path: Path) -> list[list[Any]]:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)

    def parse_record(self, record: list[Any]) -> Proposal:
        raw_type = record[_IDX_PROPOSAL_TYPE]
        proposal_type = raw_type if raw_type else None
        session_number_str = record[_IDX_SESSION_NUMBER]
        proposal_number_str = record[_IDX_PROPOSAL_NUMBER]
        title = record[_IDX_TITLE]
        raw_result = record[_IDX_RESULT]

        external_id = self._extract_external_id(record)

        session_number = int(session_number_str) if session_number_str else None
        proposal_number = int(proposal_number_str) if proposal_number_str else None

        proposal_category = Proposal.normalize_category(raw_type)
        deliberation_result = Proposal.normalize_result(raw_result)
        deliberation_status = raw_result.strip() if raw_result else None

        return Proposal(
            title=title,
            proposal_type=proposal_type,
            proposal_category=proposal_category,
            session_number=session_number,
            proposal_number=proposal_number,
            governing_body_id=self._governing_body_id,
            conference_id=self._conference_id,
            external_id=external_id,
            deliberation_result=deliberation_result,
            deliberation_status=deliberation_status,
            detail_url=external_id,
        )

    @staticmethod
    def parse_group_judges(
        record: list[Any], proposal_id: int
    ) -> list[ExtractedProposalJudge]:
        judges: list[ExtractedProposalJudge] = []
        try:
            nested = record[_IDX_NESTED_DATA]
            if not nested or not nested[0]:
                return judges
            row = nested[0]
            for idx, judgment in [
                (_IDX_NESTED_SANSEI_KAIHA, "賛成"),
                (_IDX_NESTED_HANTAI_KAIHA, "反対"),
            ]:
                if len(row) <= idx:
                    continue
                raw = row[idx]
                if not raw:
                    continue
                for group_name in raw.split(";"):
                    stripped = group_name.strip()
                    if not stripped:
                        continue
                    judges.append(
                        ExtractedProposalJudge(
                            proposal_id=proposal_id,
                            extracted_parliamentary_group_name=stripped,
                            extracted_judgment=judgment,
                            source_url=_SOURCE_URL,
                            matching_status="pending",
                        )
                    )
        except (IndexError, TypeError):
            logger.debug("会派賛否データの解析をスキップ: %s", record[:4])
        return judges

    @staticmethod
    def _extract_external_id(record: list[Any]) -> str | None:
        try:
            nested = record[_IDX_NESTED_DATA]
            if nested and nested[0] and len(nested[0]) > _IDX_NESTED_URL:
                url = nested[0][_IDX_NESTED_URL]
                return url if url else None
        except (IndexError, TypeError):
            pass
        return None
