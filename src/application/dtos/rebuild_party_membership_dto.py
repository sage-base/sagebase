"""政党所属履歴再構築に関するDTO."""

from dataclasses import dataclass


@dataclass
class RebuildPartyMembershipInputDto:
    """政党所属履歴再構築の入力DTO."""

    dry_run: bool = True


@dataclass
class RebuildPartyMembershipOutputDto:
    """政党所属履歴再構築の出力DTO."""

    total_politicians: int = 0
    deleted_old_records: int = 0
    created_new_records: int = 0
    politicians_with_party_change: int = 0
    skipped_no_party: int = 0
    dry_run: bool = True
