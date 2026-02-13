"""比例代表候補者の値オブジェクト — Domain layer."""

from dataclasses import dataclass
from datetime import date


@dataclass
class ProportionalCandidateRecord:
    """比例代表候補者データ."""

    name: str
    party_name: str
    block_name: str
    list_order: int
    smd_result: str  # "当"/"落"/""
    loss_ratio: float | None
    is_elected: bool


@dataclass
class ProportionalBlockResult:
    """比例ブロック単位の結果."""

    block_name: str
    party_name: str
    votes: int
    winners_count: int
    candidates: list[ProportionalCandidateRecord]


@dataclass
class ProportionalElectionInfo:
    """比例代表選挙の基本情報."""

    election_number: int
    election_date: date
