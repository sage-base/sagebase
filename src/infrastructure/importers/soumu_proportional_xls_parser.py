"""総務省比例代表XLSファイルパーサー.

XLSファイルのセル値変換・ブロック名検出・当選者フィルタリング等の
ユーティリティ関数、およびxlrdによる直接パース機能を提供する。
"""

import logging
import re

from datetime import date
from pathlib import Path

from src.domain.value_objects.proportional_candidate import (
    ProportionalCandidateRecord,
    ProportionalElectionInfo,
)
from src.infrastructure.importers._constants import PROPORTIONAL_BLOCKS
from src.infrastructure.importers._utils import zen_to_han


logger = logging.getLogger(__name__)

# ブロック名の検出パターン（「ブロック」「選挙区」両方に対応）
_BLOCK_PATTERN = re.compile(
    r"(北海道|東北|北関東|南関東|東京|北陸信越|東海|近畿|中国|四国|九州)"
    r"\s*(?:ブロック|都?選挙区)"
)

_PARTY_GROUP_OFFSETS = [0, 7, 14, 21]

_ELECTION_DATES: dict[int, date] = {
    48: date(2017, 10, 22),
}


def _clean_cell(value: object) -> str:
    """セル値を文字列にクリーンアップする."""
    if value is None:
        return ""
    s = str(value).strip()
    if s == "":
        return ""
    return zen_to_han(s)


def _parse_float(value: object) -> float | None:
    """セル値をfloatに変換する."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value != 0 else None
    s = zen_to_han(str(value).strip().replace(",", "").replace("，", ""))
    s = s.replace("%", "").replace("％", "")
    if not s:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _parse_int(value: object) -> int | None:
    """セル値をintに変換する."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value) if value != 0 else None
    s = zen_to_han(str(value).strip().replace(",", "").replace("，", ""))
    if not s:
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _detect_block_name(row: tuple[object, ...]) -> str | None:
    """行からブロック名を検出する."""
    for cell in row:
        s = _clean_cell(cell)
        if not s:
            continue
        match = _BLOCK_PATTERN.search(s)
        if match:
            return match.group(1)
        # 単純なブロック名一致もチェック
        for block in PROPORTIONAL_BLOCKS:
            if s == block or s == f"{block}ブロック":
                return block
    return None


def get_elected_candidates(
    candidates: list[ProportionalCandidateRecord],
) -> list[ProportionalCandidateRecord]:
    """当選者のみを抽出する."""
    return [c for c in candidates if c.is_elected]


def _clean_name(raw: str) -> str:
    """XLSの氏名セルをクリーンアップする.

    全角スペースによるパディングを除去し、姓と名の間に半角スペースを入れる。
    例: '佐\u3000藤\u3000\u3000英\u3000道' → '佐藤 英道'
    """
    if not raw or not raw.strip():
        return ""
    parts = re.split(r"\u3000{2,}", raw.strip())
    sei = parts[0].replace("\u3000", "") if parts else ""
    mei = parts[1].replace("\u3000", "") if len(parts) > 1 else ""
    return f"{sei} {mei}".strip()


def _parse_winners_count(value: object) -> int:
    """当選人数セルから数値を抽出する.

    例: '3 人　　' → 3
    """
    s = _clean_cell(value)
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else 0


def _parse_proportional_rows(
    rows: list[tuple[object, ...]],
    election_number: int,
) -> list[ProportionalCandidateRecord]:
    """XLSの行データから比例代表候補者レコードを抽出する.

    XLSの構造:
    - セクション開始行: ブロック名（例: '北海道選挙区'）
    - +2行: 政党名（col2, col9, col16, col23 に最大4政党）
    - +4行: 得票数
    - +5行: 当選人数
    - +7行: ヘッダー（名簿, 氏名, 順位, 小選挙区, 惜敗率）
    - +8行〜: 候補者データ
    - 各政党グループの列オフセット: 0, 7, 14, 21
    """
    candidates: list[ProportionalCandidateRecord] = []

    section_starts: list[int] = []
    for i, row in enumerate(rows):
        s = _clean_cell(row[0]) if row else ""
        if "選挙区" in s:
            section_starts.append(i)

    for sec_idx, start in enumerate(section_starts):
        next_start = (
            section_starts[sec_idx + 1]
            if sec_idx + 1 < len(section_starts)
            else len(rows)
        )

        block_text = _clean_cell(rows[start][0])
        m = _BLOCK_PATTERN.search(block_text)
        if not m:
            continue
        block_name = m.group(1)

        if block_name not in PROPORTIONAL_BLOCKS:
            logger.warning("未知のブロック名: %s", block_name)
            continue

        party_row_idx = start + 2
        if party_row_idx >= len(rows):
            continue
        party_row = rows[party_row_idx]

        winners_row_idx = start + 5
        winners_row = rows[winners_row_idx] if winners_row_idx < len(rows) else ()

        data_start = start + 8

        for offset in _PARTY_GROUP_OFFSETS:
            party_col = offset + 2
            if party_col >= len(party_row):
                continue
            party_name = _clean_cell(party_row[party_col])
            if not party_name or party_name == "政党等名":
                continue

            winners_count = _parse_winners_count(
                winners_row[party_col] if party_col < len(winners_row) else None
            )

            name_col = offset + 1
            order_col = offset + 0
            smd_col = offset + 5
            loss_col = offset + 6

            party_candidates: list[ProportionalCandidateRecord] = []
            for r in range(data_start, next_start):
                if r >= len(rows):
                    break
                row = rows[r]
                if name_col >= len(row):
                    continue
                raw_name = str(row[name_col]) if row[name_col] else ""
                name = _clean_name(raw_name)
                if not name:
                    continue

                list_order = (
                    _parse_int(row[order_col] if order_col < len(row) else None) or 0
                )

                smd_val = _clean_cell(row[smd_col] if smd_col < len(row) else None)
                smd_result = smd_val if smd_val in ("当", "落") else ""

                loss_ratio = _parse_float(
                    row[loss_col] if loss_col < len(row) else None
                )

                party_candidates.append(
                    ProportionalCandidateRecord(
                        name=name,
                        party_name=party_name,
                        block_name=block_name,
                        list_order=list_order,
                        smd_result=smd_result,
                        loss_ratio=loss_ratio,
                        is_elected=False,
                    )
                )

            for i, c in enumerate(party_candidates):
                if i < winners_count:
                    party_candidates[i] = ProportionalCandidateRecord(
                        name=c.name,
                        party_name=c.party_name,
                        block_name=c.block_name,
                        list_order=c.list_order,
                        smd_result=c.smd_result,
                        loss_ratio=c.loss_ratio,
                        is_elected=True,
                    )

            candidates.extend(party_candidates)

    return candidates


def parse_proportional_xls(
    file_path: Path,
    election_number: int,
) -> tuple[ProportionalElectionInfo | None, list[ProportionalCandidateRecord]]:
    """xlrdを使用して比例代表XLSファイルをパースする."""
    import xlrd

    wb = xlrd.open_workbook(str(file_path))
    ws = wb.sheet_by_index(0)

    rows: list[tuple[object, ...]] = []
    for row_idx in range(ws.nrows):
        row: tuple[object, ...] = tuple(
            ws.cell_value(row_idx, col_idx) for col_idx in range(ws.ncols)
        )
        rows.append(row)

    candidates = _parse_proportional_rows(rows, election_number)

    election_date = _ELECTION_DATES.get(election_number)
    election_info: ProportionalElectionInfo | None = None
    if election_date:
        election_info = ProportionalElectionInfo(
            election_number=election_number,
            election_date=election_date,
        )

    logger.info(
        "XLSパース完了: %d候補者 (第%d回)",
        len(candidates),
        election_number,
    )
    return election_info, candidates
