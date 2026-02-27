"""バルクスクリプト（link_parliamentary_groups_bulk.py）のユニットテスト."""

from __future__ import annotations

import sys

from pathlib import Path


# スクリプトのimportを可能にする
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.link_parliamentary_groups_bulk import (
    BulkResult,
    ElectionResult,
    write_result_report,
)

from src.application.dtos.parliamentary_group_linkage_dto import (
    LinkParliamentaryGroupOutputDto,
    SkippedMember,
)


def _make_output(
    total_elected: int = 10,
    linked_count: int = 8,
    already_existed_count: int = 1,
    skipped_no_party: int = 0,
    skipped_no_group: int = 1,
    skipped_multiple_groups: int = 0,
    errors: int = 0,
) -> LinkParliamentaryGroupOutputDto:
    """テスト用のOutputDtoを生成するヘルパー."""
    return LinkParliamentaryGroupOutputDto(
        total_elected=total_elected,
        linked_count=linked_count,
        already_existed_count=already_existed_count,
        skipped_no_party=skipped_no_party,
        skipped_no_group=skipped_no_group,
        skipped_multiple_groups=skipped_multiple_groups,
        errors=errors,
    )


class TestElectionResult:
    """ElectionResult のテスト."""

    def test_election_result_has_chamber_info(self) -> None:
        """ElectionResult が chamber 情報を保持すること."""
        result = ElectionResult(
            term_number=50,
            election_type="衆議院議員総選挙",
            chamber="衆議院",
        )
        assert result.term_number == 50
        assert result.election_type == "衆議院議員総選挙"
        assert result.chamber == "衆議院"

    def test_election_result_defaults(self) -> None:
        """ElectionResult のデフォルト値が正しいこと."""
        result = ElectionResult(term_number=26)
        assert result.election_type == ""
        assert result.chamber == ""
        assert result.output is None
        assert result.error is None


class TestBulkResult:
    """BulkResult のテスト."""

    def test_results_by_chamber_filters_correctly(self) -> None:
        """results_by_chamber が指定院の結果のみ返すこと."""
        bulk = BulkResult(
            results=[
                ElectionResult(term_number=49, chamber="衆議院", output=_make_output()),
                ElectionResult(term_number=50, chamber="衆議院", output=_make_output()),
                ElectionResult(term_number=25, chamber="参議院", output=_make_output()),
                ElectionResult(term_number=26, chamber="参議院", output=_make_output()),
            ]
        )

        shugiin = bulk.results_by_chamber("衆議院")
        sangiin = bulk.results_by_chamber("参議院")

        assert len(shugiin) == 2
        assert all(r.chamber == "衆議院" for r in shugiin)
        assert len(sangiin) == 2
        assert all(r.chamber == "参議院" for r in sangiin)

    def test_results_by_chamber_returns_empty_for_no_match(self) -> None:
        """results_by_chamber が該当なしの場合に空リストを返すこと."""
        bulk = BulkResult(
            results=[
                ElectionResult(term_number=50, chamber="衆議院", output=_make_output()),
            ]
        )
        assert bulk.results_by_chamber("参議院") == []

    def test_total_properties(self) -> None:
        """合計プロパティが正しく集計されること."""
        bulk = BulkResult(
            results=[
                ElectionResult(
                    term_number=49,
                    chamber="衆議院",
                    output=_make_output(
                        total_elected=100,
                        linked_count=80,
                        already_existed_count=10,
                        skipped_no_party=5,
                        skipped_no_group=3,
                        skipped_multiple_groups=2,
                    ),
                ),
                ElectionResult(
                    term_number=50,
                    chamber="衆議院",
                    output=_make_output(
                        total_elected=200,
                        linked_count=150,
                        already_existed_count=20,
                        skipped_no_party=10,
                        skipped_no_group=15,
                        skipped_multiple_groups=5,
                    ),
                ),
            ]
        )
        assert bulk.total_elected == 300
        assert bulk.total_linked == 230
        assert bulk.total_already_existed == 30
        assert bulk.total_skipped == 40  # (5+3+2) + (10+15+5)

    def test_totals_skip_errored_results(self) -> None:
        """エラー結果は合計から除外されること."""
        bulk = BulkResult(
            results=[
                ElectionResult(
                    term_number=49,
                    chamber="衆議院",
                    output=_make_output(total_elected=100, linked_count=80),
                ),
                ElectionResult(
                    term_number=50,
                    chamber="衆議院",
                    error="DBエラー",
                ),
            ]
        )
        assert bulk.total_elected == 100
        assert bulk.total_linked == 80


class TestWriteResultReport:
    """write_result_report のテスト."""

    def test_report_contains_chamber_sections(self, tmp_path: Path) -> None:
        """レポートに院別セクションが含まれること."""
        bulk = BulkResult(
            results=[
                ElectionResult(
                    term_number=50,
                    chamber="衆議院",
                    output=_make_output(total_elected=100, linked_count=80),
                ),
                ElectionResult(
                    term_number=26,
                    chamber="参議院",
                    output=_make_output(total_elected=50, linked_count=40),
                ),
            ]
        )

        output_path = str(tmp_path / "report.txt")
        write_result_report(bulk, output_path)

        content = Path(output_path).read_text()
        assert "=== 衆議院 ===" in content
        assert "=== 参議院 ===" in content
        assert "第50回" in content
        assert "第26回" in content
        assert "=== 全体サマリー ===" in content

    def test_report_skipped_members_include_chamber(self, tmp_path: Path) -> None:
        """スキップ議員一覧に院名が含まれること."""
        bulk = BulkResult(
            results=[
                ElectionResult(
                    term_number=50,
                    chamber="衆議院",
                    output=LinkParliamentaryGroupOutputDto(
                        total_elected=10,
                        linked_count=8,
                        skipped_members=[
                            SkippedMember(
                                politician_id=1,
                                politician_name="テスト太郎",
                                reason="政党未設定",
                            )
                        ],
                    ),
                ),
            ]
        )

        output_path = str(tmp_path / "report.txt")
        write_result_report(bulk, output_path)

        content = Path(output_path).read_text()
        assert "テスト太郎" in content
        assert "(衆議院)" in content

    def test_report_with_error_result(self, tmp_path: Path) -> None:
        """エラー結果がレポートに含まれること."""
        bulk = BulkResult(
            results=[
                ElectionResult(
                    term_number=50,
                    chamber="衆議院",
                    error="接続エラー",
                ),
            ]
        )

        output_path = str(tmp_path / "report.txt")
        write_result_report(bulk, output_path)

        content = Path(output_path).read_text()
        assert "エラー: 接続エラー" in content
