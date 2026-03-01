"""広域マッチング（ConferenceMember非依存）の入出力DTO."""

from dataclasses import dataclass, field

from src.application.dtos.match_meeting_speakers_dto import SpeakerMatchResultDTO


@dataclass
class WideMatchSpeakersInputDTO:
    """広域マッチングの入力DTO."""

    meeting_id: int
    auto_match_threshold: float = 0.9
    review_threshold: float = 0.7
    enable_baml_fallback: bool = False


@dataclass
class WideMatchSpeakersOutputDTO:
    """広域マッチングの出力DTO."""

    success: bool
    message: str
    total_speakers: int = 0
    auto_matched_count: int = 0
    review_matched_count: int = 0
    skipped_count: int = 0
    non_politician_count: int = 0
    baml_matched_count: int = 0
    results: list[SpeakerMatchResultDTO] = field(default_factory=list)
