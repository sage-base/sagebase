"""ProposalPresenterの個人投票展開メソッドのテスト (Issue #1010)."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.dtos.expand_group_judges_dto import (
    ExpandGroupJudgesResultDTO,
    GroupJudgeExpansionSummary,
)
from src.application.dtos.proposal_parliamentary_group_judge_dto import (
    ProposalParliamentaryGroupJudgeDTO,
)
from src.domain.entities.meeting import Meeting
from src.domain.entities.parliamentary_group_membership import (
    ParliamentaryGroupMembership,
)
from src.domain.entities.politician import Politician
from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_judge import ProposalJudge


@pytest.fixture
def presenter():
    """ProposalPresenterのインスタンス（展開テスト用）."""
    with (
        patch(
            "src.interfaces.web.streamlit.presenters.proposal_presenter.RepositoryAdapter"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.proposal_presenter.SessionManager"
        ) as mock_session,
        patch(
            "src.interfaces.web.streamlit.presenters.proposal_presenter.ManageProposalsUseCase"
        ),
        patch("src.interfaces.web.streamlit.presenters.base.Container"),
    ):
        mock_session_instance = MagicMock()
        mock_session_instance.get = MagicMock(return_value={})
        mock_session_instance.set = MagicMock()
        mock_session.return_value = mock_session_instance

        from src.interfaces.web.streamlit.presenters.proposal_presenter import (
            ProposalPresenter,
        )

        p = ProposalPresenter()

        # リポジトリをAsyncMockで差し替え
        p.proposal_repository = AsyncMock()
        p.meeting_repository = AsyncMock()
        p.judge_repository = AsyncMock()
        p.membership_repository = AsyncMock()
        p.politician_repository = AsyncMock()

        # UseCaseをAsyncMockで差し替え
        p.manage_parliamentary_group_judges_usecase = AsyncMock()

        # DIコンテナのモック
        mock_container = MagicMock()
        p.container = mock_container

        return p


@pytest.fixture
def sample_proposal():
    """テスト用議案."""
    return Proposal(id=1, title="テスト議案", meeting_id=100)


@pytest.fixture
def sample_meeting():
    """テスト用会議."""
    return Meeting(id=100, conference_id=10, date=date(2024, 6, 15))


@pytest.fixture
def sample_group_judge_dto():
    """テスト用会派賛否DTO."""
    return ProposalParliamentaryGroupJudgeDTO(
        id=1,
        proposal_id=1,
        judgment="賛成",
        judge_type="parliamentary_group",
        parliamentary_group_ids=[10, 20],
        politician_ids=[],
        member_count=5,
        note=None,
        parliamentary_group_names=["自由民主党", "公明党"],
        politician_names=[],
        created_at=None,
    )


@pytest.fixture
def sample_memberships():
    """テスト用メンバーシップ."""
    return [
        ParliamentaryGroupMembership(
            id=1,
            politician_id=101,
            parliamentary_group_id=10,
            start_date=date(2024, 1, 1),
        ),
        ParliamentaryGroupMembership(
            id=2,
            politician_id=102,
            parliamentary_group_id=10,
            start_date=date(2024, 1, 1),
        ),
    ]


@pytest.fixture
def sample_politicians():
    """テスト用政治家."""
    return [
        Politician(id=101, name="田中太郎", prefecture="東京都", district="千代田区"),
        Politician(id=102, name="山田花子", prefecture="大阪府", district="北区"),
    ]


class TestPreviewGroupJudgesExpansion:
    """preview_group_judges_expansionメソッドのテスト."""

    async def test_preview_success(
        self,
        presenter,
        sample_proposal,
        sample_meeting,
        sample_group_judge_dto,
        sample_memberships,
        sample_politicians,
    ):
        """正常系: プレビューが成功し、メンバーリストが返る."""
        # Arrange
        presenter.proposal_repository.get_by_id.return_value = sample_proposal
        presenter.meeting_repository.get_by_id.return_value = sample_meeting

        judges_result = MagicMock()
        judges_result.judges = [sample_group_judge_dto]
        uc = presenter.manage_parliamentary_group_judges_usecase
        uc.list_by_proposal.return_value = judges_result

        presenter.judge_repository.get_by_proposal.return_value = []
        presenter.membership_repository.get_active_by_group.side_effect = [
            sample_memberships,  # group_id=10
            [],  # group_id=20
        ]
        presenter.politician_repository.get_by_ids.return_value = sample_politicians

        # Act
        result = await presenter._preview_group_judges_expansion_async(
            proposal_id=1, group_judge_ids=[1]
        )

        # Assert
        assert result.success is True
        assert len(result.items) == 1
        assert result.total_members == 2
        assert result.total_existing_votes == 0

        item = result.items[0]
        assert item.group_judge_id == 1
        assert item.judgment == "賛成"
        assert len(item.members) == 2
        assert item.members[0].politician_name == "田中太郎"
        assert item.members[0].has_existing_vote is False

    async def test_preview_with_existing_votes(
        self,
        presenter,
        sample_proposal,
        sample_meeting,
        sample_group_judge_dto,
        sample_memberships,
        sample_politicians,
    ):
        """既存の個人投票データがある場合、has_existing_voteがTrueになる."""
        # Arrange
        presenter.proposal_repository.get_by_id.return_value = sample_proposal
        presenter.meeting_repository.get_by_id.return_value = sample_meeting

        judges_result = MagicMock()
        judges_result.judges = [sample_group_judge_dto]
        uc = presenter.manage_parliamentary_group_judges_usecase
        uc.list_by_proposal.return_value = judges_result

        # 政治家ID 101は既存投票データあり
        existing_judge = ProposalJudge(
            id=1, proposal_id=1, politician_id=101, approve="賛成"
        )
        presenter.judge_repository.get_by_proposal.return_value = [existing_judge]

        presenter.membership_repository.get_active_by_group.side_effect = [
            sample_memberships,
            [],
        ]
        presenter.politician_repository.get_by_ids.return_value = sample_politicians

        # Act
        result = await presenter._preview_group_judges_expansion_async(
            proposal_id=1, group_judge_ids=[1]
        )

        # Assert
        assert result.success is True
        assert result.total_existing_votes == 1
        item = result.items[0]
        assert item.existing_vote_count == 1

        member_101 = next(m for m in item.members if m.politician_id == 101)
        assert member_101.has_existing_vote is True

        member_102 = next(m for m in item.members if m.politician_id == 102)
        assert member_102.has_existing_vote is False

    async def test_preview_proposal_not_found(self, presenter):
        """議案が見つからない場合、エラーを返す."""
        # Arrange
        presenter.proposal_repository.get_by_id.return_value = None

        # Act
        result = await presenter._preview_group_judges_expansion_async(
            proposal_id=999, group_judge_ids=[1]
        )

        # Assert
        assert result.success is False
        assert len(result.errors) > 0
        assert "999" in result.errors[0]

    async def test_preview_no_meeting_date(
        self,
        presenter,
        sample_group_judge_dto,
    ):
        """投票日が特定できない場合、アイテムにエラーが設定される."""
        # Arrange
        proposal = Proposal(id=1, title="テスト", meeting_id=None)
        presenter.proposal_repository.get_by_id.return_value = proposal

        judges_result = MagicMock()
        judges_result.judges = [sample_group_judge_dto]
        uc = presenter.manage_parliamentary_group_judges_usecase
        uc.list_by_proposal.return_value = judges_result
        presenter.judge_repository.get_by_proposal.return_value = []

        # Act
        result = await presenter._preview_group_judges_expansion_async(
            proposal_id=1, group_judge_ids=[1]
        )

        # Assert
        assert result.success is True
        assert len(result.items) == 1
        assert len(result.items[0].errors) > 0
        assert "投票日" in result.items[0].errors[0]

    async def test_preview_no_matching_group_judges(
        self,
        presenter,
        sample_proposal,
        sample_meeting,
    ):
        """選択された会派賛否IDが見つからない場合、エラーを返す."""
        # Arrange
        presenter.proposal_repository.get_by_id.return_value = sample_proposal
        presenter.meeting_repository.get_by_id.return_value = sample_meeting

        judges_result = MagicMock()
        judges_result.judges = []
        uc = presenter.manage_parliamentary_group_judges_usecase
        uc.list_by_proposal.return_value = judges_result
        presenter.judge_repository.get_by_proposal.return_value = []

        # Act
        result = await presenter._preview_group_judges_expansion_async(
            proposal_id=1, group_judge_ids=[999]
        )

        # Assert
        assert result.success is False
        assert len(result.errors) > 0


class TestExpandGroupJudgesToIndividual:
    """expand_group_judges_to_individualメソッドのテスト."""

    async def test_expand_with_group_judge_ids(self, presenter):
        """group_judge_idsを指定して展開する場合、各IDについてUseCaseが実行される."""
        # Arrange
        mock_usecase = AsyncMock()
        mock_usecase.execute.return_value = ExpandGroupJudgesResultDTO(
            success=True,
            total_group_judges_processed=1,
            total_judges_created=5,
            total_judges_skipped=0,
            total_judges_overwritten=0,
            group_summaries=[
                GroupJudgeExpansionSummary(
                    group_judge_id=1,
                    proposal_id=1,
                    judgment="賛成",
                    parliamentary_group_ids=[10],
                    members_found=5,
                    judges_created=5,
                )
            ],
        )
        presenter.container.use_cases.expand_group_judges_usecase.return_value = (
            mock_usecase
        )

        # Act
        result = await presenter._expand_group_judges_to_individual_async(
            group_judge_ids=[1, 2],
            force_overwrite=False,
        )

        # Assert
        assert result.success is True
        assert mock_usecase.execute.call_count == 2
        assert result.total_judges_created == 10  # 5 * 2

    async def test_expand_with_proposal_id(self, presenter):
        """proposal_idを指定して展開する場合、UseCaseが1回実行される."""
        # Arrange
        mock_usecase = AsyncMock()
        mock_usecase.execute.return_value = ExpandGroupJudgesResultDTO(
            success=True,
            total_group_judges_processed=3,
            total_judges_created=100,
        )
        presenter.container.use_cases.expand_group_judges_usecase.return_value = (
            mock_usecase
        )

        # Act
        result = await presenter._expand_group_judges_to_individual_async(
            proposal_id=1,
            force_overwrite=False,
        )

        # Assert
        assert result.success is True
        assert result.total_judges_created == 100
        mock_usecase.execute.assert_called_once()

    async def test_expand_with_force_overwrite(self, presenter):
        """force_overwrite=Trueの場合、リクエストにフラグが含まれる."""
        # Arrange
        mock_usecase = AsyncMock()
        mock_usecase.execute.return_value = ExpandGroupJudgesResultDTO(
            success=True,
            total_judges_overwritten=3,
        )
        presenter.container.use_cases.expand_group_judges_usecase.return_value = (
            mock_usecase
        )

        # Act
        await presenter._expand_group_judges_to_individual_async(
            group_judge_ids=[1],
            force_overwrite=True,
        )

        # Assert
        call_args = mock_usecase.execute.call_args[0][0]
        assert call_args.force_overwrite is True

    async def test_expand_partial_failure(self, presenter):
        """一部のgroup_judgeで失敗した場合、success=Falseになる."""
        # Arrange
        mock_usecase = AsyncMock()
        mock_usecase.execute.side_effect = [
            ExpandGroupJudgesResultDTO(
                success=True,
                total_judges_created=5,
            ),
            ExpandGroupJudgesResultDTO(
                success=False,
                errors=["エラーが発生しました"],
            ),
        ]
        presenter.container.use_cases.expand_group_judges_usecase.return_value = (
            mock_usecase
        )

        # Act
        result = await presenter._expand_group_judges_to_individual_async(
            group_judge_ids=[1, 2],
            force_overwrite=False,
        )

        # Assert
        assert result.success is False
        assert result.total_judges_created == 5
        assert len(result.errors) == 1
