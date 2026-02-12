"""ProposalPresenterの個人投票展開メソッドのテスト (Issue #1010)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.dtos.expand_group_judges_dto import (
    ExpandGroupJudgesPreviewDTO,
    ExpandGroupJudgesResultDTO,
    GroupJudgeExpansionSummary,
    GroupJudgePreviewItem,
    GroupJudgePreviewMember,
)


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

        # DIコンテナのモック
        mock_container = MagicMock()
        p.container = mock_container

        return p


class TestPreviewGroupJudgesExpansion:
    """preview_group_judges_expansionメソッドのテスト（UseCase委譲）."""

    async def test_preview_delegates_to_usecase(self, presenter):
        """プレビューがUseCaseのpreview()に委譲される."""
        # Arrange
        expected = ExpandGroupJudgesPreviewDTO(
            success=True,
            items=[
                GroupJudgePreviewItem(
                    group_judge_id=1,
                    proposal_id=1,
                    judgment="賛成",
                    parliamentary_group_names=["自由民主党"],
                    members=[
                        GroupJudgePreviewMember(
                            politician_id=101,
                            politician_name="田中太郎",
                            has_existing_vote=False,
                        )
                    ],
                )
            ],
            total_members=1,
            total_existing_votes=0,
        )
        mock_usecase = AsyncMock()
        mock_usecase.preview.return_value = expected
        presenter.container.use_cases.expand_group_judges_usecase.return_value = (
            mock_usecase
        )

        # Act
        result = await presenter._preview_group_judges_expansion_async(
            proposal_id=1, group_judge_ids=[1]
        )

        # Assert
        assert result is expected
        mock_usecase.preview.assert_called_once_with(1, [1])

    async def test_preview_raises_when_no_container(self, presenter):
        """containerがNoneの場合、ValueErrorが発生する."""
        presenter.container = None

        with pytest.raises(ValueError, match="DI container is not initialized"):
            await presenter._preview_group_judges_expansion_async(
                proposal_id=1, group_judge_ids=[1]
            )


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

    async def test_expand_raises_when_no_container(self, presenter):
        """containerがNoneの場合、ValueErrorが発生する."""
        presenter.container = None

        with pytest.raises(ValueError, match="DI container is not initialized"):
            await presenter._expand_group_judges_to_individual_async(
                group_judge_ids=[1],
                force_overwrite=False,
            )


class TestExpandSingleGroupJudge:
    """expand_single_group_judgeメソッドのテスト."""

    async def test_single_expand_calls_usecase(self, presenter):
        """単一の会派賛否展開がUseCaseに委譲される."""
        # Arrange
        expected = ExpandGroupJudgesResultDTO(
            success=True,
            total_judges_created=5,
        )
        mock_usecase = AsyncMock()
        mock_usecase.execute.return_value = expected
        presenter.container.use_cases.expand_group_judges_usecase.return_value = (
            mock_usecase
        )

        # Act
        result = await presenter._expand_single_group_judge_async(
            group_judge_id=1, force_overwrite=False
        )

        # Assert
        assert result is expected
        mock_usecase.execute.assert_called_once()
        call_args = mock_usecase.execute.call_args[0][0]
        assert call_args.group_judge_id == 1
        assert call_args.force_overwrite is False
