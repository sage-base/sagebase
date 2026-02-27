"""Pass 1 Speaker Matching パイプライン.

ベースライン計測 + 分類 + ルールベースマッチング。

Speaker紐付け率を0%から推定30-50%に改善するためのパイプラインスクリプト。
以下のステップを実行する:
1. ベースライン計測（現状のSpeaker統計）
2. is_politicianフラグ分類（非政治家パターンに基づく）
3. ルールベースマッチング（MatchSpeakersUseCase use_llm=False）
4. 結果レポート出力

Usage (Docker経由で実行):
    # ベースライン計測のみ
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/run_pass1_speaker_matching.py --mode baseline

    # is_politicianフラグ分類のみ
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/run_pass1_speaker_matching.py --mode classify

    # ルールベースマッチング実行のみ
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/run_pass1_speaker_matching.py --mode match

    # 結果レポート出力のみ
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/run_pass1_speaker_matching.py --mode report

    # 全工程実行（baseline → classify → match → report）
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/run_pass1_speaker_matching.py --mode full

前提条件:
    - Docker環境が起動済み（just up-detached）
    - Alembicマイグレーション適用済み
    - Speaker / Politician データがインポート済み
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://sagebase_user:sagebase_password@postgres:5432/sagebase_db",
)

RESULT_JSON_PATH = Path("tmp/pass1_matching_result.json")


# --- データクラス ---


@dataclass
class SpeakerStats:
    """Speaker統計."""

    total_speakers: int
    politician_speakers: int
    non_politician_speakers: int
    linked_speakers: int
    linked_politician_speakers: int
    match_rate: float
    measured_at: str


@dataclass
class ClassifyResult:
    """分類結果."""

    total_updated_to_politician: int
    total_kept_non_politician: int


@dataclass
class MatchResult:
    """マッチング結果."""

    total_processed: int
    matched: int
    match_rate: float


@dataclass
class PipelineResult:
    """パイプライン全体の結果."""

    before: SpeakerStats | None = None
    classify: ClassifyResult | None = None
    after_classify: SpeakerStats | None = None
    match: MatchResult | None = None
    after_match: SpeakerStats | None = None


# --- 計測関数 ---


async def measure_speaker_stats(session: AsyncSession) -> SpeakerStats:
    """Speaker統計を計測する."""
    query = text("""
        WITH stats AS (
            SELECT
                COUNT(*) as total_speakers,
                COUNT(CASE WHEN is_politician = TRUE THEN 1 END)
                    as politician_speakers,
                COUNT(CASE WHEN is_politician = FALSE THEN 1 END)
                    as non_politician_speakers
            FROM speakers
        ),
        linked_stats AS (
            SELECT
                COUNT(DISTINCT s.id) as linked_speakers,
                COUNT(
                    DISTINCT CASE WHEN s.is_politician = TRUE THEN s.id END
                ) as linked_politician_speakers
            FROM speakers s
            INNER JOIN politicians p ON s.politician_id = p.id
        )
        SELECT
            stats.total_speakers,
            stats.politician_speakers,
            stats.non_politician_speakers,
            linked_stats.linked_speakers,
            linked_stats.linked_politician_speakers,
            CASE
                WHEN stats.politician_speakers > 0
                THEN ROUND(
                    CAST(
                        linked_stats.linked_politician_speakers AS NUMERIC
                    ) * 100.0 / stats.politician_speakers, 1
                )
                ELSE 0
            END as match_rate
        FROM stats, linked_stats
    """)
    result = await session.execute(query)
    row = result.fetchone()

    if not row:
        return SpeakerStats(
            total_speakers=0,
            politician_speakers=0,
            non_politician_speakers=0,
            linked_speakers=0,
            linked_politician_speakers=0,
            match_rate=0.0,
            measured_at=datetime.now(UTC).isoformat(),
        )

    return SpeakerStats(
        total_speakers=row.total_speakers,
        politician_speakers=row.politician_speakers,
        non_politician_speakers=row.non_politician_speakers,
        linked_speakers=row.linked_speakers,
        linked_politician_speakers=row.linked_politician_speakers,
        match_rate=float(row.match_rate),
        measured_at=datetime.now(UTC).isoformat(),
    )


async def get_non_politician_breakdown(session: AsyncSession) -> list[tuple[str, int]]:
    """非政治家パターン別の件数内訳を取得する."""
    from src.domain.services.speaker_classifier import NON_POLITICIAN_EXACT_NAMES

    names_list = list(NON_POLITICIAN_EXACT_NAMES)
    query = text("""
        SELECT name, COUNT(*) as cnt
        FROM speakers
        WHERE name = ANY(:names)
          AND politician_id IS NULL
        GROUP BY name
        ORDER BY cnt DESC
    """)
    result = await session.execute(query, {"names": names_list})
    return [(row.name, row.cnt) for row in result.fetchall()]


async def get_unmatched_speakers_top(
    session: AsyncSession, limit: int = 20
) -> list[tuple[str, str | None, int]]:
    """未マッチSpeaker上位を取得する."""
    query = text("""
        SELECT s.name, s.political_party_name, COUNT(c.id) as conv_count
        FROM speakers s
        LEFT JOIN conversations c ON c.speaker_id = s.id
        WHERE s.is_politician = TRUE
          AND s.politician_id IS NULL
        GROUP BY s.name, s.political_party_name
        ORDER BY conv_count DESC
        LIMIT :limit
    """)
    result = await session.execute(query, {"limit": limit})
    return [
        (row.name, row.political_party_name, row.conv_count)
        for row in result.fetchall()
    ]


# --- 実行関数 ---


async def run_baseline(session: AsyncSession) -> SpeakerStats:
    """ベースライン計測を実行する."""
    stats = await measure_speaker_stats(session)
    print_stats("ベースライン計測結果", stats)
    return stats


async def run_classify() -> ClassifyResult:
    """is_politicianフラグ分類を実行する（ClassifySpeakersPoliticianUseCase経由）."""
    from src.infrastructure.di.container import init_container

    logger.info("is_politicianフラグ分類を開始...")

    container = init_container()
    usecase = container.use_cases.classify_speakers_politician_usecase()
    result = await usecase.execute()

    classify_result = ClassifyResult(
        total_updated_to_politician=result["total_updated_to_politician"],
        total_kept_non_politician=result["total_kept_non_politician"],
    )

    logger.info(
        "分類完了: 政治家に設定=%d件, 非政治家に設定=%d件",
        result["total_updated_to_politician"],
        result["total_kept_non_politician"],
    )
    return classify_result


async def run_match() -> MatchResult:
    """ルールベースマッチングを実行する（MatchSpeakersUseCase経由）."""
    from src.infrastructure.di.container import init_container

    logger.info("ルールベースマッチングを開始（use_llm=False）...")

    container = init_container()
    match_speakers_usecase = container.use_cases.match_speakers_usecase()

    results = await match_speakers_usecase.execute(use_llm=False)

    matched = sum(1 for r in results if r.matched_politician_id is not None)
    total = len(results)
    rate = (matched / total * 100) if total > 0 else 0.0

    match_result = MatchResult(
        total_processed=total,
        matched=matched,
        match_rate=round(rate, 1),
    )

    logger.info(
        "マッチング完了: 処理=%d件, マッチ=%d件 (%.1f%%)",
        total,
        matched,
        rate,
    )
    return match_result


async def run_report(session: AsyncSession, pipeline: PipelineResult) -> None:
    """結果レポートを出力する."""
    print("\n" + "=" * 60)
    print("Pass 1 Speaker Matching レポート")
    print("=" * 60)

    # Before/After比較
    if pipeline.before:
        print_stats("実行前", pipeline.before)

    if pipeline.classify:
        print("\n--- 分類結果 ---")
        print(f"  政治家に設定: {pipeline.classify.total_updated_to_politician}件")
        print(f"  非政治家に設定: {pipeline.classify.total_kept_non_politician}件")

    if pipeline.after_classify:
        print_stats("分類後", pipeline.after_classify)

    if pipeline.match:
        print("\n--- マッチング結果 ---")
        print(f"  処理対象: {pipeline.match.total_processed}件")
        print(f"  マッチ成功: {pipeline.match.matched}件")
        print(f"  マッチ率: {pipeline.match.match_rate}%")

    if pipeline.after_match:
        print_stats("マッチング後", pipeline.after_match)

    # 非政治家パターン別内訳
    breakdown = await get_non_politician_breakdown(session)
    if breakdown:
        print("\n--- 非政治家パターン別件数 ---")
        for name, cnt in breakdown:
            print(f"  {name}: {cnt}件")

    # 未マッチSpeaker上位
    unmatched = await get_unmatched_speakers_top(session)
    if unmatched:
        print("\n--- 未マッチSpeaker上位（発言数順）---")
        for name, party, conv_count in unmatched:
            party_str = f" ({party})" if party else ""
            print(f"  {name}{party_str}: {conv_count}発言")

    # JSON保存
    save_result_json(pipeline)

    print("\n" + "=" * 60)


def print_stats(label: str, stats: SpeakerStats) -> None:
    """Speaker統計を表示する."""
    print(f"\n--- {label} ---")
    print(f"  全Speaker数: {stats.total_speakers}")
    print(f"  政治家Speaker: {stats.politician_speakers}")
    print(f"  非政治家Speaker: {stats.non_politician_speakers}")
    print(f"  リンク済み: {stats.linked_speakers}")
    print(f"  リンク済み政治家: {stats.linked_politician_speakers}")
    print(f"  マッチ率: {stats.match_rate}%")


def save_result_json(pipeline: PipelineResult) -> None:
    """結果をJSONで保存する."""
    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {}
    if pipeline.before:
        data["before"] = asdict(pipeline.before)
    if pipeline.classify:
        data["classify"] = asdict(pipeline.classify)
    if pipeline.after_classify:
        data["after_classify"] = asdict(pipeline.after_classify)
    if pipeline.match:
        data["match"] = asdict(pipeline.match)
    if pipeline.after_match:
        data["after_match"] = asdict(pipeline.after_match)

    RESULT_JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    logger.info("結果をJSON保存: %s", RESULT_JSON_PATH)


# --- メイン関数 ---


async def main() -> None:
    """メイン実行関数."""
    parser = argparse.ArgumentParser(
        description=(
            "Pass 1 Speaker Matching: ベースライン計測 + 分類 + ルールベースマッチング"
        ),
        epilog=(
            "例: docker compose -f docker/docker-compose.yml exec sagebase "
            "uv run python scripts/run_pass1_speaker_matching.py --mode full"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["baseline", "classify", "match", "report", "full"],
        default="full",
        help="実行モード: baseline=計測のみ, classify=分類のみ, match=マッチのみ, "
        "report=レポートのみ, full=全工程実行",
    )
    args = parser.parse_args()

    db_url = DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url)
    pipeline = PipelineResult()

    try:
        if args.mode == "baseline":
            async with engine.connect() as conn:
                async with conn.begin():
                    session = AsyncSession(bind=conn)
                    await run_baseline(session)

        elif args.mode == "classify":
            # 分類（DIコンテナ経由）
            pipeline.classify = await run_classify()
            async with engine.connect() as conn:
                async with conn.begin():
                    session = AsyncSession(bind=conn)
                    pipeline.after_classify = await measure_speaker_stats(session)
                    print_stats("分類後", pipeline.after_classify)

        elif args.mode == "match":
            async with engine.connect() as conn:
                async with conn.begin():
                    session = AsyncSession(bind=conn)
                    pipeline.before = await measure_speaker_stats(session)
            # マッチングはDIコンテナ経由（独自セッション管理）
            pipeline.match = await run_match()
            async with engine.connect() as conn:
                async with conn.begin():
                    session = AsyncSession(bind=conn)
                    pipeline.after_match = await measure_speaker_stats(session)
                    print_stats("マッチング後", pipeline.after_match)

        elif args.mode == "report":
            async with engine.connect() as conn:
                async with conn.begin():
                    session = AsyncSession(bind=conn)
                    pipeline.after_match = await measure_speaker_stats(session)
                    await run_report(session, pipeline)

        elif args.mode == "full":
            # Step 1: ベースライン計測
            async with engine.connect() as conn:
                async with conn.begin():
                    session = AsyncSession(bind=conn)
                    pipeline.before = await run_baseline(session)

            # Step 2: 分類（DIコンテナ経由）
            pipeline.classify = await run_classify()
            async with engine.connect() as conn:
                async with conn.begin():
                    session = AsyncSession(bind=conn)
                    pipeline.after_classify = await measure_speaker_stats(session)

            # Step 3: マッチング（DIコンテナ経由）
            pipeline.match = await run_match()

            # Step 4: レポート
            async with engine.connect() as conn:
                async with conn.begin():
                    session = AsyncSession(bind=conn)
                    pipeline.after_match = await measure_speaker_stats(session)
                    await run_report(session, pipeline)

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
