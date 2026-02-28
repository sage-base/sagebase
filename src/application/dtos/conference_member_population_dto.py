"""選挙当選者→ConferenceMember一括生成用DTO."""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class PopulateConferenceMembersInputDto:
    """ConferenceMember一括生成の入力DTO."""

    term_number: int
    governing_body_id: int = 1
    conference_name: str = "衆議院本会議"
    election_type: str | None = None
    dry_run: bool = False


@dataclass
class PopulatedMember:
    """生成されたメンバー."""

    politician_id: int
    politician_name: str
    start_date: date
    end_date: date | None
    was_existing: bool


@dataclass
class PopulateConferenceMembersOutputDto:
    """ConferenceMember一括生成の出力DTO."""

    total_elected: int = 0
    created_count: int = 0
    already_existed_count: int = 0
    errors: int = 0
    populated_members: list[PopulatedMember] = field(default_factory=list)
    error_details: list[str] = field(default_factory=list)
