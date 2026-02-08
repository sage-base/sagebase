"""LLM-related type definitions."""

from typing import TypedDict


class LLMMatchResult(TypedDict):
    """Result from LLM matching operations."""

    matched: bool
    confidence: float
    reason: str
    matched_id: int | None
    metadata: dict[str, str]


class LLMExtractResult(TypedDict):
    """Result from LLM extraction operations."""

    success: bool
    extracted_data: list[dict[str, str]]
    error: str | None
    metadata: dict[str, str]


class LLMSpeakerMatchContext(TypedDict):
    """Context for LLM speaker matching."""

    speaker_name: str
    normalized_name: str
    party_affiliation: str | None
    position: str | None
    meeting_date: str
    candidates: list[dict[str, str]]


class LLMPoliticianMatchContext(TypedDict):
    """Context for LLM politician matching."""

    name: str
    party: str | None
    prefecture: str | None
    electoral_district: str | None
    candidates: list[dict[str, str]]
