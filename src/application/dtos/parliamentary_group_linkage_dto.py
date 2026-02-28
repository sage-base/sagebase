"""会派自動紐付け用DTO."""

from dataclasses import dataclass, field


@dataclass
class LinkParliamentaryGroupInputDto:
    """会派紐付けの入力DTO."""

    term_number: int
    governing_body_id: int = 1
    chamber: str = ""
    election_type: str | None = None
    dry_run: bool = False


@dataclass
class LinkedMember:
    """紐付け成功した議員."""

    politician_id: int
    politician_name: str
    parliamentary_group_id: int
    parliamentary_group_name: str
    was_existing: bool


@dataclass
class SkippedMember:
    """スキップされた議員."""

    politician_id: int
    politician_name: str
    reason: str
    political_party_id: int | None = None


@dataclass
class LinkParliamentaryGroupOutputDto:
    """会派紐付けの出力DTO."""

    total_elected: int = 0
    linked_count: int = 0
    already_existed_count: int = 0
    skipped_no_party: int = 0
    skipped_no_group: int = 0
    skipped_multiple_groups: int = 0
    errors: int = 0
    linked_members: list[LinkedMember] = field(default_factory=list)
    skipped_members: list[SkippedMember] = field(default_factory=list)
    error_details: list[str] = field(default_factory=list)
