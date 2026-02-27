"""会派所属パイプラインのベースライン計測・結果検証スクリプト.

選挙当選者→デフォルト会派の自動割当パイプライン（link_parliamentary_groups_bulk.py）の
実行前後の状態を数値で検証し、品質を定量評価する。

Usage (Docker経由で実行):
    # ベースライン計測のみ
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/verify_parliamentary_group_pipeline.py --mode baseline

    # 結果検証のみ（保存済みベースラインがあれば差分表示）
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/verify_parliamentary_group_pipeline.py --mode verify

    # ベースライン計測 → パイプライン実行 → 結果検証
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/verify_parliamentary_group_pipeline.py --mode full

    # ドライラン（DB書き込みなし、mode=full時のみ有効）
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/verify_parliamentary_group_pipeline.py \
        --mode full --dry-run

    # 院フィルタ（衆議院のみ）
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/verify_parliamentary_group_pipeline.py \
        --mode verify --chamber 衆議院

前提条件:
    - Docker環境が起動済み（just up-detached）
    - マスターデータ（開催主体「国会」ID=1）がロード済み
    - Alembicマイグレーション適用済み
    - 選挙データ・当選者データがインポート済み
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
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if TYPE_CHECKING:
    from scripts.link_parliamentary_groups_bulk import BulkResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://sagebase_user:sagebase_password@postgres:5432/sagebase_db",
)

MAX_DISPLAY_REVIEW_CASES = 20

# --- データクラス ---


@dataclass
class BaselineMetrics:
    """パイプライン実行前のベースライン計測結果."""

    total_memberships: int
    memberships_by_chamber: dict[str, int]
    memberships_by_group: list[tuple[str, int]]
    measured_at: str


@dataclass
class ElectionCoverage:
    """各選挙ごとのカバー率."""

    term_number: int
    election_type: str
    total_elected: int
    has_membership: int
    coverage_rate: float


@dataclass
class CoverageStat:
    """院別のカバー率統計."""

    chamber: str
    elections_with_members: int
    total_elections: int
    coverage_rate: float
    details: list[ElectionCoverage]


@dataclass
class SkipStats:
    """スキップ統計."""

    total_processed: int
    skipped_no_party: int
    skipped_no_group: int
    skipped_multiple_groups: int
    is_estimated: bool = False

    @property
    def skip_rate_excluding_no_party(self) -> float:
        """成功指標用のスキップ率（政党未設定を除外）."""
        denominator = self.total_processed - self.skipped_no_party
        if denominator <= 0:
            return 0.0
        return (self.skipped_no_group + self.skipped_multiple_groups) / denominator


@dataclass
class ManualReviewCase:
    """手動レビューが必要なケース."""

    politician_id: int
    politician_name: str
    reason: str
    term_number: int
    chamber: str


@dataclass
class CriterionResult:
    """成功指標の判定結果."""

    name: str
    target: str
    actual: str
    passed: bool


@dataclass
class VerificationResult:
    """検証結果の全体像."""

    baseline: BaselineMetrics | None
    new_memberships: int
    total_memberships: int
    coverage_by_chamber: dict[str, CoverageStat]
    skip_stats: SkipStats
    manual_review_cases: list[ManualReviewCase]
    criteria_results: list[CriterionResult]
    overall_passed: bool


# --- 成功指標判定（純粋関数） ---


def evaluate_criteria(
    coverage_by_chamber: dict[str, CoverageStat],
    skip_stats: SkipStats,
) -> list[CriterionResult]:
    """成功指標を評価する（純粋関数）."""
    results: list[CriterionResult] = []

    # 衆議院カバー率
    hr_stat = coverage_by_chamber.get("衆議院")
    if hr_stat is not None:
        hr_passed = hr_stat.elections_with_members == hr_stat.total_elections
        results.append(
            CriterionResult(
                name="衆議院カバー率",
                target="全選挙にメンバーシップが存在する",
                actual=(
                    f"{hr_stat.elections_with_members}/{hr_stat.total_elections}選挙"
                ),
                passed=hr_passed,
            )
        )

    # 参議院カバー率
    hc_stat = coverage_by_chamber.get("参議院")
    if hc_stat is not None:
        hc_passed = hc_stat.elections_with_members == hc_stat.total_elections
        results.append(
            CriterionResult(
                name="参議院カバー率",
                target="全選挙にメンバーシップが存在する",
                actual=(
                    f"{hc_stat.elections_with_members}/{hc_stat.total_elections}選挙"
                ),
                passed=hc_passed,
            )
        )

    # スキップ率
    skip_rate = skip_stats.skip_rate_excluding_no_party
    skip_passed = skip_rate <= 0.10
    results.append(
        CriterionResult(
            name="スキップ率",
            target="10%以下",
            actual=f"{skip_rate:.1%}",
            passed=skip_passed,
        )
    )

    return results


# --- DB計測関数 ---


async def measure_baseline(session: AsyncSession) -> BaselineMetrics:
    """パイプライン実行前のベースライン計測."""
    # 総レコード数
    result = await session.execute(
        text("SELECT COUNT(*) FROM parliamentary_group_memberships")
    )
    total = result.scalar_one()

    # 院別メンバー数
    result = await session.execute(
        text("""
            SELECT pg.chamber, COUNT(*)
            FROM parliamentary_group_memberships pgm
            JOIN parliamentary_groups pg ON pg.id = pgm.parliamentary_group_id
            GROUP BY pg.chamber
            ORDER BY pg.chamber
        """)
    )
    by_chamber: dict[str, int] = {}
    for row in result.fetchall():
        by_chamber[row[0]] = row[1]

    # 会派別メンバー数
    result = await session.execute(
        text("""
            SELECT pg.name, COUNT(*)
            FROM parliamentary_group_memberships pgm
            JOIN parliamentary_groups pg ON pg.id = pgm.parliamentary_group_id
            GROUP BY pg.name
            ORDER BY COUNT(*) DESC
        """)
    )
    by_group: list[tuple[str, int]] = [(row[0], row[1]) for row in result.fetchall()]

    return BaselineMetrics(
        total_memberships=total,
        memberships_by_chamber=by_chamber,
        memberships_by_group=by_group,
        measured_at=datetime.now(UTC).isoformat(),
    )


async def calculate_coverage(
    session: AsyncSession,
    chamber_filter: str | None = None,
) -> dict[str, CoverageStat]:
    """各選挙について当選者数 vs メンバーシップ保持者数を算出する."""
    params: dict[str, str] = {}
    chamber_clause = ""
    if chamber_filter and chamber_filter != "all":
        chamber_clause = "AND e.chamber = :chamber"
        params["chamber"] = chamber_filter

    result = await session.execute(
        text(f"""
            SELECT
                e.term_number,
                COALESCE(e.election_type, '') AS election_type,
                e.chamber,
                COUNT(DISTINCT em.politician_id) AS total_elected,
                COUNT(DISTINCT pgm.politician_id) AS has_membership
            FROM elections e
            JOIN election_members em ON em.election_id = e.id
            LEFT JOIN parliamentary_group_memberships pgm
                ON pgm.politician_id = em.politician_id
                AND e.election_date >= pgm.start_date
                AND (pgm.end_date IS NULL OR e.election_date <= pgm.end_date)
            WHERE em.result IN ('当選', '繰上当選', '無投票当選')
                {chamber_clause}
            GROUP BY e.term_number, e.election_type, e.chamber
            ORDER BY e.chamber, e.term_number
        """),
        params if params else None,
    )

    stats_by_chamber: dict[str, list[ElectionCoverage]] = {}
    for row in result.fetchall():
        chamber = row[2]
        total_elected = row[3]
        has_membership = row[4]
        rate = has_membership / total_elected if total_elected > 0 else 0.0
        detail = ElectionCoverage(
            term_number=row[0],
            election_type=row[1],
            total_elected=total_elected,
            has_membership=has_membership,
            coverage_rate=rate,
        )
        if chamber not in stats_by_chamber:
            stats_by_chamber[chamber] = []
        stats_by_chamber[chamber].append(detail)

    coverage: dict[str, CoverageStat] = {}
    for chamber, details in stats_by_chamber.items():
        with_members = sum(1 for d in details if d.has_membership > 0)
        total = len(details)
        coverage[chamber] = CoverageStat(
            chamber=chamber,
            elections_with_members=with_members,
            total_elections=total,
            coverage_rate=with_members / total if total > 0 else 0.0,
            details=details,
        )

    return coverage


async def calculate_skip_rate(
    session: AsyncSession,
    bulk_result: BulkResult | None = None,
) -> SkipStats:
    """スキップ率を計算する.

    mode=full時: BulkResultの統計値を直接使用（最も正確）。
    mode=verify時: DB状態から推定。
    """
    if bulk_result is not None:
        # BulkResultから直接取得
        from scripts.link_parliamentary_groups_bulk import BulkResult

        if isinstance(bulk_result, BulkResult):
            total_no_party = sum(
                r.output.skipped_no_party for r in bulk_result.results if r.output
            )
            total_no_group = sum(
                r.output.skipped_no_group for r in bulk_result.results if r.output
            )
            total_multiple = sum(
                r.output.skipped_multiple_groups
                for r in bulk_result.results
                if r.output
            )
            return SkipStats(
                total_processed=bulk_result.total_elected,
                skipped_no_party=total_no_party,
                skipped_no_group=total_no_group,
                skipped_multiple_groups=total_multiple,
                is_estimated=False,
            )

    # DB状態から推定
    # 全当選者数
    result = await session.execute(
        text("""
            SELECT COUNT(DISTINCT em.politician_id)
            FROM election_members em
            WHERE em.result IN ('当選', '繰上当選', '無投票当選')
        """)
    )
    total_elected = result.scalar_one()

    # 政党未設定の当選者数
    result = await session.execute(
        text("""
            SELECT COUNT(DISTINCT em.politician_id)
            FROM election_members em
            WHERE em.result IN ('当選', '繰上当選', '無投票当選')
              AND NOT EXISTS (
                  SELECT 1
                  FROM party_membership_history pmh
                  WHERE pmh.politician_id = em.politician_id
                    AND pmh.end_date IS NULL
              )
        """)
    )
    no_party = result.scalar_one()

    # メンバーシップなし＋政党ありの当選者数（スキップとみなす）
    result = await session.execute(
        text("""
            SELECT COUNT(DISTINCT em.politician_id)
            FROM election_members em
            WHERE em.result IN ('当選', '繰上当選', '無投票当選')
              AND EXISTS (
                  SELECT 1
                  FROM party_membership_history pmh
                  WHERE pmh.politician_id = em.politician_id
                    AND pmh.end_date IS NULL
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM parliamentary_group_memberships pgm
                  WHERE pgm.politician_id = em.politician_id
              )
        """)
    )
    skipped_with_party = result.scalar_one()

    return SkipStats(
        total_processed=total_elected,
        skipped_no_party=no_party,
        skipped_no_group=skipped_with_party,
        skipped_multiple_groups=0,
        is_estimated=True,
    )


async def extract_manual_review_cases(
    session: AsyncSession,
) -> list[ManualReviewCase]:
    """手動レビューが必要なケースを抽出する.

    当選者のうち、メンバーシップなし＋政党所属ありの議員をリスト化する。
    """
    result = await session.execute(
        text("""
            SELECT DISTINCT
                p.id AS politician_id,
                p.name AS politician_name,
                e.term_number,
                e.chamber
            FROM election_members em
            JOIN elections e ON e.id = em.election_id
            JOIN politicians p ON p.id = em.politician_id
            WHERE em.result IN ('当選', '繰上当選', '無投票当選')
              AND EXISTS (
                  SELECT 1
                  FROM party_membership_history pmh
                  WHERE pmh.politician_id = em.politician_id
                    AND pmh.end_date IS NULL
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM parliamentary_group_memberships pgm
                  WHERE pgm.politician_id = em.politician_id
              )
            ORDER BY e.chamber, e.term_number, p.id
            LIMIT 100
        """)
    )

    cases: list[ManualReviewCase] = []
    for row in result.fetchall():
        cases.append(
            ManualReviewCase(
                politician_id=row[0],
                politician_name=row[1],
                reason="対応会派なし",
                term_number=row[2],
                chamber=row[3],
            )
        )

    return cases


# --- レポート出力 ---


def print_baseline_report(baseline: BaselineMetrics) -> None:
    """ベースライン計測結果をコンソール出力する."""
    print("=" * 60)
    print("ベースライン計測結果")
    print("=" * 60)
    print(f"計測日時: {baseline.measured_at}")
    print(f"会派メンバーシップ総数: {baseline.total_memberships}")

    if baseline.memberships_by_chamber:
        print("\n[院別メンバー数]")
        for chamber, count in baseline.memberships_by_chamber.items():
            print(f"  {chamber}: {count}")

    if baseline.memberships_by_group:
        print("\n[会派別メンバー数（上位10件）]")
        for name, count in baseline.memberships_by_group[:10]:
            print(f"  {name}: {count}")


def print_verification_report(result: VerificationResult) -> None:
    """検証結果をコンソール出力する."""
    print("=" * 60)
    print("会派所属パイプライン検証結果")
    print("=" * 60)

    # ベースラインとの差分
    if result.baseline is not None:
        print("\n[メンバーシップ変動]")
        print(f"  実行前: {result.baseline.total_memberships}")
        print(f"  実行後: {result.total_memberships}")
        print(f"  新規追加: {result.new_memberships}")

    # カバー率
    print("\n[院別カバー率]")
    for chamber, stat in result.coverage_by_chamber.items():
        print(
            f"  {chamber}: "
            f"{stat.elections_with_members}/{stat.total_elections}選挙 "
            f"({stat.coverage_rate:.0%})"
        )
        for d in stat.details:
            mark = "○" if d.has_membership > 0 else "×"
            print(
                f"    {mark} 第{d.term_number}回: "
                f"{d.has_membership}/{d.total_elected}人 "
                f"({d.coverage_rate:.0%})"
            )

    # スキップ率
    print("\n[スキップ統計]")
    ss = result.skip_stats
    print(f"  処理対象: {ss.total_processed}")
    print(f"  政党未設定: {ss.skipped_no_party}")
    print(f"  対応会派なし: {ss.skipped_no_group}")
    print(f"  複数会派マッチ: {ss.skipped_multiple_groups}")
    print(f"  スキップ率（政党未設定除外）: {ss.skip_rate_excluding_no_party:.1%}")
    if ss.is_estimated:
        print(
            "  ※ DB推定のため複数会派マッチは区別不可（mode=fullで正確な値を取得可能）"
        )

    # 手動レビューケース
    if result.manual_review_cases:
        print(f"\n[手動レビュー対象（{len(result.manual_review_cases)}件）]")
        for case in result.manual_review_cases[:MAX_DISPLAY_REVIEW_CASES]:
            print(
                f"  - {case.politician_name} (ID:{case.politician_id}) "
                f"第{case.term_number}回 {case.chamber} - {case.reason}"
            )
        if len(result.manual_review_cases) > MAX_DISPLAY_REVIEW_CASES:
            remaining = len(result.manual_review_cases) - MAX_DISPLAY_REVIEW_CASES
            print(f"  ... 他 {remaining}件")

    # 成功指標判定
    print("\n[成功指標]")
    for cr in result.criteria_results:
        mark = "PASS" if cr.passed else "FAIL"
        print(f"  [{mark}] {cr.name}: {cr.actual}（目標: {cr.target}）")

    print("=" * 60)
    if result.overall_passed:
        print("結果: 全指標パス")
    else:
        print("結果: 一部の指標が未達")


def save_json_report(result: VerificationResult, output_path: Path) -> None:
    """検証結果をJSONファイルに保存する."""
    data = {
        "baseline": asdict(result.baseline) if result.baseline else None,
        "new_memberships": result.new_memberships,
        "total_memberships": result.total_memberships,
        "coverage_by_chamber": {
            k: asdict(v) for k, v in result.coverage_by_chamber.items()
        },
        "skip_stats": {
            "total_processed": result.skip_stats.total_processed,
            "skipped_no_party": result.skip_stats.skipped_no_party,
            "skipped_no_group": result.skip_stats.skipped_no_group,
            "skipped_multiple_groups": result.skip_stats.skipped_multiple_groups,
            "skip_rate_excluding_no_party": (
                result.skip_stats.skip_rate_excluding_no_party
            ),
            "is_estimated": result.skip_stats.is_estimated,
        },
        "manual_review_cases": [asdict(c) for c in result.manual_review_cases],
        "criteria_results": [asdict(cr) for cr in result.criteria_results],
        "overall_passed": result.overall_passed,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\nJSON結果を保存: {output_path}")


def save_baseline_json(baseline: BaselineMetrics, output_path: Path) -> None:
    """ベースライン計測結果をJSONファイルに保存する."""
    data = asdict(baseline)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\nベースラインを保存: {output_path}")


def load_baseline_json(path: Path) -> BaselineMetrics | None:
    """保存済みのベースラインJSONを読み込む."""
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return BaselineMetrics(
        total_memberships=data["total_memberships"],
        memberships_by_chamber=data["memberships_by_chamber"],
        memberships_by_group=[tuple(x) for x in data["memberships_by_group"]],
        measured_at=data["measured_at"],
    )


# --- メインフロー ---

BASELINE_JSON_PATH = Path("tmp/pipeline_baseline.json")
RESULT_JSON_PATH = Path("tmp/pipeline_verification_results.json")


async def run_baseline(session: AsyncSession) -> BaselineMetrics:
    """ベースライン計測を実行する."""
    baseline = await measure_baseline(session)
    print_baseline_report(baseline)
    save_baseline_json(baseline, BASELINE_JSON_PATH)
    return baseline


async def run_verify(
    session: AsyncSession,
    chamber_filter: str | None = None,
    bulk_result: BulkResult | None = None,
    baseline: BaselineMetrics | None = None,
) -> VerificationResult:
    """結果検証を実行する."""
    # ベースライン読み込み（未指定の場合は保存済みを試行）
    if baseline is None:
        baseline = load_baseline_json(BASELINE_JSON_PATH)

    # 現在の総メンバーシップ数
    result = await session.execute(
        text("SELECT COUNT(*) FROM parliamentary_group_memberships")
    )
    total_memberships = result.scalar_one()
    new_memberships = (
        total_memberships - baseline.total_memberships
        if baseline
        else total_memberships
    )

    # カバー率
    coverage = await calculate_coverage(session, chamber_filter)

    # スキップ率
    skip_stats = await calculate_skip_rate(session, bulk_result)

    # 手動レビューケース
    manual_cases = await extract_manual_review_cases(session)

    # 成功指標判定
    criteria = evaluate_criteria(coverage, skip_stats)
    overall = all(cr.passed for cr in criteria)

    verification = VerificationResult(
        baseline=baseline,
        new_memberships=new_memberships,
        total_memberships=total_memberships,
        coverage_by_chamber=coverage,
        skip_stats=skip_stats,
        manual_review_cases=manual_cases,
        criteria_results=criteria,
        overall_passed=overall,
    )

    print_verification_report(verification)
    save_json_report(verification, RESULT_JSON_PATH)

    return verification


async def run_full(
    dry_run: bool = False,
    chamber_filter: str | None = None,
) -> VerificationResult:
    """ベースライン計測 → パイプライン実行 → 結果検証."""
    from scripts.link_parliamentary_groups_bulk import (
        detect_national_elections,
        run_bulk_with_details,
    )

    db_url = DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url)

    # Step 1: ベースライン計測
    async with engine.connect() as conn:
        async with conn.begin():
            session = AsyncSession(bind=conn)
            baseline = await run_baseline(session)

    # Step 2: パイプライン実行
    elections_by_chamber = await detect_national_elections()

    target_elections = []
    if chamber_filter and chamber_filter != "all":
        target_elections = elections_by_chamber.get(chamber_filter, [])
    else:
        for chamber_elections in elections_by_chamber.values():
            target_elections.extend(chamber_elections)

    bulk_result = await run_bulk_with_details(target_elections, dry_run=dry_run)

    # Step 3: 結果検証
    async with engine.connect() as conn:
        async with conn.begin():
            session = AsyncSession(bind=conn)
            verification = await run_verify(
                session,
                chamber_filter=chamber_filter,
                bulk_result=bulk_result,
                baseline=baseline,
            )

    await engine.dispose()
    return verification


async def main() -> None:
    """メイン実行関数."""
    parser = argparse.ArgumentParser(
        description="会派所属パイプラインのベースライン計測・結果検証",
        epilog=(
            "例: docker compose -f docker/docker-compose.yml exec sagebase "
            "uv run python scripts/verify_parliamentary_group_pipeline.py --mode verify"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["baseline", "verify", "full"],
        default="verify",
        help="実行モード: baseline=計測のみ, verify=検証のみ, full=計測→実行→検証",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="パイプラインをドライランで実行（mode=full時のみ有効）",
    )
    parser.add_argument(
        "--chamber",
        choices=["衆議院", "参議院", "all"],
        default="all",
        help="院フィルタ（デフォルト: all）",
    )
    args = parser.parse_args()

    if args.mode == "full":
        result = await run_full(
            dry_run=args.dry_run,
            chamber_filter=args.chamber,
        )
        if not result.overall_passed:
            sys.exit(1)
        return

    db_url = DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url)

    if args.mode == "baseline":
        async with engine.connect() as conn:
            async with conn.begin():
                session = AsyncSession(bind=conn)
                await run_baseline(session)
    elif args.mode == "verify":
        async with engine.connect() as conn:
            async with conn.begin():
                session = AsyncSession(bind=conn)
                result = await run_verify(
                    session,
                    chamber_filter=args.chamber,
                )
                if not result.overall_passed:
                    await engine.dispose()
                    sys.exit(1)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
