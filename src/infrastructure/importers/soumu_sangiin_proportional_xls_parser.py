"""総務省参議院比例代表XLSファイルパーサー.

参議院比例代表（全国一区・非拘束名簿式）のXLS/XLSXファイルから
候補者データを抽出する。

XLS構造（「党派別名簿登載者別得票数、当選人数」シート）:
    - 複数セクションに分かれ、各セクションで最大4政党が横並び
    - 各政党は6列幅（offset 0, 6, 12, 18）
    - セクション構造:
        - 「政党等の名称」行でセクション開始を検出
        - +1行: 政党名
        - +7行付近: 「得票順位」「当落」「名簿登載者名」ヘッダー
        - 以降: 候補者データ（「当」で当選判定）
"""

import logging
import re

from pathlib import Path

from src.domain.value_objects.proportional_candidate import (
    ProportionalCandidateRecord,
    ProportionalElectionInfo,
)
from src.infrastructure.importers._utils import zen_to_han
from src.infrastructure.importers.soumu_sangiin_election_scraper import (
    SANGIIN_ELECTION_DATES,
)


logger = logging.getLogger(__name__)

_ELECTED_PATTERNS = re.compile(r"^(当選?|○)$")
_NAME_CLEANUP = re.compile(r"\s+")
_PARTY_GROUP_WIDTH = 6
_MAX_PARTY_GROUPS = 4


def _clean_cell(value: object) -> str:
    """セル値を文字列にクリーンアップする."""
    if value is None:
        return ""
    s = str(value).strip()
    if s == "":
        return ""
    return zen_to_han(s)


def _clean_name(raw: str) -> str:
    """候補者名をクリーンアップする."""
    name = _NAME_CLEANUP.sub("", raw).strip()
    name = name.replace("\u3000", "").replace(" ", "")
    if not name or name.isdigit():
        return ""
    return name


def _is_elected(value: str) -> bool:
    """当選フラグを判定する."""
    return bool(_ELECTED_PATTERNS.match(value))


def _is_meibo_torokusha_file(rows: list[tuple[object, ...]]) -> bool:
    """「党派別名簿登載者別得票数」ファイルかどうかを判定する."""
    for row in rows[:5]:
        first = _clean_cell(row[0]) if row else ""
        if "名簿登載者" in first and "得票" in first:
            return True
    return False


def _find_section_starts(rows: list[tuple[object, ...]]) -> list[int]:
    """「政党等の名称」行のインデックスを検出する."""
    starts: list[int] = []
    for i, row in enumerate(rows):
        cell = _clean_cell(row[0]) if row else ""
        if cell == "政党等の名称":
            starts.append(i)
    return starts


def _parse_meibo_torokusha(
    rows: list[tuple[object, ...]],
) -> list[ProportionalCandidateRecord]:
    """「党派別名簿登載者別得票数」XLSをパースする.

    構造:
    - 複数セクション（「政党等の名称」行で区切り）
    - 各セクション内で最大4政党が横並び（6列幅: offset 0,6,12,18）
    - セクション内レイアウト:
        +1行: 政党名（offset+3の列）
        +9行付近: 「得票順位」「当落」ヘッダー行
        +11行以降: 候補者データ
    """
    candidates: list[ProportionalCandidateRecord] = []
    section_starts = _find_section_starts(rows)

    for sec_idx, start in enumerate(section_starts):
        next_start = (
            section_starts[sec_idx + 1]
            if sec_idx + 1 < len(section_starts)
            else len(rows)
        )

        # 各政党グループを処理
        for group in range(_MAX_PARTY_GROUPS):
            offset = group * _PARTY_GROUP_WIDTH

            # 政党名を取得（セクション開始+1行目、offset+3列）
            party_name_col = offset + 3
            party_row_idx = start + 1
            if party_row_idx >= len(rows):
                continue
            party_row = rows[party_row_idx]
            if party_name_col >= len(party_row):
                continue
            party_name = _clean_cell(party_row[party_name_col])
            if not party_name:
                continue

            # 「得票順位」「順位」ヘッダー行を検出
            data_start = None
            for r in range(start + 2, min(start + 15, next_start)):
                if r >= len(rows):
                    break
                cell = _clean_cell(rows[r][offset]) if offset < len(rows[r]) else ""
                if "順位" in cell:
                    data_start = r + 2  # ヘッダー行 + 空行1行
                    break

            if data_start is None:
                continue

            # 候補者データ行: [得票順位, 当落, 名簿登載者名, ?, 得票数, ?]
            elected_col = offset + 1
            name_col = offset + 2

            for r in range(data_start, next_start):
                if r >= len(rows):
                    break
                row = rows[r]
                if name_col >= len(row):
                    continue

                name = _clean_name(_clean_cell(row[name_col]))
                if not name:
                    continue

                elected = False
                if elected_col < len(row):
                    elected = _is_elected(_clean_cell(row[elected_col]))

                candidates.append(
                    ProportionalCandidateRecord(
                        name=name,
                        party_name=party_name,
                        block_name="比例代表",
                        list_order=0,
                        smd_result="",
                        loss_ratio=None,
                        is_elected=elected,
                    )
                )

    return candidates


def _detect_header_columns(
    rows: list[tuple[object, ...]],
) -> dict[str, int] | None:
    """ヘッダー行を検出し、各列のインデックスを返す.

    Returns:
        {"name": col_idx, "party": col_idx, "elected": col_idx}
        or None if header not found
    """
    for row_idx, row in enumerate(rows):
        cells = [_clean_cell(c) for c in row]
        name_col = None
        party_col = None
        elected_col = None

        for col_idx, cell in enumerate(cells):
            if "候補者" in cell or "氏名" in cell or "名前" in cell:
                name_col = col_idx
            elif "政党" in cell or "名簿届出政党" in cell:
                party_col = col_idx
            elif "当選" in cell or "当落" in cell or cell == "当":
                elected_col = col_idx

        if name_col is not None and (elected_col is not None or party_col is not None):
            result = {
                "name": name_col,
                "header_row": row_idx,
            }
            if party_col is not None:
                result["party"] = party_col
            if elected_col is not None:
                result["elected"] = elected_col
            return result

    return None


def _parse_with_header(
    rows: list[tuple[object, ...]],
    columns: dict[str, int],
) -> list[ProportionalCandidateRecord]:
    """ヘッダー検出結果に基づいてパースする."""
    candidates: list[ProportionalCandidateRecord] = []
    data_start = columns["header_row"] + 1
    name_col = columns["name"]
    party_col = columns.get("party")
    elected_col = columns.get("elected")
    current_party = ""

    for row_idx in range(data_start, len(rows)):
        row = rows[row_idx]
        if name_col >= len(row):
            continue

        name = _clean_name(_clean_cell(row[name_col]))
        if not name:
            if party_col is not None and party_col < len(row):
                party_val = _clean_cell(row[party_col])
                if party_val and not party_val.isdigit():
                    current_party = party_val
            continue

        party = ""
        if party_col is not None and party_col < len(row):
            party_val = _clean_cell(row[party_col])
            if party_val and not party_val.isdigit():
                party = party_val
        if not party:
            party = current_party

        elected = False
        if elected_col is not None and elected_col < len(row):
            elected = _is_elected(_clean_cell(row[elected_col]))

        candidates.append(
            ProportionalCandidateRecord(
                name=name,
                party_name=party,
                block_name="比例代表",
                list_order=0,
                smd_result="",
                loss_ratio=None,
                is_elected=elected,
            )
        )

    return candidates


def _parse_fallback(
    rows: list[tuple[object, ...]],
) -> list[ProportionalCandidateRecord]:
    """ヘッダーが見つからない場合のフォールバックパース."""
    candidates: list[ProportionalCandidateRecord] = []
    current_party = ""

    for row in rows:
        cells = [_clean_cell(c) for c in row]
        if len(cells) < 2:
            continue

        first = cells[0]
        if ("党" in first or "の会" in first or "クラブ" in first) and len(first) < 30:
            current_party = first
            continue

        elected = False
        name = ""
        for _i, cell in enumerate(cells):
            if _is_elected(cell):
                elected = True
            if (
                len(cell) >= 2
                and not cell.isdigit()
                and not _is_elected(cell)
                and "合計" not in cell
                and "計" not in cell
                and "政党" not in cell
                and "候補" not in cell
            ):
                if not name:
                    name = _clean_name(cell)

        if name:
            candidates.append(
                ProportionalCandidateRecord(
                    name=name,
                    party_name=current_party,
                    block_name="比例代表",
                    list_order=0,
                    smd_result="",
                    loss_ratio=None,
                    is_elected=elected,
                )
            )

    return candidates


def parse_sangiin_proportional_xls(
    file_path: Path,
    election_number: int,
) -> tuple[ProportionalElectionInfo | None, list[ProportionalCandidateRecord]]:
    """参議院比例代表XLSファイルをパースする.

    Args:
        file_path: XLSファイルパス
        election_number: 選挙回次

    Returns:
        (選挙情報, 候補者レコードリスト)
    """
    rows = _read_xls_rows(file_path)

    if _is_meibo_torokusha_file(rows):
        candidates = _parse_meibo_torokusha(rows)
    else:
        columns = _detect_header_columns(rows)
        if columns is not None:
            candidates = _parse_with_header(rows, columns)
        else:
            candidates = _parse_fallback(rows)

    election_date = SANGIIN_ELECTION_DATES.get(election_number)
    election_info: ProportionalElectionInfo | None = None
    if election_date:
        election_info = ProportionalElectionInfo(
            election_number=election_number,
            election_date=election_date,
        )

    elected_count = sum(1 for c in candidates if c.is_elected)
    logger.info(
        "参議院比例代表パース完了: %d候補者 (当選%d名, 第%d回, %s)",
        len(candidates),
        elected_count,
        election_number,
        file_path.name,
    )
    return election_info, candidates


def _read_xls_rows(file_path: Path) -> list[tuple[object, ...]]:
    """XLS/XLSXファイルを読み込んで行データを返す."""
    suffix = file_path.suffix.lower()
    if suffix == ".xlsx":
        return _read_xlsx_rows(file_path)
    return _read_xls_rows_xlrd(file_path)


def _read_xls_rows_xlrd(file_path: Path) -> list[tuple[object, ...]]:
    """xlrdでXLSファイルを読み込む."""
    import xlrd

    wb = xlrd.open_workbook(str(file_path))
    ws = wb.sheet_by_index(0)

    rows: list[tuple[object, ...]] = []
    for row_idx in range(ws.nrows):
        row: tuple[object, ...] = tuple(
            ws.cell_value(row_idx, col_idx) for col_idx in range(ws.ncols)
        )
        rows.append(row)
    return rows


def _read_xlsx_rows(file_path: Path) -> list[tuple[object, ...]]:
    """openpyxlでXLSXファイルを読み込む."""
    import openpyxl

    wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        return []

    rows: list[tuple[object, ...]] = []
    for row in ws.iter_rows():
        rows.append(tuple(cell.value for cell in row))
    wb.close()
    return rows
