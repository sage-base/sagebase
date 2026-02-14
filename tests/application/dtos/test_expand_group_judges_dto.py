"""ExpandGroupJudgesResultDTO.merge()のテスト."""

from src.application.dtos.expand_group_judges_dto import (
    ExpandGroupJudgesResultDTO,
    GroupJudgeExpansionSummary,
)


class TestExpandGroupJudgesResultDTOMerge:
    """merge()クラスメソッドのテストケース."""

    def test_merge_empty_list(self):
        """空リスト: success=True、全フィールド0の結果が返る."""
        result = ExpandGroupJudgesResultDTO.merge([])

        assert result.success is True
        assert result.total_group_judges_processed == 0
        assert result.total_members_found == 0
        assert result.total_judges_created == 0
        assert result.total_judges_skipped == 0
        assert result.total_judges_overwritten == 0
        assert result.skipped_no_meeting_date == 0
        assert result.group_summaries == []
        assert result.errors == []

    def test_merge_single_result(self):
        """単一要素: 入力と同じ値が返る."""
        single = ExpandGroupJudgesResultDTO(
            success=True,
            total_group_judges_processed=2,
            total_members_found=10,
            total_judges_created=8,
            total_judges_skipped=2,
            total_judges_overwritten=0,
            skipped_no_meeting_date=1,
            errors=["エラー1"],
        )

        result = ExpandGroupJudgesResultDTO.merge([single])

        assert result.success is True
        assert result.total_group_judges_processed == 2
        assert result.total_members_found == 10
        assert result.total_judges_created == 8
        assert result.total_judges_skipped == 2
        assert result.skipped_no_meeting_date == 1
        assert result.errors == ["エラー1"]

    def test_merge_multiple_all_success(self):
        """全成功: 数値が合算される."""
        r1 = ExpandGroupJudgesResultDTO(
            success=True,
            total_group_judges_processed=1,
            total_members_found=5,
            total_judges_created=3,
            total_judges_skipped=2,
        )
        r2 = ExpandGroupJudgesResultDTO(
            success=True,
            total_group_judges_processed=2,
            total_members_found=10,
            total_judges_created=7,
            total_judges_overwritten=3,
        )

        result = ExpandGroupJudgesResultDTO.merge([r1, r2])

        assert result.success is True
        assert result.total_group_judges_processed == 3
        assert result.total_members_found == 15
        assert result.total_judges_created == 10
        assert result.total_judges_skipped == 2
        assert result.total_judges_overwritten == 3

    def test_merge_partial_failure(self):
        """部分失敗: success=Falseになりエラーが集約される."""
        r1 = ExpandGroupJudgesResultDTO(
            success=True,
            total_judges_created=3,
        )
        r2 = ExpandGroupJudgesResultDTO(
            success=False,
            errors=["会派賛否の取得に失敗"],
        )

        result = ExpandGroupJudgesResultDTO.merge([r1, r2])

        assert result.success is False
        assert result.total_judges_created == 3
        assert result.errors == ["会派賛否の取得に失敗"]

    def test_merge_group_summaries_concatenated(self):
        """group_summaries: リストが結合される."""
        s1 = GroupJudgeExpansionSummary(
            group_judge_id=1,
            proposal_id=100,
            judgment="賛成",
            parliamentary_group_ids=[10],
            judges_created=3,
        )
        s2 = GroupJudgeExpansionSummary(
            group_judge_id=2,
            proposal_id=200,
            judgment="反対",
            parliamentary_group_ids=[20],
            judges_created=5,
        )
        r1 = ExpandGroupJudgesResultDTO(success=True, group_summaries=[s1])
        r2 = ExpandGroupJudgesResultDTO(success=True, group_summaries=[s2])

        result = ExpandGroupJudgesResultDTO.merge([r1, r2])

        assert len(result.group_summaries) == 2
        assert result.group_summaries[0].group_judge_id == 1
        assert result.group_summaries[1].group_judge_id == 2

    def test_merge_errors_from_multiple_results(self):
        """複数エラー: 全結果のエラーが集約される."""
        r1 = ExpandGroupJudgesResultDTO(success=False, errors=["エラーA", "エラーB"])
        r2 = ExpandGroupJudgesResultDTO(success=False, errors=["エラーC"])

        result = ExpandGroupJudgesResultDTO.merge([r1, r2])

        assert result.success is False
        assert result.errors == ["エラーA", "エラーB", "エラーC"]
