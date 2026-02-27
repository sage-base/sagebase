"""会派所属パイプライン検証スクリプトのユニットテスト."""

from __future__ import annotations

import json
import sys

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.verify_parliamentary_group_pipeline import (
    BaselineMetrics,
    CoverageStat,
    CriterionResult,
    ElectionCoverage,
    ManualReviewCase,
    SkipStats,
    VerificationResult,
    calculate_coverage,
    calculate_skip_rate,
    evaluate_criteria,
    extract_manual_review_cases,
    load_baseline_json,
    measure_baseline,
    save_json_report,
)


# --- evaluate_criteria テスト ---


class TestEvaluateCriteria:
    """evaluate_criteria 関数のテスト."""

    def test_all_pass(self) -> None:
        """全指標がパスするケース."""
        coverage = {
            "衆議院": CoverageStat(
                chamber="衆議院",
                elections_with_members=3,
                total_elections=3,
                coverage_rate=1.0,
                details=[],
            ),
            "参議院": CoverageStat(
                chamber="参議院",
                elections_with_members=2,
                total_elections=2,
                coverage_rate=1.0,
                details=[],
            ),
        }
        skip_stats = SkipStats(
            total_processed=100,
            skipped_no_party=10,
            skipped_no_group=5,
            skipped_multiple_groups=2,
        )

        results = evaluate_criteria(coverage, skip_stats)

        assert len(results) == 3
        assert all(cr.passed for cr in results)

    def test_house_of_representatives_coverage_fail(self) -> None:
        """衆議院カバー率が不足するケース."""
        coverage = {
            "衆議院": CoverageStat(
                chamber="衆議院",
                elections_with_members=2,
                total_elections=3,
                coverage_rate=2.0 / 3,
                details=[],
            ),
            "参議院": CoverageStat(
                chamber="参議院",
                elections_with_members=2,
                total_elections=2,
                coverage_rate=1.0,
                details=[],
            ),
        }
        skip_stats = SkipStats(
            total_processed=100,
            skipped_no_party=10,
            skipped_no_group=5,
            skipped_multiple_groups=2,
        )

        results = evaluate_criteria(coverage, skip_stats)

        hr = next(cr for cr in results if cr.name == "衆議院カバー率")
        hc = next(cr for cr in results if cr.name == "参議院カバー率")
        assert not hr.passed
        assert hc.passed

    def test_house_of_councillors_coverage_fail(self) -> None:
        """参議院カバー率が不足するケース."""
        coverage = {
            "衆議院": CoverageStat(
                chamber="衆議院",
                elections_with_members=3,
                total_elections=3,
                coverage_rate=1.0,
                details=[],
            ),
            "参議院": CoverageStat(
                chamber="参議院",
                elections_with_members=1,
                total_elections=2,
                coverage_rate=0.5,
                details=[],
            ),
        }
        skip_stats = SkipStats(
            total_processed=100,
            skipped_no_party=10,
            skipped_no_group=5,
            skipped_multiple_groups=2,
        )

        results = evaluate_criteria(coverage, skip_stats)

        hc = next(cr for cr in results if cr.name == "参議院カバー率")
        assert not hc.passed

    def test_skip_rate_exceeds_threshold(self) -> None:
        """スキップ率が10%を超過するケース."""
        coverage = {
            "衆議院": CoverageStat(
                chamber="衆議院",
                elections_with_members=3,
                total_elections=3,
                coverage_rate=1.0,
                details=[],
            ),
        }
        # 政党未設定10人を除いた90人中、15人がスキップ → 16.7%
        skip_stats = SkipStats(
            total_processed=100,
            skipped_no_party=10,
            skipped_no_group=10,
            skipped_multiple_groups=5,
        )

        results = evaluate_criteria(coverage, skip_stats)

        skip_cr = next(cr for cr in results if cr.name == "スキップ率")
        assert not skip_cr.passed

    def test_skip_rate_boundary_at_10_percent(self) -> None:
        """スキップ率がちょうど10%の境界値ケース."""
        coverage: dict[str, CoverageStat] = {}
        # 政党未設定0人、100人中10人がスキップ → ちょうど10%
        skip_stats = SkipStats(
            total_processed=100,
            skipped_no_party=0,
            skipped_no_group=7,
            skipped_multiple_groups=3,
        )

        results = evaluate_criteria(coverage, skip_stats)

        skip_cr = next(cr for cr in results if cr.name == "スキップ率")
        assert skip_cr.passed  # 10%以下なのでパス

    def test_skip_rate_just_above_10_percent(self) -> None:
        """スキップ率がわずかに10%を超過する境界値ケース."""
        coverage: dict[str, CoverageStat] = {}
        # 100人中11人がスキップ → 11%
        skip_stats = SkipStats(
            total_processed=100,
            skipped_no_party=0,
            skipped_no_group=6,
            skipped_multiple_groups=5,
        )

        results = evaluate_criteria(coverage, skip_stats)

        skip_cr = next(cr for cr in results if cr.name == "スキップ率")
        assert not skip_cr.passed

    def test_no_chamber_data(self) -> None:
        """院データがない場合、スキップ率のみ判定される."""
        coverage: dict[str, CoverageStat] = {}
        skip_stats = SkipStats(
            total_processed=50,
            skipped_no_party=5,
            skipped_no_group=2,
            skipped_multiple_groups=1,
        )

        results = evaluate_criteria(coverage, skip_stats)

        assert len(results) == 1
        assert results[0].name == "スキップ率"


# --- SkipStats テスト ---


class TestSkipStats:
    """SkipStats のスキップ率計算テスト."""

    def test_normal_calculation(self) -> None:
        """正常なスキップ率計算."""
        stats = SkipStats(
            total_processed=100,
            skipped_no_party=20,
            skipped_no_group=5,
            skipped_multiple_groups=3,
        )
        # (5 + 3) / (100 - 20) = 8 / 80 = 0.1
        assert stats.skip_rate_excluding_no_party == pytest.approx(0.1)

    def test_zero_division_prevention_all_no_party(self) -> None:
        """全員が政党未設定の場合のゼロ除算防止."""
        stats = SkipStats(
            total_processed=50,
            skipped_no_party=50,
            skipped_no_group=0,
            skipped_multiple_groups=0,
        )
        assert stats.skip_rate_excluding_no_party == 0.0

    def test_zero_division_prevention_zero_processed(self) -> None:
        """処理対象が0人の場合のゼロ除算防止."""
        stats = SkipStats(
            total_processed=0,
            skipped_no_party=0,
            skipped_no_group=0,
            skipped_multiple_groups=0,
        )
        assert stats.skip_rate_excluding_no_party == 0.0

    def test_no_skip(self) -> None:
        """スキップ0件."""
        stats = SkipStats(
            total_processed=100,
            skipped_no_party=10,
            skipped_no_group=0,
            skipped_multiple_groups=0,
        )
        assert stats.skip_rate_excluding_no_party == 0.0


# --- measure_baseline テスト ---


class TestMeasureBaseline:
    """measure_baseline のテスト."""

    @pytest.mark.asyncio
    async def test_measure_baseline_returns_metrics(self) -> None:
        """ベースライン計測結果がBaselineMetricsを返す."""
        session = AsyncMock(spec=AsyncMock)

        # 総レコード数
        total_result = MagicMock()
        total_result.scalar_one.return_value = 150

        # 院別
        chamber_result = MagicMock()
        chamber_result.fetchall.return_value = [
            ("衆議院", 100),
            ("参議院", 50),
        ]

        # 会派別
        group_result = MagicMock()
        group_result.fetchall.return_value = [
            ("自由民主党", 80),
            ("立憲民主党", 40),
            ("公明党", 30),
        ]

        session.execute = AsyncMock(
            side_effect=[total_result, chamber_result, group_result]
        )

        baseline = await measure_baseline(session)

        assert baseline.total_memberships == 150
        assert baseline.memberships_by_chamber == {"衆議院": 100, "参議院": 50}
        assert len(baseline.memberships_by_group) == 3
        assert baseline.memberships_by_group[0] == ("自由民主党", 80)
        assert baseline.measured_at  # 空でないこと


# --- calculate_coverage テスト ---


class TestCalculateCoverage:
    """calculate_coverage のテスト."""

    @pytest.mark.asyncio
    async def test_all_elections_have_members(self) -> None:
        """全選挙にメンバーシップがあるケース."""
        session = AsyncMock(spec=AsyncMock)

        result_mock = MagicMock()
        result_mock.fetchall.return_value = [
            (49, "衆議院議員総選挙", "衆議院", 465, 400),
            (50, "衆議院議員総選挙", "衆議院", 465, 450),
        ]
        session.execute = AsyncMock(return_value=result_mock)

        coverage = await calculate_coverage(session)

        assert "衆議院" in coverage
        hr = coverage["衆議院"]
        assert hr.elections_with_members == 2
        assert hr.total_elections == 2
        assert hr.coverage_rate == 1.0

    @pytest.mark.asyncio
    async def test_partial_coverage(self) -> None:
        """一部の選挙のみメンバーシップがあるケース."""
        session = AsyncMock(spec=AsyncMock)

        result_mock = MagicMock()
        result_mock.fetchall.return_value = [
            (49, "衆議院議員総選挙", "衆議院", 465, 400),
            (50, "衆議院議員総選挙", "衆議院", 465, 0),
        ]
        session.execute = AsyncMock(return_value=result_mock)

        coverage = await calculate_coverage(session)

        hr = coverage["衆議院"]
        assert hr.elections_with_members == 1
        assert hr.total_elections == 2
        assert hr.coverage_rate == 0.5

    @pytest.mark.asyncio
    async def test_empty_data(self) -> None:
        """データなしのケース."""
        session = AsyncMock(spec=AsyncMock)

        result_mock = MagicMock()
        result_mock.fetchall.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        coverage = await calculate_coverage(session)

        assert coverage == {}

    @pytest.mark.asyncio
    async def test_chamber_filter(self) -> None:
        """院フィルタが適用されること."""
        session = AsyncMock(spec=AsyncMock)

        result_mock = MagicMock()
        result_mock.fetchall.return_value = [
            (49, "衆議院議員総選挙", "衆議院", 465, 400),
        ]
        session.execute = AsyncMock(return_value=result_mock)

        await calculate_coverage(session, chamber_filter="衆議院")

        # SQLにフィルタが含まれることを確認
        call_args = session.execute.call_args[0][0]
        assert "衆議院" in str(call_args)


# --- calculate_skip_rate テスト ---


class TestCalculateSkipRate:
    """calculate_skip_rate のテスト."""

    @pytest.mark.asyncio
    async def test_from_db_estimation(self) -> None:
        """DB状態から推定するケース."""
        session = AsyncMock(spec=AsyncMock)

        total_result = MagicMock()
        total_result.scalar_one.return_value = 500

        no_party_result = MagicMock()
        no_party_result.scalar_one.return_value = 50

        skipped_result = MagicMock()
        skipped_result.scalar_one.return_value = 30

        session.execute = AsyncMock(
            side_effect=[total_result, no_party_result, skipped_result]
        )

        stats = await calculate_skip_rate(session)

        assert stats.total_processed == 500
        assert stats.skipped_no_party == 50
        assert stats.skipped_no_group == 30
        assert stats.skipped_multiple_groups == 0


# --- extract_manual_review_cases テスト ---


class TestExtractManualReviewCases:
    """extract_manual_review_cases のテスト."""

    @pytest.mark.asyncio
    async def test_returns_cases(self) -> None:
        """手動レビューケースを返すこと."""
        session = AsyncMock(spec=AsyncMock)

        result_mock = MagicMock()
        result_mock.fetchall.return_value = [
            (101, "山田太郎", 49, "衆議院"),
            (102, "鈴木花子", 25, "参議院"),
        ]
        session.execute = AsyncMock(return_value=result_mock)

        cases = await extract_manual_review_cases(session)

        assert len(cases) == 2
        assert cases[0].politician_id == 101
        assert cases[0].politician_name == "山田太郎"
        assert cases[0].reason == "対応会派なし"
        assert cases[0].term_number == 49
        assert cases[0].chamber == "衆議院"

    @pytest.mark.asyncio
    async def test_empty_result(self) -> None:
        """レビューケースなしの場合."""
        session = AsyncMock(spec=AsyncMock)

        result_mock = MagicMock()
        result_mock.fetchall.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        cases = await extract_manual_review_cases(session)

        assert cases == []


# --- JSON出力テスト ---


class TestJsonReport:
    """JSON出力のテスト."""

    def test_save_json_report_creates_valid_json(self, tmp_path: Path) -> None:
        """有効なJSONが出力されること."""
        result = VerificationResult(
            baseline=BaselineMetrics(
                total_memberships=100,
                memberships_by_chamber={"衆議院": 70, "参議院": 30},
                memberships_by_group=[("自由民主党", 50)],
                measured_at="2025-01-01T00:00:00+00:00",
            ),
            new_memberships=50,
            total_memberships=150,
            coverage_by_chamber={
                "衆議院": CoverageStat(
                    chamber="衆議院",
                    elections_with_members=3,
                    total_elections=3,
                    coverage_rate=1.0,
                    details=[
                        ElectionCoverage(
                            term_number=49,
                            election_type="衆議院議員総選挙",
                            total_elected=465,
                            has_membership=400,
                            coverage_rate=400 / 465,
                        )
                    ],
                ),
            },
            skip_stats=SkipStats(
                total_processed=100,
                skipped_no_party=10,
                skipped_no_group=5,
                skipped_multiple_groups=2,
            ),
            manual_review_cases=[
                ManualReviewCase(
                    politician_id=1,
                    politician_name="テスト太郎",
                    reason="対応会派なし",
                    term_number=49,
                    chamber="衆議院",
                )
            ],
            criteria_results=[
                CriterionResult(
                    name="衆議院カバー率",
                    target="全選挙にメンバーシップが存在する",
                    actual="3/3選挙",
                    passed=True,
                )
            ],
            overall_passed=True,
        )

        output_path = tmp_path / "test_result.json"
        save_json_report(result, output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert data["overall_passed"] is True
        assert data["new_memberships"] == 50
        assert data["total_memberships"] == 150
        assert "衆議院" in data["coverage_by_chamber"]
        assert len(data["manual_review_cases"]) == 1
        assert data["skip_stats"]["skip_rate_excluding_no_party"] == pytest.approx(
            7 / 90
        )

    def test_save_json_report_without_baseline(self, tmp_path: Path) -> None:
        """ベースラインなしでもJSON出力できること."""
        result = VerificationResult(
            baseline=None,
            new_memberships=0,
            total_memberships=100,
            coverage_by_chamber={},
            skip_stats=SkipStats(
                total_processed=50,
                skipped_no_party=5,
                skipped_no_group=3,
                skipped_multiple_groups=1,
            ),
            manual_review_cases=[],
            criteria_results=[],
            overall_passed=True,
        )

        output_path = tmp_path / "test_no_baseline.json"
        save_json_report(result, output_path)

        data = json.loads(output_path.read_text())
        assert data["baseline"] is None


# --- load_baseline_json テスト ---


class TestLoadBaselineJson:
    """load_baseline_json のテスト."""

    def test_load_existing_file(self, tmp_path: Path) -> None:
        """保存済みのベースラインを読み込めること."""
        data = {
            "total_memberships": 200,
            "memberships_by_chamber": {"衆議院": 120, "参議院": 80},
            "memberships_by_group": [["自由民主党", 100], ["立憲民主党", 60]],
            "measured_at": "2025-01-01T00:00:00+00:00",
        }
        path = tmp_path / "baseline.json"
        path.write_text(json.dumps(data, ensure_ascii=False))

        result = load_baseline_json(path)

        assert result is not None
        assert result.total_memberships == 200
        assert result.memberships_by_chamber == {"衆議院": 120, "参議院": 80}
        assert result.memberships_by_group == [("自由民主党", 100), ("立憲民主党", 60)]

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        """ファイルが存在しない場合はNoneを返すこと."""
        path = tmp_path / "nonexistent.json"
        result = load_baseline_json(path)
        assert result is None
