"""ValidateDataIntegrityUseCaseのテスト."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dtos.data_integrity_dto import (
    CheckResult,
    DataIntegrityReport,
)
from src.application.usecases.validate_data_integrity_usecase import (
    ValidateDataIntegrityUseCase,
)
from src.domain.repositories.session_adapter import ISessionAdapter


@pytest.fixture
def mock_session() -> AsyncMock:
    """ISessionAdapterのモックを作成."""
    return AsyncMock(spec=ISessionAdapter)


def _make_scalar_result(value: int) -> MagicMock:
    """scalar()でカウント値を返すモック結果を作成."""
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _make_fetchall_result(rows: list[MagicMock]) -> MagicMock:
    """fetchall()で行リストを返すモック結果を作成."""
    result = MagicMock()
    result.fetchall.return_value = rows
    return result


def _make_row(**kwargs: int | str | date | None) -> MagicMock:
    """名前付きアクセス可能な行モックを作成."""
    row = MagicMock()
    for key, value in kwargs.items():
        setattr(row, key, value)
    return row


class TestDataIntegrityReport:
    """DataIntegrityReportのユニットテスト."""

    def test_all_passed_when_all_checks_pass(self) -> None:
        report = DataIntegrityReport(
            checks=[
                CheckResult(
                    name="check1",
                    passed=True,
                    total_checked=10,
                    issue_count=0,
                ),
                CheckResult(
                    name="check2",
                    passed=True,
                    total_checked=5,
                    issue_count=0,
                ),
            ]
        )
        assert report.all_passed is True
        assert report.total_issues == 0

    def test_all_passed_false_when_any_fails(self) -> None:
        report = DataIntegrityReport(
            checks=[
                CheckResult(
                    name="check1",
                    passed=True,
                    total_checked=10,
                    issue_count=0,
                ),
                CheckResult(
                    name="check2",
                    passed=False,
                    total_checked=5,
                    issue_count=2,
                ),
            ]
        )
        assert report.all_passed is False
        assert report.total_issues == 2

    def test_empty_checks(self) -> None:
        report = DataIntegrityReport()
        assert report.all_passed is True
        assert report.total_issues == 0


class TestCheckResult:
    """CheckResultのユニットテスト."""

    def test_summary_pass(self) -> None:
        result = CheckResult(name="test", passed=True, total_checked=100, issue_count=0)
        assert "PASS" in result.summary
        assert "100件" in result.summary

    def test_summary_fail(self) -> None:
        result = CheckResult(
            name="test",
            passed=False,
            total_checked=100,
            issue_count=3,
        )
        assert "FAIL" in result.summary
        assert "3件" in result.summary


class TestPartyMembershipOverlapCheck:
    """政党所属期間の重複チェックのテスト."""

    @pytest.mark.asyncio
    async def test_no_overlaps(self, mock_session: AsyncMock) -> None:
        """重複がない場合PASSになる."""
        mock_session.execute = AsyncMock(
            side_effect=[
                _make_scalar_result(100),  # count
                _make_fetchall_result([]),  # overlap query
                # 以降のチェック（全PASS）
                _make_scalar_result(0),
                _make_fetchall_result([]),
                _make_scalar_result(0),
                _make_fetchall_result([]),
                # 孤立FKチェック（6つのFK確認）
                *[_make_fetchall_result([]) for _ in range(6)],
            ]
        )

        usecase = ValidateDataIntegrityUseCase(mock_session)
        report = await usecase.execute()

        party_check = report.checks[0]
        assert party_check.name == "政党所属期間の重複チェック"
        assert party_check.passed is True
        assert party_check.total_checked == 100
        assert party_check.issue_count == 0

    @pytest.mark.asyncio
    async def test_with_overlaps(self, mock_session: AsyncMock) -> None:
        """重複がある場合FAILになる."""
        overlap_row = _make_row(
            id_a=1,
            id_b=2,
            politician_id=10,
            start_a=date(2020, 1, 1),
            end_a=date(2022, 12, 31),
            start_b=date(2022, 1, 1),
            end_b=date(2023, 12, 31),
        )

        mock_session.execute = AsyncMock(
            side_effect=[
                _make_scalar_result(50),
                _make_fetchall_result([overlap_row]),
                # 以降のチェック（全PASS）
                _make_scalar_result(0),
                _make_fetchall_result([]),
                _make_scalar_result(0),
                _make_fetchall_result([]),
                # 孤立FKチェック（6つのFK確認）
                *[_make_fetchall_result([]) for _ in range(6)],
            ]
        )

        usecase = ValidateDataIntegrityUseCase(mock_session)
        report = await usecase.execute()

        party_check = report.checks[0]
        assert party_check.passed is False
        assert party_check.issue_count == 1
        assert party_check.issues[0].table == "party_membership_history"
        assert "politician_id=10" in party_check.issues[0].description
        assert "レコード1" in party_check.issues[0].description
        assert "レコード2" in party_check.issues[0].description


class TestMembershipWithinGroupPeriodCheck:
    """メンバーシップ期間の整合性チェックのテスト."""

    @pytest.mark.asyncio
    async def test_all_within_period(self, mock_session: AsyncMock) -> None:
        """全メンバーシップが会派存続期間内の場合PASSになる."""
        mock_session.execute = AsyncMock(
            side_effect=[
                # 政党所属チェック
                _make_scalar_result(0),
                _make_fetchall_result([]),
                # メンバーシップ整合性チェック
                _make_scalar_result(50),
                _make_fetchall_result([]),
                # 会派重複チェック
                _make_scalar_result(0),
                _make_fetchall_result([]),
                # 孤立FKチェック
                *[_make_fetchall_result([]) for _ in range(6)],
            ]
        )

        usecase = ValidateDataIntegrityUseCase(mock_session)
        report = await usecase.execute()

        membership_check = report.checks[1]
        assert membership_check.name == "メンバーシップ期間の整合性チェック"
        assert membership_check.passed is True

    @pytest.mark.asyncio
    async def test_membership_exceeds_group_period(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """メンバーシップが会派存続期間を逸脱する場合FAILになる."""
        mismatch_row = _make_row(
            id=5,
            parliamentary_group_id=3,
            politician_id=20,
            m_start=date(2019, 1, 1),
            m_end=date(2024, 12, 31),
            group_name="テスト会派",
            g_start=date(2020, 1, 1),
            g_end=date(2023, 12, 31),
        )

        mock_session.execute = AsyncMock(
            side_effect=[
                # 政党所属チェック
                _make_scalar_result(0),
                _make_fetchall_result([]),
                # メンバーシップ整合性チェック
                _make_scalar_result(10),
                _make_fetchall_result([mismatch_row]),
                # 会派重複チェック
                _make_scalar_result(0),
                _make_fetchall_result([]),
                # 孤立FKチェック
                *[_make_fetchall_result([]) for _ in range(6)],
            ]
        )

        usecase = ValidateDataIntegrityUseCase(mock_session)
        report = await usecase.execute()

        membership_check = report.checks[1]
        assert membership_check.passed is False
        assert membership_check.issue_count == 1
        assert "テスト会派" in membership_check.issues[0].description
        assert "politician_id=20" in membership_check.issues[0].description


class TestParliamentaryGroupOverlapCheck:
    """会派の時代重複チェックのテスト."""

    @pytest.mark.asyncio
    async def test_no_group_overlaps(self, mock_session: AsyncMock) -> None:
        """重複がない場合PASSになる."""
        mock_session.execute = AsyncMock(
            side_effect=[
                # 政党所属チェック
                _make_scalar_result(0),
                _make_fetchall_result([]),
                # メンバーシップ整合性チェック
                _make_scalar_result(0),
                _make_fetchall_result([]),
                # 会派重複チェック
                _make_scalar_result(88),
                _make_fetchall_result([]),
                # 孤立FKチェック
                *[_make_fetchall_result([]) for _ in range(6)],
            ]
        )

        usecase = ValidateDataIntegrityUseCase(mock_session)
        report = await usecase.execute()

        group_check = report.checks[2]
        assert group_check.name == "会派の時代重複チェック"
        assert group_check.passed is True
        assert group_check.total_checked == 88

    @pytest.mark.asyncio
    async def test_with_group_overlaps(self, mock_session: AsyncMock) -> None:
        """同一会派名で重複がある場合FAILになる."""
        overlap_row = _make_row(
            id_a=10,
            id_b=11,
            name="自由民主党",
            governing_body_id=1,
            start_a=date(2020, 1, 1),
            end_a=date(2023, 12, 31),
            start_b=date(2023, 1, 1),
            end_b=None,
        )

        mock_session.execute = AsyncMock(
            side_effect=[
                # 政党所属チェック
                _make_scalar_result(0),
                _make_fetchall_result([]),
                # メンバーシップ整合性チェック
                _make_scalar_result(0),
                _make_fetchall_result([]),
                # 会派重複チェック
                _make_scalar_result(88),
                _make_fetchall_result([overlap_row]),
                # 孤立FKチェック
                *[_make_fetchall_result([]) for _ in range(6)],
            ]
        )

        usecase = ValidateDataIntegrityUseCase(mock_session)
        report = await usecase.execute()

        group_check = report.checks[2]
        assert group_check.passed is False
        assert "自由民主党" in group_check.issues[0].description


class TestOrphanedForeignKeyCheck:
    """孤立FK参照チェックのテスト."""

    @pytest.mark.asyncio
    async def test_no_orphaned_fks(self, mock_session: AsyncMock) -> None:
        """孤立FKがない場合PASSになる."""
        mock_session.execute = AsyncMock(
            side_effect=[
                # 政党所属チェック
                _make_scalar_result(0),
                _make_fetchall_result([]),
                # メンバーシップ整合性チェック
                _make_scalar_result(0),
                _make_fetchall_result([]),
                # 会派重複チェック
                _make_scalar_result(0),
                _make_fetchall_result([]),
                # 孤立FKチェック（6つのFK確認、全て問題なし）
                *[_make_fetchall_result([]) for _ in range(6)],
            ]
        )

        usecase = ValidateDataIntegrityUseCase(mock_session)
        report = await usecase.execute()

        fk_check = report.checks[3]
        assert fk_check.name == "孤立FK参照チェック"
        assert fk_check.passed is True
        assert fk_check.total_checked == 6

    @pytest.mark.asyncio
    async def test_with_orphaned_fks(self, mock_session: AsyncMock) -> None:
        """孤立FKがある場合FAILになる."""
        orphan_row = _make_row(id=99, politician_id=9999)

        mock_session.execute = AsyncMock(
            side_effect=[
                # 政党所属チェック
                _make_scalar_result(0),
                _make_fetchall_result([]),
                # メンバーシップ整合性チェック
                _make_scalar_result(0),
                _make_fetchall_result([]),
                # 会派重複チェック
                _make_scalar_result(0),
                _make_fetchall_result([]),
                # 孤立FKチェック:
                # 最初のFK（party_membership_history.politician_id）に孤立あり
                _make_fetchall_result([orphan_row]),
                # 残り5つのFK確認は問題なし
                *[_make_fetchall_result([]) for _ in range(5)],
            ]
        )

        usecase = ValidateDataIntegrityUseCase(mock_session)
        report = await usecase.execute()

        fk_check = report.checks[3]
        assert fk_check.passed is False
        assert fk_check.issue_count == 1
        assert fk_check.issues[0].table == "party_membership_history"
        assert "politician_id=9999" in fk_check.issues[0].description
        assert "politicians.id" in fk_check.issues[0].description


class TestExecuteAllChecks:
    """全チェック実行の統合テスト."""

    @pytest.mark.asyncio
    async def test_all_checks_pass(self, mock_session: AsyncMock) -> None:
        """全チェックPASS時のレポートを検証."""
        mock_session.execute = AsyncMock(
            side_effect=[
                # 政党所属チェック
                _make_scalar_result(100),
                _make_fetchall_result([]),
                # メンバーシップ整合性チェック
                _make_scalar_result(50),
                _make_fetchall_result([]),
                # 会派重複チェック
                _make_scalar_result(88),
                _make_fetchall_result([]),
                # 孤立FKチェック
                *[_make_fetchall_result([]) for _ in range(6)],
            ]
        )

        usecase = ValidateDataIntegrityUseCase(mock_session)
        report = await usecase.execute()

        assert len(report.checks) == 4
        assert report.all_passed is True
        assert report.total_issues == 0

    @pytest.mark.asyncio
    async def test_multiple_failures(self, mock_session: AsyncMock) -> None:
        """複数チェック失敗時のレポートを検証."""
        overlap_row = _make_row(
            id_a=1,
            id_b=2,
            politician_id=10,
            start_a=date(2020, 1, 1),
            end_a=None,
            start_b=date(2021, 1, 1),
            end_b=None,
        )
        orphan_row = _make_row(id=99, politician_id=9999)

        mock_session.execute = AsyncMock(
            side_effect=[
                # 政党所属チェック（FAIL）
                _make_scalar_result(100),
                _make_fetchall_result([overlap_row]),
                # メンバーシップ整合性チェック（PASS）
                _make_scalar_result(50),
                _make_fetchall_result([]),
                # 会派重複チェック（PASS）
                _make_scalar_result(88),
                _make_fetchall_result([]),
                # 孤立FKチェック（FAIL: 最初のFKに孤立あり）
                _make_fetchall_result([orphan_row]),
                *[_make_fetchall_result([]) for _ in range(5)],
            ]
        )

        usecase = ValidateDataIntegrityUseCase(mock_session)
        report = await usecase.execute()

        assert report.all_passed is False
        assert report.total_issues == 2
        assert report.checks[0].passed is False  # 政党所属
        assert report.checks[1].passed is True  # メンバーシップ
        assert report.checks[2].passed is True  # 会派重複
        assert report.checks[3].passed is False  # 孤立FK
