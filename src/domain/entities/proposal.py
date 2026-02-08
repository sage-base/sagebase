"""Proposal entity module."""

from src.domain.entities.base import BaseEntity


class Proposal(BaseEntity):
    """議案を表すエンティティ."""

    def __init__(
        self,
        title: str,
        detail_url: str | None = None,
        status_url: str | None = None,
        votes_url: str | None = None,
        meeting_id: int | None = None,
        conference_id: int | None = None,
        proposal_category: str | None = None,
        proposal_type: str | None = None,
        governing_body_id: int | None = None,
        session_number: int | None = None,
        proposal_number: int | None = None,
        external_id: str | None = None,
        deliberation_status: str | None = None,
        deliberation_result: str | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.title = title
        self.detail_url = detail_url
        self.status_url = status_url
        self.votes_url = votes_url
        self.meeting_id = meeting_id
        self.conference_id = conference_id
        self.proposal_category = proposal_category
        self.proposal_type = proposal_type
        self.governing_body_id = governing_body_id
        self.session_number = session_number
        self.proposal_number = proposal_number
        self.external_id = external_id
        self.deliberation_status = deliberation_status
        self.deliberation_result = deliberation_result

    def __str__(self) -> str:
        identifier = f"ID:{self.id}"
        return f"Proposal {identifier}: {self.title[:50]}..."
