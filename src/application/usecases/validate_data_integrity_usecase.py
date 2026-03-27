"""データ整合性バリデーションユースケース.

以下の5つのチェックを実行する:
1. 同一政治家の政党所属期間重複チェック
2. 会派存続期間とメンバーシップ期間の整合性チェック
3. 同一会派名の時代重複チェック
4. 孤立FKチェック（全テーブル）
5. サマリレポート出力
"""

import logging

from sqlalchemy import text

from src.application.dtos.data_integrity_dto import (
    CheckResult,
    DataIntegrityReport,
    ValidationIssue,
)
from src.domain.repositories.session_adapter import ISessionAdapter


logger = logging.getLogger(__name__)


class ValidateDataIntegrityUseCase:
    """データ整合性バリデーションを実行するユースケース."""

    def __init__(self, session: ISessionAdapter) -> None:
        self._session = session

    async def execute(self) -> DataIntegrityReport:
        """全チェックを実行してレポートを返す."""
        report = DataIntegrityReport()

        report.checks.append(await self._check_party_membership_overlap())
        report.checks.append(await self._check_membership_within_group_period())
        report.checks.append(await self._check_parliamentary_group_overlap())
        report.checks.append(await self._check_orphaned_foreign_keys())

        return report

    async def _check_party_membership_overlap(self) -> CheckResult:
        """同一政治家の政党所属期間重複チェック.

        party_membership_historyで同一politician_idの期間が重複していないか確認する。
        """
        # 全レコード数を取得
        count_result = await self._session.execute(
            text("SELECT count(*) FROM party_membership_history")
        )
        total = count_result.scalar()

        # 同一政治家で期間が重複するレコードを検出
        overlap_query = text("""
            SELECT a.id AS id_a, b.id AS id_b,
                   a.politician_id,
                   a.start_date AS start_a, a.end_date AS end_a,
                   b.start_date AS start_b, b.end_date AS end_b
            FROM party_membership_history a
            JOIN party_membership_history b
              ON a.politician_id = b.politician_id
             AND a.id < b.id
            WHERE (a.end_date IS NULL OR a.end_date >= b.start_date)
              AND (b.end_date IS NULL OR b.end_date >= a.start_date)
        """)
        result = await self._session.execute(overlap_query)
        rows = result.fetchall()

        issues = [
            ValidationIssue(
                table="party_membership_history",
                record_id=row.id_a,
                description=(
                    f"politician_id={row.politician_id}: "
                    f"レコード{row.id_a}({row.start_a}〜{row.end_a})と"
                    f"レコード{row.id_b}({row.start_b}〜{row.end_b})が重複"
                ),
            )
            for row in rows
        ]

        return CheckResult(
            name="政党所属期間の重複チェック",
            passed=len(issues) == 0,
            total_checked=total,
            issue_count=len(issues),
            issues=issues,
        )

    async def _check_membership_within_group_period(self) -> CheckResult:
        """会派存続期間とメンバーシップ期間の整合性チェック.

        parliamentary_group_membershipsの期間が
        所属するparliamentary_groupsの存続期間内か確認する。
        """
        count_result = await self._session.execute(
            text("SELECT count(*) FROM parliamentary_group_memberships")
        )
        total = count_result.scalar()

        # メンバーシップ期間がグループ存続期間を逸脱するレコードを検出
        mismatch_query = text("""
            SELECT m.id, m.parliamentary_group_id, m.politician_id,
                   m.start_date AS m_start, m.end_date AS m_end,
                   g.name AS group_name,
                   g.start_date AS g_start, g.end_date AS g_end
            FROM parliamentary_group_memberships m
            JOIN parliamentary_groups g ON m.parliamentary_group_id = g.id
            WHERE
                (g.start_date IS NOT NULL AND m.start_date < g.start_date)
                OR (g.end_date IS NOT NULL AND m.end_date IS NULL)
                OR (g.end_date IS NOT NULL AND m.end_date IS NOT NULL
                    AND m.end_date > g.end_date)
        """)
        result = await self._session.execute(mismatch_query)
        rows = result.fetchall()

        issues = [
            ValidationIssue(
                table="parliamentary_group_memberships",
                record_id=row.id,
                description=(
                    f"会派「{row.group_name}」(期間:{row.g_start}〜{row.g_end})に対し、"
                    f"メンバーシップ(politician_id={row.politician_id})の"
                    f"期間({row.m_start}〜{row.m_end})が逸脱"
                ),
            )
            for row in rows
        ]

        return CheckResult(
            name="メンバーシップ期間の整合性チェック",
            passed=len(issues) == 0,
            total_checked=total,
            issue_count=len(issues),
            issues=issues,
        )

    async def _check_parliamentary_group_overlap(self) -> CheckResult:
        """同一会派名で期間が重複していないかチェック.

        同一governing_body_id + 同一nameの会派で期間が重複するものを検出する。
        """
        count_result = await self._session.execute(
            text("SELECT count(*) FROM parliamentary_groups")
        )
        total = count_result.scalar()

        overlap_query = text("""
            SELECT a.id AS id_a, b.id AS id_b,
                   a.name, a.governing_body_id,
                   a.start_date AS start_a, a.end_date AS end_a,
                   b.start_date AS start_b, b.end_date AS end_b
            FROM parliamentary_groups a
            JOIN parliamentary_groups b
              ON a.governing_body_id = b.governing_body_id
             AND a.name = b.name
             AND a.id < b.id
            WHERE
                (a.start_date IS NOT NULL AND b.start_date IS NOT NULL)
                AND (a.end_date IS NULL OR a.end_date >= b.start_date)
                AND (b.end_date IS NULL OR b.end_date >= a.start_date)
        """)
        result = await self._session.execute(overlap_query)
        rows = result.fetchall()

        issues = [
            ValidationIssue(
                table="parliamentary_groups",
                record_id=row.id_a,
                description=(
                    f"会派「{row.name}」(governing_body_id={row.governing_body_id}): "
                    f"レコード{row.id_a}({row.start_a}〜{row.end_a})と"
                    f"レコード{row.id_b}({row.start_b}〜{row.end_b})が重複"
                ),
            )
            for row in rows
        ]

        return CheckResult(
            name="会派の時代重複チェック",
            passed=len(issues) == 0,
            total_checked=total,
            issue_count=len(issues),
            issues=issues,
        )

    async def _check_orphaned_foreign_keys(self) -> CheckResult:
        """全テーブルの孤立FKチェック.

        各テーブルのFK参照先が存在するか確認する。
        """
        fk_checks: list[tuple[str, str, str, str]] = [
            # (テーブル, FKカラム, 参照先テーブル, 参照先カラム)
            ("party_membership_history", "politician_id", "politicians", "id"),
            (
                "party_membership_history",
                "political_party_id",
                "political_parties",
                "id",
            ),
            (
                "parliamentary_group_memberships",
                "politician_id",
                "politicians",
                "id",
            ),
            (
                "parliamentary_group_memberships",
                "parliamentary_group_id",
                "parliamentary_groups",
                "id",
            ),
            (
                "parliamentary_group_parties",
                "parliamentary_group_id",
                "parliamentary_groups",
                "id",
            ),
            (
                "parliamentary_group_parties",
                "political_party_id",
                "political_parties",
                "id",
            ),
        ]

        issues: list[ValidationIssue] = []
        total_checked = 0

        for source_table, fk_col, ref_table, ref_col in fk_checks:
            total_checked += 1
            query = text(f"""
                SELECT s.id, s.{fk_col}
                FROM {source_table} s
                LEFT JOIN {ref_table} r ON s.{fk_col} = r.{ref_col}
                WHERE r.{ref_col} IS NULL
            """)  # noqa: S608
            result = await self._session.execute(query)
            rows = result.fetchall()

            for row in rows:
                issues.append(
                    ValidationIssue(
                        table=source_table,
                        record_id=row.id,
                        description=(
                            f"{fk_col}={getattr(row, fk_col)} が "
                            f"{ref_table}.{ref_col} に存在しない"
                        ),
                    )
                )

        return CheckResult(
            name="孤立FK参照チェック",
            passed=len(issues) == 0,
            total_checked=total_checked,
            issue_count=len(issues),
            issues=issues,
        )
