"""ProposalPresenter展開メソッドのテスト."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.dtos.expand_group_judges_dto import (
    ExpandGroupJudgesRequestDTO,
    ExpandGroupJudgesResultDTO,
)
from src.application.dtos.expand_group_judges_preview_dto import (
    ExpandGroupJudgesPreviewDTO,
    GroupJudgePreviewItem,
    GroupJudgePreviewMember,
)


@pytest.fixture
def mock_expand_usecase():
    return AsyncMock()


@pytest.fixture
def presenter(mock_expand_usecase):
    with (
        patch(
            "src.interfaces.web.streamlit.presenters.proposal_presenter.RepositoryAdapter"
        ) as mock_adapter,
        patch(
            "src.interfaces.web.streamlit.presenters.proposal_presenter.SessionManager"
        ),
    ):
        mock_adapter.return_value = MagicMock()
        from src.interfaces.web.streamlit.presenters.proposal_presenter import (
            ProposalPresenter,
        )

        p = ProposalPresenter.__new__(ProposalPresenter)
        p.expand_group_judges_usecase = mock_expand_usecase
        p.logger = MagicMock()

        def _run_async(coro):
            import asyncio

            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        p._run_async = _run_async
        return p


class TestProposalPresenterExpand:
    """ProposalPresenter展開メソッドのテストケース."""

    def test_preview_delegates_to_usecase(self, presenter, mock_expand_usecase):
        """プレビューがUseCaseに委譲される."""
        expected = ExpandGroupJudgesPreviewDTO(
            success=True,
            items=[
                GroupJudgePreviewItem(
                    group_judge_id=1,
                    judgment="賛成",
                    parliamentary_group_names=["テスト会派"],
                    members=[
                        GroupJudgePreviewMember(
                            politician_id=501,
                            politician_name="議員A",
                            has_existing_vote=False,
                        )
                    ],
                )
            ],
            total_members=1,
        )
        mock_expand_usecase.preview.return_value = expected

        result = presenter.preview_group_judges_expansion([1])

        assert result.success is True
        assert result.total_members == 1
        mock_expand_usecase.preview.assert_called_once_with([1])

    def test_expand_multiple_ids_merges_results(self, presenter, mock_expand_usecase):
        """複数ID統合: 各IDのexecute結果がmergeされる."""
        result1 = ExpandGroupJudgesResultDTO(success=True, total_judges_created=3)
        result2 = ExpandGroupJudgesResultDTO(success=True, total_judges_created=2)
        mock_expand_usecase.execute.side_effect = [result1, result2]

        result = presenter.expand_group_judges_to_individual(group_judge_ids=[1, 2])

        assert result.success is True
        assert result.total_judges_created == 5
        assert mock_expand_usecase.execute.call_count == 2

    def test_expand_with_force_overwrite(self, presenter, mock_expand_usecase):
        """force_overwriteパラメータが正しく渡される."""
        mock_expand_usecase.execute.return_value = ExpandGroupJudgesResultDTO(
            success=True, total_judges_overwritten=1
        )

        presenter.expand_group_judges_to_individual(
            group_judge_ids=[1], force_overwrite=True
        )

        call_args = mock_expand_usecase.execute.call_args[0][0]
        assert isinstance(call_args, ExpandGroupJudgesRequestDTO)
        assert call_args.force_overwrite is True

    def test_expand_single_group_judge(self, presenter, mock_expand_usecase):
        """単一会派賛否の展開."""
        mock_expand_usecase.execute.return_value = ExpandGroupJudgesResultDTO(
            success=True, total_judges_created=5
        )

        result = presenter.expand_single_group_judge(
            group_judge_id=1, force_overwrite=False
        )

        assert result.success is True
        assert result.total_judges_created == 5
        call_args = mock_expand_usecase.execute.call_args[0][0]
        assert call_args.group_judge_id == 1
        assert call_args.force_overwrite is False

    def test_expand_partial_failure(self, presenter, mock_expand_usecase):
        """部分失敗: 一部のIDが失敗してもmerge結果が返却される."""
        result1 = ExpandGroupJudgesResultDTO(success=True, total_judges_created=3)
        result2 = ExpandGroupJudgesResultDTO(success=False, errors=["テストエラー"])
        mock_expand_usecase.execute.side_effect = [result1, result2]

        result = presenter.expand_group_judges_to_individual(group_judge_ids=[1, 2])

        assert result.success is False
        assert result.total_judges_created == 3
        assert "テストエラー" in result.errors

    def test_expand_by_proposal_id(self, presenter, mock_expand_usecase):
        """proposal_id指定での展開."""
        mock_expand_usecase.execute.return_value = ExpandGroupJudgesResultDTO(
            success=True, total_judges_created=10
        )

        result = presenter.expand_group_judges_to_individual(proposal_id=100)

        assert result.success is True
        call_args = mock_expand_usecase.execute.call_args[0][0]
        assert call_args.proposal_id == 100
        assert call_args.group_judge_id is None
