"""会派賛否展開プレビューのテスト."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.application.usecases.expand_group_judges_to_individual_usecase import (
    ExpandGroupJudgesToIndividualUseCase,
)
from src.domain.entities.meeting import Meeting
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.parliamentary_group_membership import (
    ParliamentaryGroupMembership,
)
from src.domain.entities.politician import Politician
from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_judge import ProposalJudge
from src.domain.entities.proposal_parliamentary_group_judge import (
    ProposalParliamentaryGroupJudge,
)
from src.domain.repositories.meeting_repository import MeetingRepository
from src.domain.repositories.parliamentary_group_membership_repository import (
    ParliamentaryGroupMembershipRepository,
)
from src.domain.repositories.parliamentary_group_repository import (
    ParliamentaryGroupRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.proposal_deliberation_repository import (
    ProposalDeliberationRepository,
)
from src.domain.repositories.proposal_judge_repository import ProposalJudgeRepository
from src.domain.repositories.proposal_parliamentary_group_judge_repository import (
    ProposalParliamentaryGroupJudgeRepository,
)
from src.domain.repositories.proposal_repository import ProposalRepository
from src.domain.value_objects.judge_type import JudgeType


class TestExpandGroupJudgesPreview:
    """会派賛否展開プレビューのテストケース."""

    @pytest.fixture
    def mock_group_judge_repo(self):
        return AsyncMock(spec=ProposalParliamentaryGroupJudgeRepository)

    @pytest.fixture
    def mock_proposal_judge_repo(self):
        return AsyncMock(spec=ProposalJudgeRepository)

    @pytest.fixture
    def mock_membership_repo(self):
        return AsyncMock(spec=ParliamentaryGroupMembershipRepository)

    @pytest.fixture
    def mock_proposal_repo(self):
        return AsyncMock(spec=ProposalRepository)

    @pytest.fixture
    def mock_meeting_repo(self):
        return AsyncMock(spec=MeetingRepository)

    @pytest.fixture
    def mock_politician_repo(self):
        return AsyncMock(spec=PoliticianRepository)

    @pytest.fixture
    def mock_deliberation_repo(self):
        return AsyncMock(spec=ProposalDeliberationRepository)

    @pytest.fixture
    def mock_pg_repo(self):
        return AsyncMock(spec=ParliamentaryGroupRepository)

    @pytest.fixture
    def use_case(
        self,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        mock_politician_repo,
        mock_deliberation_repo,
        mock_pg_repo,
    ):
        return ExpandGroupJudgesToIndividualUseCase(
            group_judge_repository=mock_group_judge_repo,
            proposal_judge_repository=mock_proposal_judge_repo,
            membership_repository=mock_membership_repo,
            proposal_repository=mock_proposal_repo,
            meeting_repository=mock_meeting_repo,
            politician_repository=mock_politician_repo,
            deliberation_repository=mock_deliberation_repo,
            parliamentary_group_repository=mock_pg_repo,
        )

    @pytest.mark.asyncio
    async def test_preview_returns_members(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        mock_politician_repo,
        mock_deliberation_repo,
        mock_pg_repo,
    ):
        """正常系: メンバーリストが正しく返却される."""
        gj = ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=100,
            judgment="賛成",
            judge_type=JudgeType.PARLIAMENTARY_GROUP,
            parliamentary_group_ids=[10],
        )
        mock_group_judge_repo.get_by_id.return_value = gj
        mock_deliberation_repo.get_by_proposal_id.return_value = []
        mock_proposal_repo.get_by_id.return_value = Proposal(
            id=100, title="テスト議案", meeting_id=200
        )
        mock_meeting_repo.get_by_id.return_value = Meeting(
            id=200, conference_id=300, date=date(2025, 6, 15)
        )
        mock_pg_repo.get_by_id.return_value = ParliamentaryGroup(
            id=10, name="テスト会派", governing_body_id=1
        )
        mock_membership_repo.get_active_by_group.return_value = [
            ParliamentaryGroupMembership(
                id=1,
                politician_id=501,
                parliamentary_group_id=10,
                start_date=date(2024, 1, 1),
            ),
            ParliamentaryGroupMembership(
                id=2,
                politician_id=502,
                parliamentary_group_id=10,
                start_date=date(2024, 1, 1),
            ),
        ]
        mock_politician_repo.get_by_id.side_effect = [
            Politician(id=501, name="議員A", prefecture="東京都", district="地区A"),
            Politician(id=502, name="議員B", prefecture="東京都", district="地区B"),
        ]
        mock_proposal_judge_repo.get_by_proposal_and_politician.return_value = None

        result = await use_case.preview([1])

        assert result.success is True
        assert len(result.items) == 1
        assert result.total_members == 2
        assert result.total_existing_votes == 0
        assert result.items[0].judgment == "賛成"
        assert result.items[0].parliamentary_group_names == ["テスト会派"]
        assert len(result.items[0].members) == 2

    @pytest.mark.asyncio
    async def test_preview_detects_existing_votes(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        mock_politician_repo,
        mock_deliberation_repo,
        mock_pg_repo,
    ):
        """既存投票あり: has_existing_vote=Trueのメンバーが検出される."""
        gj = ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=100,
            judgment="賛成",
            judge_type=JudgeType.PARLIAMENTARY_GROUP,
            parliamentary_group_ids=[10],
        )
        mock_group_judge_repo.get_by_id.return_value = gj
        mock_deliberation_repo.get_by_proposal_id.return_value = []
        mock_proposal_repo.get_by_id.return_value = Proposal(
            id=100, title="テスト議案", meeting_id=200
        )
        mock_meeting_repo.get_by_id.return_value = Meeting(
            id=200, conference_id=300, date=date(2025, 6, 15)
        )
        mock_pg_repo.get_by_id.return_value = ParliamentaryGroup(
            id=10, name="テスト会派", governing_body_id=1
        )
        mock_membership_repo.get_active_by_group.return_value = [
            ParliamentaryGroupMembership(
                id=1,
                politician_id=501,
                parliamentary_group_id=10,
                start_date=date(2024, 1, 1),
            ),
        ]
        mock_politician_repo.get_by_id.return_value = Politician(
            id=501, name="議員A", prefecture="東京都", district="地区A"
        )
        existing_judge = ProposalJudge(
            id=99, proposal_id=100, politician_id=501, approve="反対"
        )
        mock_proposal_judge_repo.get_by_proposal_and_politician.return_value = (
            existing_judge
        )

        result = await use_case.preview([1])

        assert result.success is True
        assert result.total_existing_votes == 1
        assert result.items[0].members[0].has_existing_vote is True

    @pytest.mark.asyncio
    async def test_preview_group_judge_not_found(
        self,
        use_case,
        mock_group_judge_repo,
    ):
        """会派賛否なし: エラーが返却される."""
        mock_group_judge_repo.get_by_id.return_value = None

        result = await use_case.preview([999])

        assert result.success is True
        assert len(result.items) == 0
        assert len(result.errors) == 1
        assert "999" in result.errors[0]

    @pytest.mark.asyncio
    async def test_preview_no_meeting_date(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_repo,
        mock_deliberation_repo,
        mock_pg_repo,
    ):
        """投票日なし: エラーが返却される."""
        gj = ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=100,
            judgment="賛成",
            judge_type=JudgeType.PARLIAMENTARY_GROUP,
            parliamentary_group_ids=[10],
        )
        mock_group_judge_repo.get_by_id.return_value = gj
        mock_deliberation_repo.get_by_proposal_id.return_value = []
        mock_proposal_repo.get_by_id.return_value = Proposal(
            id=100, title="テスト議案", meeting_id=None
        )
        mock_pg_repo.get_by_id.return_value = ParliamentaryGroup(
            id=10, name="テスト会派", governing_body_id=1
        )

        result = await use_case.preview([1])

        assert result.success is True
        assert len(result.items) == 1
        assert len(result.items[0].errors) == 1
        assert "投票日" in result.items[0].errors[0]

    @pytest.mark.asyncio
    async def test_preview_empty_ids(
        self,
        use_case,
    ):
        """空のIDリスト: 空のプレビューが返却される."""
        result = await use_case.preview([])

        assert result.success is True
        assert len(result.items) == 0
        assert result.total_members == 0
