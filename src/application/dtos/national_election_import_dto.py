"""国政選挙データインポート用DTO."""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class CandidateRecord:
    """XLSから抽出した候補者データ."""

    name: str
    party_name: str
    district_name: str
    prefecture: str
    total_votes: int
    rank: int
    is_elected: bool


@dataclass
class ElectionInfo:
    """選挙の基本情報."""

    election_number: int
    election_date: date


@dataclass
class ImportNationalElectionInputDto:
    """国政選挙インポートの入力DTO."""

    election_number: int
    governing_body_id: int
    dry_run: bool = False


@dataclass
class ImportNationalElectionOutputDto:
    """国政選挙インポートの出力DTO."""

    election_number: int
    election_id: int | None = None
    total_candidates: int = 0
    matched_politicians: int = 0
    created_politicians: int = 0
    created_parties: int = 0
    skipped_ambiguous: int = 0
    election_members_created: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=lambda: list[str]())
