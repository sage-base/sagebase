"""カバレッジページのデータをBQから取得して更新するスクリプト.

BQの sagebase_source データセットからカバレッジ指標を集計し、
website/data/coverage.json に書き出す。
Hugo テンプレート (coverage.html) がこの JSON を参照してページを生成する。

Usage (Docker経由で実行):
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/update_coverage_data.py

    # ドライラン（JSONを標準出力に表示、ファイル書き込みなし）
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/update_coverage_data.py --dry-run

前提条件:
    - GCP認証済み（gcloud auth application-default login）
    - GOOGLE_CLOUD_PROJECT 環境変数が設定されている
    - BigQuery の sagebase_source データセットにデータが存在する
"""

import argparse
import asyncio
import json
import logging
import os
import sys

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.domain.entities.bq_coverage_stats import BQCoverageSummary
from src.infrastructure.bigquery.bq_data_coverage_repository_impl import (
    BQDataCoverageRepositoryImpl,
)


logger = logging.getLogger(__name__)

# website/data/coverage.json のパス
WEBSITE_DATA_DIR = Path(__file__).resolve().parent.parent / "website" / "data"
COVERAGE_JSON_PATH = WEBSITE_DATA_DIR / "coverage.json"


def _format_number_jp(n: int) -> str:
    """数値を日本語表記用にフォーマット.

    例: 10800000 → "1,080万+"、6400 → "6,400"
    """
    if n >= 10_000_000:
        man = n // 10_000
        return f"{man:,}万+"
    if n >= 10_000:
        man = round(n / 10_000, 1)
        # 小数点以下が0なら整数表示
        if man == int(man):
            return f"{int(man):,}万+"
        return f"{man:,}万+"
    return f"{n:,}"


def _extract_year(date_str: str | None) -> int | None:
    """日付文字列から年を抽出."""
    if not date_str:
        return None
    try:
        return int(date_str[:4])
    except (ValueError, IndexError):
        return None


def _calculate_year_span(earliest: str | None, latest: str | None) -> str | None:
    """年数の表示文字列を生成（例: '79年分'）."""
    e = _extract_year(earliest)
    l = _extract_year(latest)  # noqa: E741
    if e and l:
        return f"{l - e + 1}"
    return None


def _count_covered_prefectures(
    prefecture_stats: list[dict[str, Any]],
) -> int:
    """データが存在する都道府県数をカウント."""
    return sum(1 for p in prefecture_stats if p.get("conversation_count", 0) > 0)


def _count_covered_municipalities(
    prefecture_stats: list[dict[str, Any]],
) -> int:
    """市区町村レベルの議会体数を合計（governing_body_count）."""
    return sum(p.get("governing_body_count", 0) for p in prefecture_stats)


def _build_prefecture_entry(
    p: dict[str, Any],
    timeline_start: int,
    timeline_end: int,
) -> dict[str, Any]:
    """都道府県データにタイムライン表示用の計算値を追加."""
    e_year = _extract_year(p.get("earliest_date"))
    l_year = _extract_year(p.get("latest_date"))
    timeline_span = timeline_end - timeline_start

    # タイムライン上の位置と幅を%で計算
    timeline_left: int | None = None
    timeline_width: int | None = None
    timeline_intensity = "intensity-low"
    if e_year and l_year and timeline_span > 0:
        timeline_left = round((e_year - timeline_start) / timeline_span * 100)
        timeline_width = round((l_year - e_year + 1) / timeline_span * 100)
        span = l_year - e_year
        if span > 50:
            timeline_intensity = "intensity-high"
        elif span > 25:
            timeline_intensity = "intensity-mid"

    return {
        "name": p["prefecture"],
        "conversation_count": p["conversation_count"],
        "meeting_count": p["meeting_count"],
        "politician_count": p["politician_count"],
        "speaker_count": p["speaker_count"],
        "matched_speaker_count": p["matched_speaker_count"],
        "linkage_rate": p["linkage_rate"],
        "proposal_count": p["proposal_count"],
        "governing_body_count": p["governing_body_count"],
        "earliest_date": p.get("earliest_date"),
        "latest_date": p.get("latest_date"),
        "earliest_year": e_year,
        "latest_year": l_year,
        "timeline_left": timeline_left,
        "timeline_width": timeline_width,
        "timeline_intensity": timeline_intensity,
    }


def build_coverage_json(summary: BQCoverageSummary) -> dict[str, Any]:
    """BQCoverageSummaryからHugo用JSONデータを構築."""
    now_str = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_date = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    national = summary["national"]
    local = summary["local_total"]
    politician = summary["politician_stats"]
    proposal = summary["proposal_stats"]
    speaker = summary["speaker_linkage"]
    pg_mapping = summary["parliamentary_group_mapping"]
    party_group = summary["party_group_counts"]
    national_period = summary["national_period"]
    prefecture_stats = summary["prefecture_stats"]

    # 年数計算
    national_year_span = _calculate_year_span(
        national_period["earliest_date"], national_period["latest_date"]
    )
    national_earliest_year = _extract_year(national_period["earliest_date"])
    national_latest_year = _extract_year(national_period["latest_date"])

    # カバー済み都道府県数
    covered_prefectures = _count_covered_prefectures(prefecture_stats)

    # カバー済み市区町村数（概算: governing_body_count合計）
    covered_municipalities = _count_covered_municipalities(prefecture_stats)

    # 合計値
    total_conversations = national["conversation_count"] + local["conversation_count"]
    total_meetings = national["meeting_count"] + local["meeting_count"]
    total_politicians = (
        politician["national_politician_count"] + politician["local_politician_count"]
    )

    # タイムライン用定数
    timeline_start = 1947
    timeline_end = national_latest_year or 2026

    # 都道府県別データ（ランキング用: 発言数降順）
    prefecture_ranking = sorted(
        [
            _build_prefecture_entry(p, timeline_start, timeline_end)
            for p in prefecture_stats
            if p["conversation_count"] > 0
        ],
        key=lambda x: x["conversation_count"],
        reverse=True,
    )

    return {
        "updated_at": now_str,
        "updated_date": now_date,
        "hero": {
            "national": {
                "conversation_count": national["conversation_count"],
                "conversation_count_display": _format_number_jp(
                    national["conversation_count"]
                ),
                "meeting_count": national["meeting_count"],
                "meeting_count_display": _format_number_jp(national["meeting_count"]),
                "politician_count": politician["national_politician_count"],
                "politician_count_display": _format_number_jp(
                    politician["national_politician_count"]
                ),
                "year_span": national_year_span,
                "earliest_year": national_earliest_year,
                "latest_year": national_latest_year,
                "proposal_count": proposal["national_proposal_count"],
                "proposal_count_display": _format_number_jp(
                    proposal["national_proposal_count"]
                ),
            },
            "local": {
                "conversation_count": local["conversation_count"],
                "conversation_count_display": _format_number_jp(
                    local["conversation_count"]
                ),
                "meeting_count": local["meeting_count"],
                "meeting_count_display": _format_number_jp(local["meeting_count"]),
                "politician_count": politician["local_politician_count"],
                "politician_count_display": _format_number_jp(
                    politician["local_politician_count"]
                ),
                "covered_prefectures": covered_prefectures,
                "total_prefectures": 47,
                "covered_municipalities": covered_municipalities,
            },
        },
        "totals": {
            "conversation_count": total_conversations,
            "conversation_count_display": _format_number_jp(total_conversations),
            "meeting_count": total_meetings,
            "meeting_count_display": _format_number_jp(total_meetings),
            "politician_count": total_politicians,
            "politician_count_display": _format_number_jp(total_politicians),
            "party_count": party_group["political_party_count"],
        },
        "quality": {
            "speaker_linkage": {
                "rate": speaker["linkage_rate"],
                "total_speakers": speaker["total_speakers"],
                "matched_speakers": speaker["matched_speakers"],
                "government_official_count": speaker["government_official_count"],
            },
            "parliamentary_group_mapping": {
                "rate": pg_mapping["mapping_rate"],
                "total_groups": pg_mapping["total_parliamentary_groups"],
                "mapped_groups": pg_mapping["mapped_parliamentary_groups"],
            },
        },
        "prefecture_ranking": prefecture_ranking,
    }


async def fetch_and_save(
    project_id: str,
    dataset_id: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """BQからデータを取得してJSONファイルに保存."""
    logger.info("BQからカバレッジデータを取得中...")
    repo = BQDataCoverageRepositoryImpl(
        project_id=project_id,
        dataset_id=dataset_id,
    )

    summary = await repo.get_coverage_summary()
    coverage_data = build_coverage_json(summary)

    if dry_run:
        print(json.dumps(coverage_data, ensure_ascii=False, indent=2))
        logger.info("ドライラン: ファイル書き込みをスキップしました")
    else:
        WEBSITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        COVERAGE_JSON_PATH.write_text(
            json.dumps(coverage_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        logger.info(f"カバレッジデータを保存しました: {COVERAGE_JSON_PATH}")

    return coverage_data


def main() -> None:
    """エントリーポイント."""
    parser = argparse.ArgumentParser(
        description=(
            "BQからカバレッジデータを取得し website/data/coverage.json を更新する"
        ),
        epilog=(
            "例: docker compose -f docker/docker-compose.yml exec sagebase "
            "uv run python scripts/update_coverage_data.py"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="JSONを標準出力に表示するのみ（ファイル書き込みなし）",
    )
    parser.add_argument(
        "--dataset",
        default="sagebase_source",
        help="BigQueryデータセット名（デフォルト: sagebase_source）",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        logger.error("GOOGLE_CLOUD_PROJECT 環境変数が設定されていません")
        sys.exit(1)

    data = asyncio.run(
        fetch_and_save(
            project_id=project_id,
            dataset_id=args.dataset,
            dry_run=args.dry_run,
        )
    )

    # サマリー表示
    hero = data["hero"]
    quality = data["quality"]
    print("\n=== カバレッジデータ更新完了 ===")
    print(f"国会発言数: {hero['national']['conversation_count_display']}")
    print(f"地方発言数: {hero['local']['conversation_count_display']}")
    print(f"紐付け率: {quality['speaker_linkage']['rate']}%")
    print(f"会派マッピング率: {quality['parliamentary_group_mapping']['rate']}%")
    print(f"都道府県カバー数: {hero['local']['covered_prefectures']} / 47")
    print(f"更新日時: {data['updated_at']}")


if __name__ == "__main__":
    main()
