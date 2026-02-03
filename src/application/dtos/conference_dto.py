"""Conference-related DTOs."""

from dataclasses import dataclass
from datetime import date


@dataclass
class ConferenceDTO:
    """DTO for conference data."""

    id: int
    name: str
    governing_body_id: int
    governing_body_name: str
    type: str | None
    members_introduction_url: str | None
    total_members: int | None = None
    active_groups: int | None = None


@dataclass
class ExtractedConferenceMemberDTO:
    """DTO for extracted conference member."""

    name: str
    conference_id: int
    party_name: str | None = None
    role: str | None = None
    profile_url: str | None = None


@dataclass
class CreateAffiliationDTO:
    """DTO for creating politician affiliation."""

    politician_id: int
    conference_id: int
    start_date: date
    end_date: date | None = None
    role: str | None = None


@dataclass
class AffiliationDTO:
    """DTO for politician affiliation data."""

    id: int
    politician_id: int
    politician_name: str
    conference_id: int
    conference_name: str
    start_date: date
    end_date: date | None
    role: str | None
