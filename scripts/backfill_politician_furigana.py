"""Politicianのfuriganaバックフィルスクリプト.

マッチ済みSpeakerのname_yomi（国会API由来）を、
紐付け先Politicianのfuriganaカラムにバックフィルする。

Usage (Docker経由で実行):
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/backfill_politician_furigana.py

    # ドライラン（DB書き込みなし）
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/backfill_politician_furigana.py --dry-run

前提条件:
    - Docker環境が起動済み（just up-detached）
    - speakersテーブルにpolitician_idとname_yomiが設定済みのレコードが存在
"""

import argparse
import asyncio
import logging
import sys

from collections import Counter
from pathlib import Path
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from src.domain.services.name_normalizer import NameNormalizer
from src.infrastructure.config.async_database import get_async_session


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def fetch_speaker_yomi_data(session) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
    """マッチ済みSpeakerのname_yomiデータを取得する."""
    query = text("""
        SELECT s.politician_id, s.name_yomi
        FROM speakers s
        WHERE s.politician_id IS NOT NULL
          AND s.name_yomi IS NOT NULL
          AND s.name_yomi != ''
    """)
    result = await session.execute(query)
    return [
        {"politician_id": row.politician_id, "name_yomi": row.name_yomi}
        for row in result.fetchall()
    ]


async def fetch_politicians_without_furigana(session) -> set[int]:  # type: ignore[no-untyped-def]
    """furiganaが未設定のPolitician IDを取得する."""
    query = text("""
        SELECT id FROM politicians
        WHERE furigana IS NULL OR furigana = ''
    """)
    result = await session.execute(query)
    return {row.id for row in result.fetchall()}


async def update_furigana_bulk(session, updates: list[tuple[int, str]]) -> int:  # type: ignore[no-untyped-def]
    """Politicianのfuriganaを一括更新する."""
    query = text("""
        UPDATE politicians SET furigana = :furigana, updated_at = CURRENT_TIMESTAMP
        WHERE id = :id AND (furigana IS NULL OR furigana = '')
    """)
    updated = 0
    for politician_id, furigana in updates:
        result = await session.execute(
            query, {"id": politician_id, "furigana": furigana}
        )
        updated += result.rowcount
    return updated


def aggregate_yomi_by_politician(
    speaker_data: list[dict[str, Any]], target_ids: set[int]
) -> dict[int, str]:
    """Politician毎にname_yomiを集約する（最頻値を採用）."""
    yomi_counter: dict[int, Counter[str]] = {}

    for row in speaker_data:
        pid = row["politician_id"]
        if pid not in target_ids:
            continue
        normalized = NameNormalizer.normalize_kana(row["name_yomi"])
        if not normalized:
            continue
        if pid not in yomi_counter:
            yomi_counter[pid] = Counter()
        yomi_counter[pid][normalized] += 1

    # 各Politicianの最頻値を採用
    return {pid: counter.most_common(1)[0][0] for pid, counter in yomi_counter.items()}


async def run_backfill(dry_run: bool) -> None:
    """furiganaバックフィルを実行する."""
    async with get_async_session() as session:
        # 1. データ取得
        speaker_data = await fetch_speaker_yomi_data(session)
        logger.info("マッチ済みSpeaker（name_yomiあり）: %d件", len(speaker_data))

        target_ids = await fetch_politicians_without_furigana(session)
        logger.info("furigana未設定Politician: %d件", len(target_ids))

        if not target_ids:
            logger.info("バックフィル対象なし")
            return

        # 2. 集約
        yomi_map = aggregate_yomi_by_politician(speaker_data, target_ids)
        logger.info("バックフィル対象（Speakerからyomi取得可能）: %d件", len(yomi_map))

        if not yomi_map:
            logger.info("バックフィル可能なデータなし")
            return

        # 3. プレビュー
        for pid, furigana in sorted(yomi_map.items())[:10]:
            logger.info("  politician_id=%d → furigana='%s'", pid, furigana)
        if len(yomi_map) > 10:
            logger.info("  ... 他 %d件", len(yomi_map) - 10)

        # 4. 更新
        if dry_run:
            logger.info("[DRY RUN] %d件のfuriganaを更新予定", len(yomi_map))
        else:
            updates = list(yomi_map.items())
            updated = await update_furigana_bulk(session, updates)
            await session.commit()
            logger.info("furiganaを%d件更新完了", updated)


def main() -> None:
    """メイン処理."""
    parser = argparse.ArgumentParser(
        description="マッチ済みSpeakerのname_yomiからPoliticianのfuriganaをバックフィルする"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="DB書き込みなしでプレビューのみ表示",
    )
    args = parser.parse_args()
    asyncio.run(run_backfill(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
