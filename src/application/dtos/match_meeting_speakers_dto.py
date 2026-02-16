"""会議発言者マッチングの入出力DTO."""

from dataclasses import dataclass, field

from src.domain.value_objects.speaker_politician_match_result import MatchMethod


@dataclass
class MatchMeetingSpeakersInputDTO:
    """会議発言者マッチングの入力DTO."""

    meeting_id: int
    confidence_threshold: float = 0.8


@dataclass
class SpeakerMatchResultDTO:
    """発言者1件のマッチング結果DTO."""

    speaker_id: int
    speaker_name: str
    politician_id: int | None
    politician_name: str | None
    confidence: float
    match_method: MatchMethod
    updated: bool


@dataclass
class MatchMeetingSpeakersOutputDTO:
    """会議発言者マッチングの出力DTO."""

    success: bool
    message: str
    total_speakers: int = 0
    matched_count: int = 0
    skipped_count: int = 0
    results: list[SpeakerMatchResultDTO] = field(default_factory=list)
