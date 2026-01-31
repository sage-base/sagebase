"""Tests for ProposalJudge entity."""

from src.domain.entities.proposal_judge import JudgmentType, ProposalJudge


class TestProposalJudge:
    """Test cases for ProposalJudge entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        judge = ProposalJudge(
            proposal_id=1,
            politician_id=2,
        )

        assert judge.proposal_id == 1
        assert judge.politician_id == 2
        assert judge.approve is None
        assert judge.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        judge = ProposalJudge(
            id=10,
            proposal_id=5,
            politician_id=3,
            approve="賛成",
        )

        assert judge.id == 10
        assert judge.proposal_id == 5
        assert judge.politician_id == 3
        assert judge.approve == "賛成"

    def test_is_approve(self) -> None:
        """Test is_approve method."""
        judge_approve = ProposalJudge(
            proposal_id=1,
            politician_id=2,
            approve=JudgmentType.APPROVE.value,
        )
        judge_oppose = ProposalJudge(
            proposal_id=1,
            politician_id=2,
            approve=JudgmentType.OPPOSE.value,
        )

        assert judge_approve.is_approve() is True
        assert judge_oppose.is_approve() is False

    def test_is_oppose(self) -> None:
        """Test is_oppose method."""
        judge_oppose = ProposalJudge(
            proposal_id=1,
            politician_id=2,
            approve=JudgmentType.OPPOSE.value,
        )
        judge_approve = ProposalJudge(
            proposal_id=1,
            politician_id=2,
            approve=JudgmentType.APPROVE.value,
        )

        assert judge_oppose.is_oppose() is True
        assert judge_approve.is_oppose() is False

    def test_is_abstain(self) -> None:
        """Test is_abstain method."""
        judge_abstain = ProposalJudge(
            proposal_id=1,
            politician_id=2,
            approve=JudgmentType.ABSTAIN.value,
        )
        judge_approve = ProposalJudge(
            proposal_id=1,
            politician_id=2,
            approve=JudgmentType.APPROVE.value,
        )

        assert judge_abstain.is_abstain() is True
        assert judge_approve.is_abstain() is False

    def test_is_absent(self) -> None:
        """Test is_absent method."""
        judge_absent = ProposalJudge(
            proposal_id=1,
            politician_id=2,
            approve=JudgmentType.ABSENT.value,
        )
        judge_approve = ProposalJudge(
            proposal_id=1,
            politician_id=2,
            approve=JudgmentType.APPROVE.value,
        )

        assert judge_absent.is_absent() is True
        assert judge_approve.is_absent() is False

    def test_str_representation_with_approve(self) -> None:
        """Test string representation with approve value."""
        judge = ProposalJudge(
            proposal_id=1,
            politician_id=5,
            approve="賛成",
        )

        assert str(judge) == "ProposalJudge: Politician 5 - 賛成"

    def test_str_representation_without_approve(self) -> None:
        """Test string representation without approve value."""
        judge = ProposalJudge(
            proposal_id=1,
            politician_id=3,
        )

        assert str(judge) == "ProposalJudge: Politician 3 - None"

    def test_judgment_type_enum_values(self) -> None:
        """Test JudgmentType enum values."""
        assert JudgmentType.APPROVE.value == "賛成"
        assert JudgmentType.OPPOSE.value == "反対"
        assert JudgmentType.ABSTAIN.value == "棄権"
        assert JudgmentType.ABSENT.value == "欠席"

    def test_all_judgment_methods_with_none(self) -> None:
        """Test all judgment methods when approve is None."""
        judge = ProposalJudge(
            proposal_id=1,
            politician_id=2,
            approve=None,
        )

        assert judge.is_approve() is False
        assert judge.is_oppose() is False
        assert judge.is_abstain() is False
        assert judge.is_absent() is False
