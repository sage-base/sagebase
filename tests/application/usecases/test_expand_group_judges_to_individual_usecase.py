"""会派賛否から個人投票データへの展開UseCaseのテスト."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.expand_group_judges_dto import ExpandGroupJudgesRequestDTO
from src.application.usecases.expand_group_judges_to_individual_usecase import (
    ExpandGroupJudgesToIndividualUseCase,
)
from src.domain.entities.meeting import Meeting
from src.domain.entities.parliamentary_group_membership import (
    ParliamentaryGroupMembership,
)
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


class TestExpandGroupJudgesToIndividualUseCase:
    """会派賛否展開UseCaseのテストケース."""

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
        mock = AsyncMock(spec=ProposalDeliberationRepository)
        mock.get_by_proposal_id.return_value = []
        return mock

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

    @pytest.fixture
    def sample_group_judge(self):
        return ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=100,
            judgment="賛成",
            judge_type=JudgeType.PARLIAMENTARY_GROUP,
            parliamentary_group_ids=[10],
        )

    @pytest.fixture
    def sample_proposal(self):
        return Proposal(
            id=100,
            title="テスト議案",
            meeting_id=200,
        )

    @pytest.fixture
    def sample_meeting(self):
        return Meeting(
            id=200,
            conference_id=300,
            date=date(2025, 6, 15),
        )

    @pytest.fixture
    def sample_memberships(self):
        return [
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
            ParliamentaryGroupMembership(
                id=3,
                politician_id=503,
                parliamentary_group_id=10,
                start_date=date(2024, 1, 1),
            ),
        ]

    @pytest.mark.asyncio
    async def test_expand_creates_individual_judges(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        sample_group_judge,
        sample_proposal,
        sample_meeting,
        sample_memberships,
    ):
        """1つのgroup judgeから3人分のProposalJudgeが作成される."""
        mock_group_judge_repo.get_by_proposal.return_value = [sample_group_judge]
        mock_proposal_repo.get_by_id.return_value = sample_proposal
        mock_meeting_repo.get_by_id.return_value = sample_meeting
        mock_membership_repo.get_active_by_group.return_value = sample_memberships
        mock_proposal_judge_repo.get_by_proposal_and_politician.return_value = None
        mock_proposal_judge_repo.bulk_create.return_value = []

        request = ExpandGroupJudgesRequestDTO(proposal_id=100)
        result = await use_case.execute(request)

        assert result.success is True
        assert result.total_group_judges_processed == 1
        assert result.total_members_found == 3
        assert result.total_judges_created == 3

        mock_proposal_judge_repo.bulk_create.assert_called_once()
        created_judges = mock_proposal_judge_repo.bulk_create.call_args[0][0]
        assert len(created_judges) == 3
        politician_ids = {j.politician_id for j in created_judges}
        assert politician_ids == {501, 502, 503}

    @pytest.mark.asyncio
    async def test_skip_when_no_meeting_id(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_repo,
    ):
        """meeting_idがない場合にスキップされる."""
        group_judge = ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=100,
            judgment="賛成",
            judge_type=JudgeType.PARLIAMENTARY_GROUP,
            parliamentary_group_ids=[10],
        )
        proposal_no_meeting = Proposal(
            id=100,
            title="テスト議案",
            meeting_id=None,
        )

        mock_group_judge_repo.get_by_proposal.return_value = [group_judge]
        mock_proposal_repo.get_by_id.return_value = proposal_no_meeting

        request = ExpandGroupJudgesRequestDTO(proposal_id=100)
        result = await use_case.execute(request)

        assert result.success is True
        assert result.skipped_no_meeting_date == 1
        assert result.total_group_judges_processed == 0

    @pytest.mark.asyncio
    async def test_skip_when_meeting_date_is_none(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_repo,
        mock_meeting_repo,
    ):
        """Meeting.dateがNoneの場合にスキップされる."""
        group_judge = ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=100,
            judgment="賛成",
            judge_type=JudgeType.PARLIAMENTARY_GROUP,
            parliamentary_group_ids=[10],
        )
        proposal = Proposal(id=100, title="テスト議案", meeting_id=200)
        meeting_no_date = Meeting(id=200, conference_id=300, date=None)

        mock_group_judge_repo.get_by_proposal.return_value = [group_judge]
        mock_proposal_repo.get_by_id.return_value = proposal
        mock_meeting_repo.get_by_id.return_value = meeting_no_date

        request = ExpandGroupJudgesRequestDTO(proposal_id=100)
        result = await use_case.execute(request)

        assert result.success is True
        assert result.skipped_no_meeting_date == 1
        assert result.total_group_judges_processed == 0

    @pytest.mark.asyncio
    async def test_skip_existing_without_force_overwrite(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        sample_group_judge,
        sample_proposal,
        sample_meeting,
    ):
        """既存個人投票あり & force_overwrite=False → スキップ."""
        mock_group_judge_repo.get_by_proposal.return_value = [sample_group_judge]
        mock_proposal_repo.get_by_id.return_value = sample_proposal
        mock_meeting_repo.get_by_id.return_value = sample_meeting
        mock_membership_repo.get_active_by_group.return_value = [
            ParliamentaryGroupMembership(
                id=1,
                politician_id=501,
                parliamentary_group_id=10,
                start_date=date(2024, 1, 1),
            ),
        ]
        existing_judge = ProposalJudge(
            id=99, proposal_id=100, politician_id=501, approve="反対"
        )
        mock_proposal_judge_repo.get_by_proposal_and_politician.return_value = (
            existing_judge
        )

        request = ExpandGroupJudgesRequestDTO(proposal_id=100, force_overwrite=False)
        result = await use_case.execute(request)

        assert result.success is True
        assert result.total_judges_skipped == 1
        assert result.total_judges_created == 0
        mock_proposal_judge_repo.update.assert_not_called()
        mock_proposal_judge_repo.bulk_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_overwrite_existing_with_force_overwrite(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        sample_group_judge,
        sample_proposal,
        sample_meeting,
    ):
        """既存個人投票あり & force_overwrite=True → 上書き."""
        mock_group_judge_repo.get_by_proposal.return_value = [sample_group_judge]
        mock_proposal_repo.get_by_id.return_value = sample_proposal
        mock_meeting_repo.get_by_id.return_value = sample_meeting
        mock_membership_repo.get_active_by_group.return_value = [
            ParliamentaryGroupMembership(
                id=1,
                politician_id=501,
                parliamentary_group_id=10,
                start_date=date(2024, 1, 1),
            ),
        ]
        existing_judge = ProposalJudge(
            id=99, proposal_id=100, politician_id=501, approve="反対"
        )
        mock_proposal_judge_repo.get_by_proposal_and_politician.return_value = (
            existing_judge
        )
        mock_proposal_judge_repo.update.return_value = existing_judge

        request = ExpandGroupJudgesRequestDTO(proposal_id=100, force_overwrite=True)
        result = await use_case.execute(request)

        assert result.success is True
        assert result.total_judges_overwritten == 1
        assert result.total_judges_created == 0
        mock_proposal_judge_repo.update.assert_called_once()
        updated = mock_proposal_judge_repo.update.call_args[0][0]
        assert updated.approve == "賛成"
        assert updated.source_type == ProposalJudge.SOURCE_TYPE_GROUP_EXPANSION
        assert updated.source_group_judge_id == 1

    @pytest.mark.asyncio
    async def test_multiple_parliamentary_groups(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        sample_proposal,
        sample_meeting,
    ):
        """複数parliamentary_group_idsの全メンバーが展開される."""
        group_judge = ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=100,
            judgment="反対",
            judge_type=JudgeType.PARLIAMENTARY_GROUP,
            parliamentary_group_ids=[10, 20],
        )

        mock_group_judge_repo.get_by_proposal.return_value = [group_judge]
        mock_proposal_repo.get_by_id.return_value = sample_proposal
        mock_meeting_repo.get_by_id.return_value = sample_meeting
        mock_proposal_judge_repo.get_by_proposal_and_politician.return_value = None
        mock_proposal_judge_repo.bulk_create.return_value = []

        group10_members = [
            ParliamentaryGroupMembership(
                id=1,
                politician_id=501,
                parliamentary_group_id=10,
                start_date=date(2024, 1, 1),
            ),
        ]
        group20_members = [
            ParliamentaryGroupMembership(
                id=2,
                politician_id=502,
                parliamentary_group_id=20,
                start_date=date(2024, 1, 1),
            ),
            ParliamentaryGroupMembership(
                id=3,
                politician_id=503,
                parliamentary_group_id=20,
                start_date=date(2024, 1, 1),
            ),
        ]
        mock_membership_repo.get_active_by_group.side_effect = [
            group10_members,
            group20_members,
        ]

        request = ExpandGroupJudgesRequestDTO(proposal_id=100)
        result = await use_case.execute(request)

        assert result.success is True
        assert result.total_members_found == 3
        assert result.total_judges_created == 3

        created_judges = mock_proposal_judge_repo.bulk_create.call_args[0][0]
        politician_ids = {j.politician_id for j in created_judges}
        assert politician_ids == {501, 502, 503}

    @pytest.mark.asyncio
    async def test_deduplication_across_groups(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        sample_proposal,
        sample_meeting,
    ):
        """同一politicianが複数グループにいる場合に重複排除される."""
        group_judge = ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=100,
            judgment="賛成",
            judge_type=JudgeType.PARLIAMENTARY_GROUP,
            parliamentary_group_ids=[10, 20],
        )

        mock_group_judge_repo.get_by_proposal.return_value = [group_judge]
        mock_proposal_repo.get_by_id.return_value = sample_proposal
        mock_meeting_repo.get_by_id.return_value = sample_meeting
        mock_proposal_judge_repo.get_by_proposal_and_politician.return_value = None
        mock_proposal_judge_repo.bulk_create.return_value = []

        group10_members = [
            ParliamentaryGroupMembership(
                id=1,
                politician_id=501,
                parliamentary_group_id=10,
                start_date=date(2024, 1, 1),
            ),
        ]
        group20_members = [
            ParliamentaryGroupMembership(
                id=2,
                politician_id=501,
                parliamentary_group_id=20,
                start_date=date(2024, 1, 1),
            ),
        ]
        mock_membership_repo.get_active_by_group.side_effect = [
            group10_members,
            group20_members,
        ]

        request = ExpandGroupJudgesRequestDTO(proposal_id=100)
        result = await use_case.execute(request)

        assert result.success is True
        assert result.total_members_found == 1
        assert result.total_judges_created == 1

        created_judges = mock_proposal_judge_repo.bulk_create.call_args[0][0]
        assert len(created_judges) == 1
        assert created_judges[0].politician_id == 501

    @pytest.mark.asyncio
    async def test_zero_members_no_error(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        sample_group_judge,
        sample_proposal,
        sample_meeting,
    ):
        """メンバー0人の場合にエラーなく0件作成."""
        mock_group_judge_repo.get_by_proposal.return_value = [sample_group_judge]
        mock_proposal_repo.get_by_id.return_value = sample_proposal
        mock_meeting_repo.get_by_id.return_value = sample_meeting
        mock_membership_repo.get_active_by_group.return_value = []

        request = ExpandGroupJudgesRequestDTO(proposal_id=100)
        result = await use_case.execute(request)

        assert result.success is True
        assert result.total_members_found == 0
        assert result.total_judges_created == 0
        mock_proposal_judge_repo.bulk_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_voted_date_fallback_when_no_meeting(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_proposal_repo,
    ):
        """meeting未紐付けでもvoted_dateで展開成功."""
        group_judge = ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=100,
            judgment="賛成",
            judge_type=JudgeType.PARLIAMENTARY_GROUP,
            parliamentary_group_ids=[10],
        )
        proposal_with_voted_date = Proposal(
            id=100,
            title="テスト議案",
            meeting_id=None,
            voted_date=date(2025, 6, 15),
        )

        mock_group_judge_repo.get_by_proposal.return_value = [group_judge]
        mock_proposal_repo.get_by_id.return_value = proposal_with_voted_date
        mock_membership_repo.get_active_by_group.return_value = [
            ParliamentaryGroupMembership(
                id=1,
                politician_id=501,
                parliamentary_group_id=10,
                start_date=date(2024, 1, 1),
            ),
        ]
        mock_proposal_judge_repo.get_by_proposal_and_politician.return_value = None
        mock_proposal_judge_repo.bulk_create.return_value = []

        request = ExpandGroupJudgesRequestDTO(proposal_id=100)
        result = await use_case.execute(request)

        assert result.success is True
        assert result.skipped_no_meeting_date == 0
        assert result.total_group_judges_processed == 1
        assert result.total_judges_created == 1

    @pytest.mark.asyncio
    async def test_meeting_date_preferred_over_voted_date(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_proposal_repo,
        mock_meeting_repo,
    ):
        """meeting日付がある場合はvoted_dateより優先される."""
        group_judge = ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=100,
            judgment="賛成",
            judge_type=JudgeType.PARLIAMENTARY_GROUP,
            parliamentary_group_ids=[10],
        )
        proposal = Proposal(
            id=100,
            title="テスト議案",
            meeting_id=200,
            voted_date=date(2025, 1, 1),
        )
        meeting = Meeting(
            id=200,
            conference_id=300,
            date=date(2025, 6, 15),
        )

        mock_group_judge_repo.get_by_proposal.return_value = [group_judge]
        mock_proposal_repo.get_by_id.return_value = proposal
        mock_meeting_repo.get_by_id.return_value = meeting
        mock_membership_repo.get_active_by_group.return_value = [
            ParliamentaryGroupMembership(
                id=1,
                politician_id=501,
                parliamentary_group_id=10,
                start_date=date(2024, 1, 1),
            ),
        ]
        mock_proposal_judge_repo.get_by_proposal_and_politician.return_value = None
        mock_proposal_judge_repo.bulk_create.return_value = []

        request = ExpandGroupJudgesRequestDTO(proposal_id=100)
        result = await use_case.execute(request)

        assert result.success is True
        assert result.total_judges_created == 1
        # meeting日付(2025-06-15)が使われることを確認（voted_dateではなく）
        mock_membership_repo.get_active_by_group.assert_called_once_with(
            10, as_of_date=date(2025, 6, 15)
        )

    @pytest.mark.asyncio
    async def test_source_fields_set_correctly(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        sample_group_judge,
        sample_proposal,
        sample_meeting,
    ):
        """source_typeとsource_group_judge_idが正しくセットされる."""
        mock_group_judge_repo.get_by_proposal.return_value = [sample_group_judge]
        mock_proposal_repo.get_by_id.return_value = sample_proposal
        mock_meeting_repo.get_by_id.return_value = sample_meeting
        mock_membership_repo.get_active_by_group.return_value = [
            ParliamentaryGroupMembership(
                id=1,
                politician_id=501,
                parliamentary_group_id=10,
                start_date=date(2024, 1, 1),
            ),
        ]
        mock_proposal_judge_repo.get_by_proposal_and_politician.return_value = None
        mock_proposal_judge_repo.bulk_create.return_value = []

        request = ExpandGroupJudgesRequestDTO(proposal_id=100)
        await use_case.execute(request)

        created_judges = mock_proposal_judge_repo.bulk_create.call_args[0][0]
        assert len(created_judges) == 1
        judge = created_judges[0]
        assert judge.source_type == ProposalJudge.SOURCE_TYPE_GROUP_EXPANSION
        assert judge.source_group_judge_id == 1
        assert judge.approve == "賛成"
        assert judge.proposal_id == 100
        assert judge.politician_id == 501
