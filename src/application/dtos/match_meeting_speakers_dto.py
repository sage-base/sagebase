"""会議発言者マッチングの入出力DTO."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.domain.services.speaker_classifier import SkipReason
from src.domain.value_objects.speaker_politician_match_result import MatchMethod


if TYPE_CHECKING:
    from src.domain.entities.speaker import Speaker


@dataclass
class MatchMeetingSpeakersInputDTO:
    """会議発言者マッチングの入力DTO."""

    meeting_id: int
    confidence_threshold: float = 0.8
    enable_baml_fallback: bool = False


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
    skip_reason: SkipReason | None = None

    @staticmethod
    def unmatched(speaker: Speaker) -> SpeakerMatchResultDTO:
        """未マッチSpeaker用のDTO生成ファクトリ."""
        return SpeakerMatchResultDTO(
            speaker_id=speaker.id,  # type: ignore[arg-type]
            speaker_name=speaker.name,
            politician_id=None,
            politician_name=None,
            confidence=0.0,
            match_method=MatchMethod.NONE,
            updated=False,
        )


@dataclass
class MatchMeetingSpeakersOutputDTO:
    """会議発言者マッチングの出力DTO."""

    success: bool
    message: str
    total_speakers: int = 0
    matched_count: int = 0
    skipped_count: int = 0
    baml_matched_count: int = 0
    non_politician_count: int = 0
    results: list[SpeakerMatchResultDTO] = field(default_factory=list)
