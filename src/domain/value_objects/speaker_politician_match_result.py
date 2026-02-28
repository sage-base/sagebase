"""発言者→政治家マッチング結果の Value Object."""

from dataclasses import dataclass
from enum import Enum


class MatchMethod(Enum):
    """マッチング方法."""

    EXACT_NAME = "exact_name"
    YOMI = "yomi"
    SURNAME_ONLY = "surname_only"
    BAML = "baml"
    NONE = "none"


@dataclass(frozen=True)
class PoliticianCandidate:
    """マッチング候補の政治家."""

    politician_id: int
    name: str
    furigana: str | None = None
    party_name: str | None = None


@dataclass(frozen=True)
class SpeakerPoliticianMatchResult:
    """発言者→政治家マッチング結果."""

    speaker_id: int
    speaker_name: str
    politician_id: int | None
    politician_name: str | None
    confidence: float
    match_method: MatchMethod
