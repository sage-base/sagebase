"""記名投票による個人データ上書きUseCaseのテスト."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.override_individual_judge_dto import (
    IndividualVoteInputItem,
    OverrideIndividualJudgeRequestDTO,
)
from src.application.usecases.override_individual_judge_usecase import (
    OverrideIndividualJudgeUseCase,
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


class TestOverrideIndividualJudgeUseCase:
    """記名投票上書きUseCaseのテストケース."""

    @pytest.fixture
    def mock_proposal_judge_repo(self):
        return AsyncMock(spec=ProposalJudgeRepository)

    @pytest.fixture
    def mock_group_judge_repo(self):
        return AsyncMock(spec=ProposalParliamentaryGroupJudgeRepository)

    @pytest.fixture
    def mock_politician_repo(self):
        return AsyncMock(spec=PoliticianRepository)

    @pytest.fixture
    def mock_membership_repo(self):
        return AsyncMock(spec=ParliamentaryGroupMembershipRepository)

    @pytest.fixture
    def mock_pg_repo(self):
        return AsyncMock(spec=ParliamentaryGroupRepository)

    @pytest.fixture
    def mock_proposal_repo(self):
        return AsyncMock(spec=ProposalRepository)

    @pytest.fixture
    def mock_meeting_repo(self):
        return AsyncMock(spec=MeetingRepository)

    @pytest.fixture
    def mock_deliberation_repo(self):
        mock = AsyncMock(spec=ProposalDeliberationRepository)
        mock.get_by_proposal_id.return_value = []
        return mock

    @pytest.fixture
    def use_case(
        self,
        mock_proposal_judge_repo,
        mock_group_judge_repo,
        mock_politician_repo,
        mock_membership_repo,
        mock_pg_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        mock_deliberation_repo,
    ):
        return OverrideIndividualJudgeUseCase(
            proposal_judge_repository=mock_proposal_judge_repo,
            group_judge_repository=mock_group_judge_repo,
            politician_repository=mock_politician_repo,
            membership_repository=mock_membership_repo,
            parliamentary_group_repository=mock_pg_repo,
            proposal_repository=mock_proposal_repo,
            meeting_repository=mock_meeting_repo,
            deliberation_repository=mock_deliberation_repo,
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
        ]

    @pytest.fixture
    def sample_pg(self):
        return ParliamentaryGroup(
            id=10,
            name="テスト会派",
            governing_body_id=1,
        )

    def _setup_meeting_date(
        self,
        mock_proposal_repo,
        mock_meeting_repo,
        sample_proposal,
        sample_meeting,
    ):
        mock_proposal_repo.get_by_id.return_value = sample_proposal
        mock_meeting_repo.get_by_id.return_value = sample_meeting

    def _setup_common_mocks(
        self,
        mock_group_judge_repo,
        mock_pg_repo,
        mock_membership_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        mock_proposal_judge_repo,
        sample_group_judge,
        sample_pg,
        sample_memberships,
        sample_proposal,
        sample_meeting,
        existing_judges=None,
    ):
        """共通のモック設定をまとめるヘルパー."""
        mock_group_judge_repo.get_by_proposal.return_value = [sample_group_judge]
        mock_pg_repo.get_by_id.return_value = sample_pg
        mock_membership_repo.get_active_by_group.return_value = sample_memberships
        self._setup_meeting_date(
            mock_proposal_repo, mock_meeting_repo, sample_proposal, sample_meeting
        )
        mock_proposal_judge_repo.get_by_proposal.return_value = (
            existing_judges if existing_judges is not None else []
        )

    @pytest.mark.asyncio
    async def test_override_creates_new_judges(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_pg_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        sample_group_judge,
        sample_proposal,
        sample_meeting,
        sample_memberships,
        sample_pg,
    ):
        self._setup_common_mocks(
            mock_group_judge_repo,
            mock_pg_repo,
            mock_membership_repo,
            mock_proposal_repo,
            mock_meeting_repo,
            mock_proposal_judge_repo,
            sample_group_judge,
            sample_pg,
            sample_memberships,
            sample_proposal,
            sample_meeting,
        )
        mock_proposal_judge_repo.bulk_create.return_value = []

        request = OverrideIndividualJudgeRequestDTO(
            proposal_id=100,
            votes=[
                IndividualVoteInputItem(politician_id=501, approve="賛成"),
                IndividualVoteInputItem(politician_id=502, approve="反対"),
            ],
        )

        result = await use_case.execute(request)

        assert result.success is True
        assert result.judges_created == 2
        assert result.judges_updated == 0
        mock_proposal_judge_repo.bulk_create.assert_called_once()
        created = mock_proposal_judge_repo.bulk_create.call_args[0][0]
        assert all(
            j.source_type == ProposalJudge.SOURCE_TYPE_ROLL_CALL for j in created
        )

    @pytest.mark.asyncio
    async def test_override_updates_existing_judges(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_pg_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        sample_group_judge,
        sample_proposal,
        sample_meeting,
        sample_memberships,
        sample_pg,
    ):
        existing_judge = ProposalJudge(
            id=10,
            proposal_id=100,
            politician_id=501,
            approve="賛成",
            source_type=ProposalJudge.SOURCE_TYPE_GROUP_EXPANSION,
            source_group_judge_id=1,
        )
        self._setup_common_mocks(
            mock_group_judge_repo,
            mock_pg_repo,
            mock_membership_repo,
            mock_proposal_repo,
            mock_meeting_repo,
            mock_proposal_judge_repo,
            sample_group_judge,
            sample_pg,
            sample_memberships,
            sample_proposal,
            sample_meeting,
            existing_judges=[existing_judge],
        )
        mock_proposal_judge_repo.bulk_update.return_value = []

        request = OverrideIndividualJudgeRequestDTO(
            proposal_id=100,
            votes=[IndividualVoteInputItem(politician_id=501, approve="反対")],
        )

        result = await use_case.execute(request)

        assert result.success is True
        assert result.judges_updated == 1
        assert result.judges_created == 0
        mock_proposal_judge_repo.bulk_update.assert_called_once()
        updated = mock_proposal_judge_repo.bulk_update.call_args[0][0]
        assert updated[0].approve == "反対"
        assert updated[0].source_type == ProposalJudge.SOURCE_TYPE_ROLL_CALL

    @pytest.mark.asyncio
    async def test_defection_detected_when_vote_differs(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_pg_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        mock_politician_repo,
        sample_group_judge,
        sample_proposal,
        sample_meeting,
        sample_memberships,
        sample_pg,
    ):
        self._setup_common_mocks(
            mock_group_judge_repo,
            mock_pg_repo,
            mock_membership_repo,
            mock_proposal_repo,
            mock_meeting_repo,
            mock_proposal_judge_repo,
            sample_group_judge,
            sample_pg,
            sample_memberships,
            sample_proposal,
            sample_meeting,
        )
        mock_proposal_judge_repo.bulk_create.return_value = []
        mock_politician_repo.get_by_id.return_value = Politician(
            id=501, name="テスト太郎", prefecture="東京都", district="1区"
        )

        request = OverrideIndividualJudgeRequestDTO(
            proposal_id=100,
            votes=[IndividualVoteInputItem(politician_id=501, approve="反対")],
        )

        result = await use_case.execute(request)

        assert result.success is True
        assert len(result.defections) == 1
        assert result.defections[0].individual_vote == "反対"
        assert result.defections[0].group_judgment == "賛成"
        assert result.defections[0].politician_name == "テスト太郎"

    @pytest.mark.asyncio
    async def test_no_defection_when_vote_matches(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_pg_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        sample_group_judge,
        sample_proposal,
        sample_meeting,
        sample_memberships,
        sample_pg,
    ):
        self._setup_common_mocks(
            mock_group_judge_repo,
            mock_pg_repo,
            mock_membership_repo,
            mock_proposal_repo,
            mock_meeting_repo,
            mock_proposal_judge_repo,
            sample_group_judge,
            sample_pg,
            sample_memberships,
            sample_proposal,
            sample_meeting,
        )
        mock_proposal_judge_repo.bulk_create.return_value = []

        request = OverrideIndividualJudgeRequestDTO(
            proposal_id=100,
            votes=[IndividualVoteInputItem(politician_id=501, approve="賛成")],
        )

        result = await use_case.execute(request)

        assert result.success is True
        assert len(result.defections) == 0

    @pytest.mark.asyncio
    async def test_defection_with_abstain(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_pg_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        mock_politician_repo,
        sample_group_judge,
        sample_proposal,
        sample_meeting,
        sample_memberships,
        sample_pg,
    ):
        self._setup_common_mocks(
            mock_group_judge_repo,
            mock_pg_repo,
            mock_membership_repo,
            mock_proposal_repo,
            mock_meeting_repo,
            mock_proposal_judge_repo,
            sample_group_judge,
            sample_pg,
            sample_memberships,
            sample_proposal,
            sample_meeting,
        )
        mock_proposal_judge_repo.bulk_create.return_value = []
        mock_politician_repo.get_by_id.return_value = Politician(
            id=501, name="テスト太郎", prefecture="東京都", district="1区"
        )

        request = OverrideIndividualJudgeRequestDTO(
            proposal_id=100,
            votes=[IndividualVoteInputItem(politician_id=501, approve="棄権")],
        )

        result = await use_case.execute(request)

        assert result.success is True
        assert len(result.defections) == 1
        assert result.defections[0].individual_vote == "棄権"
        assert result.defections[0].group_judgment == "賛成"

    @pytest.mark.asyncio
    async def test_source_group_judge_id_preserved(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_pg_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        sample_group_judge,
        sample_proposal,
        sample_meeting,
        sample_memberships,
        sample_pg,
    ):
        existing_judge = ProposalJudge(
            id=10,
            proposal_id=100,
            politician_id=501,
            approve="賛成",
            source_type=ProposalJudge.SOURCE_TYPE_GROUP_EXPANSION,
            source_group_judge_id=1,
        )
        self._setup_common_mocks(
            mock_group_judge_repo,
            mock_pg_repo,
            mock_membership_repo,
            mock_proposal_repo,
            mock_meeting_repo,
            mock_proposal_judge_repo,
            sample_group_judge,
            sample_pg,
            sample_memberships,
            sample_proposal,
            sample_meeting,
            existing_judges=[existing_judge],
        )
        mock_proposal_judge_repo.bulk_update.return_value = []

        request = OverrideIndividualJudgeRequestDTO(
            proposal_id=100,
            votes=[IndividualVoteInputItem(politician_id=501, approve="反対")],
        )

        await use_case.execute(request)

        updated = mock_proposal_judge_repo.bulk_update.call_args[0][0]
        assert updated[0].source_group_judge_id == 1

    @pytest.mark.asyncio
    async def test_is_defection_set_correctly(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_pg_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        sample_group_judge,
        sample_proposal,
        sample_meeting,
        sample_memberships,
        sample_pg,
    ):
        self._setup_common_mocks(
            mock_group_judge_repo,
            mock_pg_repo,
            mock_membership_repo,
            mock_proposal_repo,
            mock_meeting_repo,
            mock_proposal_judge_repo,
            sample_group_judge,
            sample_pg,
            sample_memberships,
            sample_proposal,
            sample_meeting,
        )
        mock_proposal_judge_repo.bulk_create.return_value = []

        request = OverrideIndividualJudgeRequestDTO(
            proposal_id=100,
            votes=[
                IndividualVoteInputItem(politician_id=501, approve="賛成"),
                IndividualVoteInputItem(politician_id=502, approve="反対"),
            ],
        )

        await use_case.execute(request)

        created = mock_proposal_judge_repo.bulk_create.call_args[0][0]
        judge_501 = next(j for j in created if j.politician_id == 501)
        judge_502 = next(j for j in created if j.politician_id == 502)
        assert judge_501.is_defection is False
        assert judge_502.is_defection is True

    def test_parse_csv_valid(self):
        csv_content = "501,賛成\n502,反対\n503,棄権\n"
        items = OverrideIndividualJudgeUseCase.parse_csv(csv_content)
        assert len(items) == 3
        assert items[0].politician_id == 501
        assert items[0].approve == "賛成"
        assert items[1].politician_id == 502
        assert items[1].approve == "反対"
        assert items[2].politician_id == 503
        assert items[2].approve == "棄権"

    def test_parse_csv_invalid_judgment(self):
        csv_content = "501,無効な値\n"
        with pytest.raises(ValueError, match="不正な賛否値です"):
            OverrideIndividualJudgeUseCase.parse_csv(csv_content)

    @pytest.mark.asyncio
    async def test_no_group_judgment_defection_is_none(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        sample_proposal,
        sample_meeting,
    ):
        mock_group_judge_repo.get_by_proposal.return_value = []
        self._setup_meeting_date(
            mock_proposal_repo, mock_meeting_repo, sample_proposal, sample_meeting
        )
        mock_proposal_judge_repo.get_by_proposal.return_value = []
        mock_proposal_judge_repo.bulk_create.return_value = []

        request = OverrideIndividualJudgeRequestDTO(
            proposal_id=100,
            votes=[IndividualVoteInputItem(politician_id=501, approve="賛成")],
        )

        await use_case.execute(request)

        created = mock_proposal_judge_repo.bulk_create.call_args[0][0]
        assert created[0].is_defection is None

    @pytest.mark.asyncio
    async def test_detect_defections_standalone(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_pg_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        mock_politician_repo,
        sample_group_judge,
        sample_proposal,
        sample_meeting,
        sample_memberships,
        sample_pg,
    ):
        mock_proposal_judge_repo.get_by_proposal.return_value = [
            ProposalJudge(
                id=10,
                proposal_id=100,
                politician_id=501,
                approve="反対",
                source_type=ProposalJudge.SOURCE_TYPE_ROLL_CALL,
            ),
            ProposalJudge(
                id=11,
                proposal_id=100,
                politician_id=502,
                approve="賛成",
                source_type=ProposalJudge.SOURCE_TYPE_ROLL_CALL,
            ),
        ]
        mock_group_judge_repo.get_by_proposal.return_value = [sample_group_judge]
        mock_pg_repo.get_by_id.return_value = sample_pg
        mock_membership_repo.get_active_by_group.return_value = sample_memberships
        self._setup_meeting_date(
            mock_proposal_repo, mock_meeting_repo, sample_proposal, sample_meeting
        )
        mock_politician_repo.get_by_id.return_value = Politician(
            id=501, name="テスト太郎", prefecture="東京都", district="1区"
        )

        defections = await use_case.detect_defections(100)

        assert len(defections) == 1
        assert defections[0].politician_id == 501
        assert defections[0].individual_vote == "反対"
        assert defections[0].group_judgment == "賛成"

    @pytest.mark.asyncio
    async def test_duplicate_politician_id_rejected(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
    ):
        """重複したpolitician_idが含まれる場合はエラーを返す."""
        request = OverrideIndividualJudgeRequestDTO(
            proposal_id=100,
            votes=[
                IndividualVoteInputItem(politician_id=501, approve="賛成"),
                IndividualVoteInputItem(politician_id=501, approve="反対"),
            ],
        )

        result = await use_case.execute(request)

        assert result.success is False
        assert any("重複したpolitician_id" in e for e in result.errors)
        mock_group_judge_repo.get_by_proposal.assert_not_called()

    @pytest.mark.asyncio
    async def test_mixed_create_and_update(
        self,
        use_case,
        mock_group_judge_repo,
        mock_proposal_judge_repo,
        mock_membership_repo,
        mock_pg_repo,
        mock_proposal_repo,
        mock_meeting_repo,
        sample_group_judge,
        sample_proposal,
        sample_meeting,
        sample_memberships,
        sample_pg,
    ):
        """既存と新規が混在する場合にbulk_createとbulk_updateの両方が呼ばれる."""
        existing_judge = ProposalJudge(
            id=10,
            proposal_id=100,
            politician_id=501,
            approve="賛成",
            source_type=ProposalJudge.SOURCE_TYPE_GROUP_EXPANSION,
        )
        self._setup_common_mocks(
            mock_group_judge_repo,
            mock_pg_repo,
            mock_membership_repo,
            mock_proposal_repo,
            mock_meeting_repo,
            mock_proposal_judge_repo,
            sample_group_judge,
            sample_pg,
            sample_memberships,
            sample_proposal,
            sample_meeting,
            existing_judges=[existing_judge],
        )
        mock_proposal_judge_repo.bulk_create.return_value = []
        mock_proposal_judge_repo.bulk_update.return_value = []

        request = OverrideIndividualJudgeRequestDTO(
            proposal_id=100,
            votes=[
                IndividualVoteInputItem(politician_id=501, approve="反対"),
                IndividualVoteInputItem(politician_id=502, approve="賛成"),
            ],
        )

        result = await use_case.execute(request)

        assert result.success is True
        assert result.judges_updated == 1
        assert result.judges_created == 1
        mock_proposal_judge_repo.bulk_update.assert_called_once()
        mock_proposal_judge_repo.bulk_create.assert_called_once()
