"""smartnews-smri 参議院議案データ（gian.json）インポーター.

参議院gian.jsonは2次元配列（ヘッダー行 + データ行）形式。
衆議院版（gian_summary.json）とはフォーマットが異なる。

データソース:
    https://github.com/smartnews-smri/house-of-councillors/blob/main/data/gian.json
"""

import json
import logging

from datetime import date
from pathlib import Path
from typing import Any

from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_submitter import ProposalSubmitter
from src.domain.value_objects.submitter_type import SubmitterType


logger = logging.getLogger(__name__)

# gian.json のカラムインデックス（ヘッダー行から特定）
_IDX_SESSION_NUMBER = 0  # 審議回次
_IDX_PROPOSAL_TYPE = 1  # 種類
_IDX_SUBMISSION_SESSION = 2  # 提出回次
_IDX_PROPOSAL_NUMBER = 3  # 提出番号
_IDX_TITLE = 4  # 件名
_IDX_GIAN_URL = 5  # 議案URL
_IDX_SUBMITTED_DATE = 8  # 議案審議情報一覧 - 提出日
_IDX_INITIATOR = 13  # 議案審議情報一覧 - 発議者
_IDX_SUBMITTER = 14  # 議案審議情報一覧 - 提出者
_IDX_SUBMITTER_TYPE = 15  # 議案審議情報一覧 - 提出者区分
_IDX_SANGIIN_PLENARY_VOTE_DATE = 20  # 参議院本会議経過情報 - 議決日
_IDX_SANGIIN_PLENARY_RESULT = 21  # 参議院本会議経過情報 - 議決
_IDX_SANGIIN_VOTE_MANNER = 23  # 参議院本会議経過情報 - 採決態様
_IDX_SANGIIN_VOTE_METHOD = 24  # 参議院本会議経過情報 - 採決方法

# 提出者区分 → SubmitterType マッピング
_SUBMITTER_TYPE_MAP: dict[str, SubmitterType] = {
    "議員": SubmitterType.POLITICIAN,
    "委員長": SubmitterType.COMMITTEE,
    "委員会": SubmitterType.COMMITTEE,
}


class SmartNewsSmriSangiinGianImporter:
    """参議院gian.jsonのインポーター."""

    def __init__(self, governing_body_id: int, conference_id: int) -> None:
        self._governing_body_id = governing_body_id
        self._conference_id = conference_id

    def load_json(self, file_path: Path) -> list[list[Any]]:
        """JSONファイルを読み込み、ヘッダー行をスキップしてデータ行のみ返す."""
        with open(file_path, encoding="utf-8") as f:
            raw_data: list[list[Any]] = json.load(f)
        if len(raw_data) < 2:
            logger.warning("gian.jsonにデータ行がありません")
            return []
        # ヘッダー行（index 0）をスキップ
        return raw_data[1:]

    def parse_record(self, row: list[Any]) -> Proposal:
        """1データ行をProposalエンティティに変換する."""
        raw_type = self._safe_str(row, _IDX_PROPOSAL_TYPE)
        proposal_type = raw_type if raw_type else None
        title = self._safe_str(row, _IDX_TITLE)
        if not title:
            msg = "件名が空です"
            raise ValueError(msg)

        session_number = self._safe_int(row, _IDX_SESSION_NUMBER)
        proposal_number = self._safe_int(row, _IDX_PROPOSAL_NUMBER)
        external_id = self._safe_str(row, _IDX_GIAN_URL) or None

        proposal_category = Proposal.normalize_category(raw_type)

        raw_result = self._safe_str(row, _IDX_SANGIIN_PLENARY_RESULT)
        deliberation_result = Proposal.normalize_result(raw_result)
        deliberation_status = raw_result.strip() if raw_result else None

        submitted_date = self._parse_iso_date(self._safe_str(row, _IDX_SUBMITTED_DATE))
        voted_date = self._parse_iso_date(
            self._safe_str(row, _IDX_SANGIIN_PLENARY_VOTE_DATE)
        )

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
            submitted_date=submitted_date,
            voted_date=voted_date,
        )

    def parse_submitter(
        self, row: list[Any], proposal_id: int
    ) -> ProposalSubmitter | None:
        """データ行から提出者情報を抽出する.

        提出者名が空の場合はNoneを返す。
        """
        submitter_name = self._safe_str(row, _IDX_SUBMITTER)
        if not submitter_name:
            # 発議者フィールドも確認
            submitter_name = self._safe_str(row, _IDX_INITIATOR)
        if not submitter_name:
            return None

        raw_type = self._safe_str(row, _IDX_SUBMITTER_TYPE)
        submitter_type = _SUBMITTER_TYPE_MAP.get(raw_type, SubmitterType.OTHER)

        return ProposalSubmitter(
            proposal_id=proposal_id,
            submitter_type=submitter_type,
            raw_name=submitter_name.strip(),
            is_representative=True,
            display_order=0,
        )

    @staticmethod
    def _parse_iso_date(text: str) -> date | None:
        """ISO形式（YYYY-MM-DD）の日付文字列をパースする."""
        if not text or not text.strip():
            return None
        try:
            return date.fromisoformat(text.strip())
        except ValueError:
            logger.debug("ISO日付のパースに失敗: %s", text)
            return None

    @staticmethod
    def _safe_str(row: list[Any], idx: int) -> str:
        """安全に文字列を取得する."""
        if idx >= len(row):
            return ""
        val = row[idx]
        if val is None:
            return ""
        return str(val).strip()

    @staticmethod
    def _safe_int(row: list[Any], idx: int) -> int | None:
        """安全に整数を取得する."""
        if idx >= len(row):
            return None
        val = row[idx]
        if val is None or (isinstance(val, str) and not val.strip()):
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None
