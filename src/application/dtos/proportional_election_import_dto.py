"""比例代表選挙データインポート用DTO."""

from dataclasses import dataclass, field


@dataclass
class ImportProportionalElectionInputDto:
    """比例代表選挙インポートの入力DTO."""

    election_number: int
    governing_body_id: int
    dry_run: bool = False


@dataclass
class ImportProportionalElectionOutputDto:
    """比例代表選挙インポートの出力DTO."""

    election_number: int
    election_id: int | None = None
    total_candidates: int = 0
    elected_candidates: int = 0
    proportional_elected: int = 0
    proportional_revival: int = 0
    matched_politicians: int = 0
    created_politicians: int = 0
    created_parties: int = 0
    skipped_smd_winner: int = 0
    skipped_ambiguous: int = 0
    election_members_created: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)
