"""Tests for ProposalDeliberation entity."""

from src.domain.entities.proposal_deliberation import ProposalDeliberation


class TestProposalDeliberation:
    """Test cases for ProposalDeliberation entity."""

    def test_initialization_with_required_fields(self) -> None:
        entity = ProposalDeliberation(proposal_id=1, conference_id=10)

        assert entity.proposal_id == 1
        assert entity.conference_id == 10
        assert entity.meeting_id is None
        assert entity.stage is None
        assert entity.id is None

    def test_initialization_with_all_fields(self) -> None:
        entity = ProposalDeliberation(
            id=100,
            proposal_id=1,
            conference_id=10,
            meeting_id=50,
            stage="付託",
        )

        assert entity.id == 100
        assert entity.proposal_id == 1
        assert entity.conference_id == 10
        assert entity.meeting_id == 50
        assert entity.stage == "付託"

    def test_has_meeting_true(self) -> None:
        entity = ProposalDeliberation(proposal_id=1, conference_id=10, meeting_id=50)
        assert entity.has_meeting is True

    def test_has_meeting_false(self) -> None:
        entity = ProposalDeliberation(proposal_id=1, conference_id=10)
        assert entity.has_meeting is False

    def test_has_stage_true(self) -> None:
        entity = ProposalDeliberation(proposal_id=1, conference_id=10, stage="採決")
        assert entity.has_stage is True

    def test_has_stage_false(self) -> None:
        entity = ProposalDeliberation(proposal_id=1, conference_id=10)
        assert entity.has_stage is False

    def test_str_representation_without_stage(self) -> None:
        entity = ProposalDeliberation(proposal_id=1, conference_id=10)
        result = str(entity)
        assert "proposal=1" in result
        assert "conference=10" in result

    def test_str_representation_with_stage(self) -> None:
        entity = ProposalDeliberation(proposal_id=1, conference_id=10, stage="付託")
        result = str(entity)
        assert "proposal=1" in result
        assert "conference=10" in result
        assert "[付託]" in result

    def test_equality_by_id(self) -> None:
        entity1 = ProposalDeliberation(id=1, proposal_id=1, conference_id=10)
        entity2 = ProposalDeliberation(id=1, proposal_id=2, conference_id=20)
        assert entity1 == entity2

    def test_inequality_by_id(self) -> None:
        entity1 = ProposalDeliberation(id=1, proposal_id=1, conference_id=10)
        entity2 = ProposalDeliberation(id=2, proposal_id=1, conference_id=10)
        assert entity1 != entity2

    def test_inherits_base_entity(self) -> None:
        entity = ProposalDeliberation(proposal_id=1, conference_id=10)
        assert entity.created_at is None
        assert entity.updated_at is None
