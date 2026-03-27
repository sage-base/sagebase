"""データ整合性バリデーション結果のDTO."""

from dataclasses import dataclass, field


@dataclass
class ValidationIssue:
    """個別のバリデーション問題."""

    table: str
    record_id: int
    description: str


@dataclass
class CheckResult:
    """単一チェック項目の結果."""

    name: str
    passed: bool
    total_checked: int
    issue_count: int
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.passed:
            return f"PASS ({self.total_checked}件チェック, 問題なし)"
        return f"FAIL ({self.total_checked}件チェック, {self.issue_count}件の問題)"


@dataclass
class DataIntegrityReport:
    """データ整合性バリデーションの全体レポート."""

    checks: list[CheckResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def total_issues(self) -> int:
        return sum(c.issue_count for c in self.checks)
