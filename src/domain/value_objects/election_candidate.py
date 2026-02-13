"""選挙候補者の値オブジェクト — Domain layer."""

from dataclasses import dataclass
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
