"""衆参の時代別 会派⇔政党マッピング調査スクリプト.

SMRI/参議院データから会派名を抽出・分析し、
既存seedデータとの差分検出、political_party_idマッピング提案を行う。
DB接続不要のスタンドアロンスクリプト。

使い方:
    # Docker経由で実行（推奨）
    docker compose exec app uv run python scripts/investigate_kaiha_mapping.py

    # ローカルで実行
    uv run python scripts/investigate_kaiha_mapping.py

    # オフラインモード（事前にダウンロードしたファイルを指定）
    uv run python scripts/investigate_kaiha_mapping.py \
        --gian-summary /tmp/gian_summary.json \
        --kaiha /tmp/kaiha.json \
        --giin /tmp/giin.json

データソース:
    衆議院: https://github.com/smartnews-smri/house-of-representatives/blob/main/data/gian_summary.json
    参議院会派: https://github.com/smartnews-smri/house-of-councillors/blob/main/data/kaiha.json
    参議院議員: https://github.com/smartnews-smri/house-of-councillors/blob/main/data/giin.json

出力:
    tmp/kaiha_shuugiin_by_session.csv  - 回次別衆議院会派一覧
    tmp/kaiha_sangiin_current.csv      - 参議院現行会派一覧
    tmp/kaiha_mapping_proposal.json    - マッピング提案
    tmp/kaiha_unmapped_groups.csv      - 未マッピング会派
"""

import argparse
import csv
import json
import logging
import re
import sys
import tempfile
import urllib.request

from collections import defaultdict
from pathlib import Path
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# --- データソースURL ---
GIAN_SUMMARY_URL = (
    "https://raw.githubusercontent.com/"
    "smartnews-smri/house-of-representatives/main/data/gian_summary.json"
)
KAIHA_URL = (
    "https://raw.githubusercontent.com/"
    "smartnews-smri/house-of-councillors/main/data/kaiha.json"
)
GIIN_URL = (
    "https://raw.githubusercontent.com/"
    "smartnews-smri/house-of-councillors/main/data/giin.json"
)

# --- gian_summary.json フィールドインデックス（SmartNewsSmriImporter準拠） ---
IDX_SESSION_NUMBER = 1
IDX_NESTED_DATA = 10
IDX_NESTED_SANSEI_KAIHA = 14
IDX_NESTED_HANTAI_KAIHA = 15

# --- giin.json フィールドインデックス（SmartNewsSmriSangiinDataSource準拠） ---
IDX_GIIN_PARTY = 4

# --- kaiha.json フィールドインデックス ---
IDX_KAIHA_NAME = 1
IDX_KAIHA_SHORT_NAME = 2

# --- 出力先ディレクトリ ---
OUTPUT_DIR = Path("tmp")


def download_file(url: str) -> Path:
    """URLからファイルをダウンロードして一時ファイルパスを返す."""
    logger.info("ダウンロード中: %s", url)
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    urllib.request.urlretrieve(url, tmp.name)  # noqa: S310
    size_mb = Path(tmp.name).stat().st_size / 1_000_000
    logger.info("ダウンロード完了: %.1f MB", size_mb)
    return Path(tmp.name)


def load_json(file_path: Path) -> list[Any]:
    """JSONファイルを読み込む."""
    with open(file_path, encoding="utf-8") as f:
        data: list[Any] = json.load(f)
        return data


# =============================================================================
# 1. 衆議院（gian_summary.json）: 回次ごとの会派名一覧を抽出
# =============================================================================


def extract_shuugiin_kaiha(data: list[Any]) -> dict[int, dict[str, int]]:
    """gian_summary.jsonから回次ごとの会派名と出現回数を抽出する.

    gian_summary.jsonの構造:
      - data[i][1]: 回次（文字列）
      - data[i][10]: nested（リストのリスト）
      - data[i][10][0][14]: 賛成会派（半角セミコロン「; 」区切り）
      - data[i][10][0][15]: 反対会派（半角セミコロン「; 」区切り）

    また、data[i][7]にも提出会派（半角セミコロン区切り）が含まれる。

    Returns:
        {回次: {会派名: 出現回数}} の辞書
    """
    session_kaiha: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for record in data:
        if not isinstance(record, list) or len(record) <= IDX_NESTED_DATA:
            continue

        try:
            session_number = int(record[IDX_SESSION_NUMBER])
        except (ValueError, TypeError, IndexError):
            continue

        # 提出会派（idx 7）からも会派名を取得
        submitter_kaiha = record[7] if len(record) > 7 else None
        if submitter_kaiha and isinstance(submitter_kaiha, str):
            # 全角セミコロンを半角に正規化してから分割
            normalized = submitter_kaiha.replace("；", ";")
            for name in normalized.split(";"):
                name = name.strip()
                if name:
                    session_kaiha[session_number][name] += 1

        nested = record[IDX_NESTED_DATA]
        if not isinstance(nested, list) or not nested:
            continue

        # nested[0]がサブリスト
        row = nested[0]
        if not isinstance(row, list):
            continue

        # 賛成会派（idx 14）と反対会派（idx 15）を取得
        for kaiha_idx in (IDX_NESTED_SANSEI_KAIHA, IDX_NESTED_HANTAI_KAIHA):
            if len(row) <= kaiha_idx:
                continue
            kaiha_str = row[kaiha_idx]
            if not kaiha_str or not isinstance(kaiha_str, str):
                continue
            # 会派名は半角セミコロン「;」区切り（前後にスペースあり）
            for name in kaiha_str.split(";"):
                name = name.strip()
                if name:
                    session_kaiha[session_number][name] += 1

    return dict(session_kaiha)


def aggregate_shuugiin_kaiha(
    session_kaiha: dict[int, dict[str, int]],
) -> list[dict[str, Any]]:
    """回次ごとの会派データをCSV出力用のフラットなリストに変換する.

    Returns:
        [{"session": int, "kaiha_name": str, "count": int}, ...] のリスト
    """
    rows = []
    for session_num in sorted(session_kaiha.keys()):
        for name, count in sorted(session_kaiha[session_num].items()):
            rows.append({"session": session_num, "kaiha_name": name, "count": count})
    return rows


def get_all_shuugiin_kaiha_with_range(
    session_kaiha: dict[int, dict[str, int]],
) -> dict[str, dict[str, Any]]:
    """全会派名とその出現回次範囲を算出する.

    Returns:
        {会派名: {"min_session": int, "max_session": int, "total_count": int}}
    """
    kaiha_range: dict[str, dict[str, Any]] = {}
    for session_num, kaiha_dict in session_kaiha.items():
        for name, count in kaiha_dict.items():
            if name not in kaiha_range:
                kaiha_range[name] = {
                    "min_session": session_num,
                    "max_session": session_num,
                    "total_count": count,
                }
            else:
                entry = kaiha_range[name]
                entry["min_session"] = min(entry["min_session"], session_num)
                entry["max_session"] = max(entry["max_session"], session_num)
                entry["total_count"] += count
    return kaiha_range


# =============================================================================
# 2. 参議院会派（kaiha.json）: 現行会派一覧を抽出
# =============================================================================


def extract_sangiin_kaiha(data: list[Any]) -> list[dict[str, str]]:
    """kaiha.jsonから参議院の現行会派一覧を抽出する.

    kaiha.jsonの構造: ヘッダー行(index 0) + データ行
    各行: [ID?, 会派名, 略称, ...]

    Returns:
        [{"name": str, "short_name": str}, ...] のリスト
    """
    result = []
    # ヘッダー行をスキップ（index 0）
    for row in data[1:]:
        if not isinstance(row, list):
            continue
        if len(row) <= IDX_KAIHA_SHORT_NAME:
            continue
        name = str(row[IDX_KAIHA_NAME]).strip() if row[IDX_KAIHA_NAME] else ""
        short_name = (
            str(row[IDX_KAIHA_SHORT_NAME]).strip() if row[IDX_KAIHA_SHORT_NAME] else ""
        )
        if name:
            result.append({"name": name, "short_name": short_name})
    return result


# =============================================================================
# 3. 参議院議員（giin.json）: 会派略称のユニーク一覧を抽出
# =============================================================================


def extract_giin_kaiha(data: list[Any]) -> list[str]:
    """giin.jsonから議員の会派略称のユニーク一覧を抽出する.

    Returns:
        ユニークな会派略称のソート済みリスト
    """
    kaiha_set: set[str] = set()
    # ヘッダー行をスキップ（index 0）
    for row in data[1:]:
        if not isinstance(row, list) or len(row) <= IDX_GIIN_PARTY:
            continue
        party = row[IDX_GIIN_PARTY]
        if party and isinstance(party, str):
            name = party.strip()
            if name:
                kaiha_set.add(name)
    return sorted(kaiha_set)


# =============================================================================
# 4. 既存seedデータの解析
# =============================================================================


def parse_seed_parliamentary_groups(seed_path: Path) -> list[dict[str, Any]]:
    """seed_parliamentary_groups_generated.sqlから既存の会派データを解析する.

    Returns:
        [{"name": str, "governing_body": str, "is_active": bool}, ...]
    """
    result = []
    content = seed_path.read_text(encoding="utf-8")

    # VALUES句の各行をパース
    # ('会派名', (SELECT ...), URL|NULL, desc|NULL, bool, 'chamber')
    pattern = re.compile(
        r"\('([^']*)',\s*"  # name
        r"\(SELECT id FROM governing_bodies "
        r"WHERE name = '([^']*)'"  # governing_body
        r"[^)]*\),\s*"  # 条件の残り
        r"(?:'[^']*'|NULL),\s*"  # url
        r"(?:'[^']*'|NULL),\s*"  # description
        r"(true|false),\s*"  # is_active
        r"'[^']*'"  # chamber
    )

    for match in pattern.finditer(content):
        name = match.group(1)
        governing_body = match.group(2)
        is_active = match.group(3) == "true"

        result.append(
            {
                "name": name,
                "governing_body": governing_body,
                "is_active": is_active,
            }
        )

    return result


def parse_seed_political_parties(seed_path: Path) -> list[str]:
    """seed_political_parties_generated.sqlから政党名一覧を抽出する.

    Returns:
        政党名のリスト
    """

    content = seed_path.read_text(encoding="utf-8")
    # INSERT INTO ... VALUES の各行から政党名を取得
    # パターン: ('政党名', URL|NULL)
    pattern = re.compile(r"\('([^']*)',\s*(?:'[^']*'|NULL)\)")
    return [m.group(1) for m in pattern.finditer(content)]


# =============================================================================
# 5. マッピング提案ロジック
# =============================================================================

# 会派名に含まれる政党名のマッピング（優先順位順）
# 長い名前を先にマッチさせるため降順ソート
KNOWN_PARTY_MAPPINGS: dict[str, str] = {
    "立憲民主党": "立憲民主党",
    "自由民主党": "自由民主党",
    "国民民主党": "国民民主党",
    "日本維新の会": "日本維新の会",
    "日本共産党": "日本共産党",
    "社会民主党": "社会民主党",
    "れいわ新選組": "れいわ新選組",
    "公明党": "公明党",
    "参政党": "参政党",
    "日本保守党": "日本保守党",
    "みんなの党": "みんなの党",
    "希望の党": "希望の党",
    "民主党": "民主党",
    "民進党": "民主党",  # 民進党は民主党の後継
    "維新の党": "日本維新の会",
    "おおさか維新の会": "日本維新の会",
    "新進党": "新進党",
    "自由党": "自由党",
    "保守党": "保守党",
    "保守新党": "保守新党",
    "国民新党": "国民新党",
    "新党さきがけ": "新党さきがけ",
    "さきがけ": "新党さきがけ",
    "新党きづな": "新党きづな",
    "太陽党": "太陽党",
    "次世代の党": "次世代の党",
    "たちあがれ日本": "たちあがれ日本",
    "結いの党": "結いの党",
    "生活の党": "生活の党",
    "減税日本": "減税日本",
    "無所属": "無所属",
    "社民": "社会民主党",
}


def propose_party_mapping(
    kaiha_name: str,
    existing_mappings: dict[str, str | None],
    known_parties: list[str],
) -> dict[str, Any]:
    """会派名から政党マッピングを提案する.

    Args:
        kaiha_name: 会派名
        existing_mappings: 既存seedの {会派名: 政党名|None} マッピング
        known_parties: seed_political_parties の政党名リスト

    Returns:
        {"kaiha_name": str, "proposed_party": str|None,
         "confidence": str, "is_coalition": bool, "note": str}
    """
    # 既存seedで既にマッピング済みの場合はそのまま使用
    if kaiha_name in existing_mappings and existing_mappings[kaiha_name] is not None:
        return {
            "kaiha_name": kaiha_name,
            "proposed_party": existing_mappings[kaiha_name],
            "confidence": "existing",
            "is_coalition": False,
            "note": "既存seedのマッピングを使用",
        }

    # 完全一致チェック
    if kaiha_name in known_parties:
        return {
            "kaiha_name": kaiha_name,
            "proposed_party": kaiha_name,
            "confidence": "high",
            "is_coalition": False,
            "note": "政党名と完全一致",
        }

    # 名前ベースの推定（長い名前から順にマッチ）
    # 長いキーワードがマッチした箇所を記録し、短いキーワードの偽マッチを防ぐ
    matched_parties = []
    matched_spans: list[tuple[int, int]] = []
    for party_keyword in sorted(KNOWN_PARTY_MAPPINGS.keys(), key=len, reverse=True):
        start = kaiha_name.find(party_keyword)
        if start == -1:
            continue
        end = start + len(party_keyword)
        # 既にマッチ済みの範囲と重複しないか確認
        if any(ms <= start < me or ms < end <= me for ms, me in matched_spans):
            continue
        matched_spans.append((start, end))
        matched_parties.append(KNOWN_PARTY_MAPPINGS[party_keyword])

    # 重複除去して順序保持
    seen: set[str] = set()
    unique_matched = []
    for p in matched_parties:
        if p not in seen:
            seen.add(p)
            unique_matched.append(p)

    if len(unique_matched) == 0:
        return {
            "kaiha_name": kaiha_name,
            "proposed_party": None,
            "confidence": "unmapped",
            "is_coalition": False,
            "note": "マッピング候補なし",
        }
    elif len(unique_matched) == 1:
        return {
            "kaiha_name": kaiha_name,
            "proposed_party": unique_matched[0],
            "confidence": "high",
            "is_coalition": False,
            "note": f"名前ベース推定: '{unique_matched[0]}'を含む",
        }
    else:
        # 連立会派: 最初にマッチした主要政党を採用
        return {
            "kaiha_name": kaiha_name,
            "proposed_party": unique_matched[0],
            "confidence": "medium",
            "is_coalition": True,
            "note": (
                f"連立会派: {', '.join(unique_matched)}"
                f" → 主要政党'{unique_matched[0]}'を設定"
            ),
        }


def generate_mapping_proposals(
    all_kaiha_names: set[str],
    existing_seed_data: list[dict[str, Any]],
    known_parties: list[str],
) -> list[dict[str, Any]]:
    """全会派名に対するマッピング提案を生成する.

    Args:
        all_kaiha_names: 全データソースから集めた会派名のセット
        existing_seed_data: parse_seed_parliamentary_groups() の結果
        known_parties: seed_political_parties の政党名リスト

    Returns:
        マッピング提案のリスト
    """
    # 既存マッピングの辞書化（国会のみ）
    existing_mappings: dict[str, str | None] = {}
    for entry in existing_seed_data:
        if entry["governing_body"] == "国会":
            existing_mappings[entry["name"]] = entry["party_name"]

    proposals = []
    for name in sorted(all_kaiha_names):
        proposal = propose_party_mapping(name, existing_mappings, known_parties)
        proposals.append(proposal)

    return proposals


# =============================================================================
# 6. 出力
# =============================================================================


def write_csv(
    rows: list[dict[str, Any]], output_path: Path, fieldnames: list[str]
) -> None:
    """CSVファイルに書き出す."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("出力: %s (%d行)", output_path, len(rows))


def write_json(data: object, output_path: Path) -> None:
    """JSONファイルに書き出す."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("出力: %s", output_path)


# =============================================================================
# メイン処理
# =============================================================================


def main(
    gian_summary_path: Path | None = None,
    kaiha_path: Path | None = None,
    giin_path: Path | None = None,
) -> None:
    """メイン処理: データ取得→分析→出力."""
    auto_fetched: list[Path] = []

    try:
        # --- データ取得 ---
        if gian_summary_path is None:
            gian_summary_path = download_file(GIAN_SUMMARY_URL)
            auto_fetched.append(gian_summary_path)
        if kaiha_path is None:
            kaiha_path = download_file(KAIHA_URL)
            auto_fetched.append(kaiha_path)
        if giin_path is None:
            giin_path = download_file(GIIN_URL)
            auto_fetched.append(giin_path)

        # --- 1. 衆議院: gian_summary.json ---
        logger.info("=== 衆議院（gian_summary.json）分析 ===")
        gian_data = load_json(gian_summary_path)
        session_kaiha = extract_shuugiin_kaiha(gian_data)
        shuugiin_rows = aggregate_shuugiin_kaiha(session_kaiha)
        kaiha_ranges = get_all_shuugiin_kaiha_with_range(session_kaiha)
        logger.info(
            "衆議院: %d回次、%dユニーク会派名",
            len(session_kaiha),
            len(kaiha_ranges),
        )

        # --- 2. 参議院会派: kaiha.json ---
        logger.info("=== 参議院会派（kaiha.json）分析 ===")
        kaiha_data = load_json(kaiha_path)
        sangiin_kaiha = extract_sangiin_kaiha(kaiha_data)
        logger.info("参議院（kaiha.json）: %d会派", len(sangiin_kaiha))

        # --- 3. 参議院議員: giin.json ---
        logger.info("=== 参議院議員（giin.json）分析 ===")
        giin_data = load_json(giin_path)
        giin_kaiha = extract_giin_kaiha(giin_data)
        logger.info("参議院（giin.json）: %d会派略称", len(giin_kaiha))

        # --- 4. 既存seedデータ ---
        logger.info("=== 既存seedデータ分析 ===")
        seed_pg_path = Path("database/seed_parliamentary_groups_generated.sql")
        seed_pp_path = Path("database/seed_political_parties_generated.sql")

        existing_seed: list[dict[str, Any]] = []
        known_parties: list[str] = []
        if seed_pg_path.exists():
            existing_seed = parse_seed_parliamentary_groups(seed_pg_path)
            national_seed = [s for s in existing_seed if s["governing_body"] == "国会"]
            mapped = sum(1 for s in national_seed if s["has_party_id"])
            logger.info(
                "既存seed（国会）: %d件（マッピング済: %d, NULL: %d）",
                len(national_seed),
                mapped,
                len(national_seed) - mapped,
            )
        else:
            logger.warning("seedファイルが見つかりません: %s", seed_pg_path)

        if seed_pp_path.exists():
            known_parties = parse_seed_political_parties(seed_pp_path)
            logger.info("既存政党seed: %d件", len(known_parties))
        else:
            logger.warning("seedファイルが見つかりません: %s", seed_pp_path)

        # --- 5. 集計・分析 ---
        logger.info("=== マッピング分析 ===")

        # 全データソースからの会派名を統合
        all_kaiha: set[str] = set()
        all_kaiha.update(kaiha_ranges.keys())  # 衆議院
        all_kaiha.update(k["name"] for k in sangiin_kaiha)  # 参議院kaiha.json
        all_kaiha.update(giin_kaiha)  # 参議院giin.json

        logger.info("全データソースからの総ユニーク会派名: %d", len(all_kaiha))

        # 既存seedに未登録の会派を検出
        existing_names = {
            s["name"] for s in existing_seed if s["governing_body"] == "国会"
        }
        new_kaiha = all_kaiha - existing_names
        if new_kaiha:
            logger.info("seedに未登録の会派: %d件", len(new_kaiha))
            for name in sorted(new_kaiha):
                logger.info("  - %s", name)

        # マッピング提案生成
        proposals = generate_mapping_proposals(all_kaiha, existing_seed, known_parties)

        # --- 6. 出力 ---
        logger.info("=== 結果出力 ===")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # 6a. 回次別衆議院会派一覧
        write_csv(
            shuugiin_rows,
            OUTPUT_DIR / "kaiha_shuugiin_by_session.csv",
            ["session", "kaiha_name", "count"],
        )

        # 6b. 参議院現行会派一覧
        write_csv(
            sangiin_kaiha,
            OUTPUT_DIR / "kaiha_sangiin_current.csv",
            ["name", "short_name"],
        )

        # 6c. マッピング提案
        proposal_output = {
            "summary": {
                "total_kaiha": len(all_kaiha),
                "existing_mapped": sum(
                    1 for p in proposals if p["confidence"] == "existing"
                ),
                "high_confidence": sum(
                    1 for p in proposals if p["confidence"] == "high"
                ),
                "medium_confidence": sum(
                    1 for p in proposals if p["confidence"] == "medium"
                ),
                "unmapped": sum(1 for p in proposals if p["confidence"] == "unmapped"),
                "coalition_count": sum(1 for p in proposals if p["is_coalition"]),
            },
            "shuugiin_kaiha_ranges": dict(sorted(kaiha_ranges.items())),
            "sangiin_kaiha_current": sangiin_kaiha,
            "sangiin_giin_kaiha": giin_kaiha,
            "new_kaiha_not_in_seed": sorted(new_kaiha),
            "proposals": proposals,
        }
        write_json(
            proposal_output,
            OUTPUT_DIR / "kaiha_mapping_proposal.json",
        )

        # 6d. 未マッピング会派
        unmapped = [p for p in proposals if p["confidence"] == "unmapped"]
        write_csv(
            unmapped,
            OUTPUT_DIR / "kaiha_unmapped_groups.csv",
            ["kaiha_name", "proposed_party", "confidence", "is_coalition", "note"],
        )

        # --- サマリー表示 ---
        logger.info("=== 分析サマリー ===")
        if kaiha_ranges:
            min_session = min(v["min_session"] for v in kaiha_ranges.values())
            max_session = max(v["max_session"] for v in kaiha_ranges.values())
            logger.info(
                "衆議院会派数: %d（%d〜%d回次）",
                len(kaiha_ranges),
                min_session,
                max_session,
            )
        else:
            logger.info("衆議院会派数: 0")
        logger.info("参議院会派数（kaiha.json）: %d", len(sangiin_kaiha))
        logger.info("参議院会派数（giin.json）: %d", len(giin_kaiha))
        logger.info("全ユニーク会派名: %d", len(all_kaiha))
        logger.info("seedに未登録: %d", len(new_kaiha))
        logger.info(
            "マッピング: existing=%d, high=%d, medium=%d, unmapped=%d",
            proposal_output["summary"]["existing_mapped"],
            proposal_output["summary"]["high_confidence"],
            proposal_output["summary"]["medium_confidence"],
            proposal_output["summary"]["unmapped"],
        )
        logger.info("連立会派: %d", proposal_output["summary"]["coalition_count"])
        logger.info("完了: tmp/ 配下に結果ファイルを出力しました")

    finally:
        # 自動取得した一時ファイルをクリーンアップ
        for tmp_path in auto_fetched:
            tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="衆参の時代別 会派⇔政党マッピング調査",
    )
    parser.add_argument(
        "--gian-summary",
        type=Path,
        default=None,
        help="gian_summary.jsonのパス（省略時はGitHubから自動取得）",
    )
    parser.add_argument(
        "--kaiha",
        type=Path,
        default=None,
        help="kaiha.jsonのパス（省略時はGitHubから自動取得）",
    )
    parser.add_argument(
        "--giin",
        type=Path,
        default=None,
        help="giin.jsonのパス（省略時はGitHubから自動取得）",
    )
    args = parser.parse_args()

    for arg_name, arg_val in [
        ("--gian-summary", args.gian_summary),
        ("--kaiha", args.kaiha),
        ("--giin", args.giin),
    ]:
        if arg_val is not None and not arg_val.exists():
            logger.error("ファイルが見つかりません (%s): %s", arg_name, arg_val)
            sys.exit(1)

    main(args.gian_summary, args.kaiha, args.giin)
