"""submitter_matching_tabの純粋関数テスト."""

import pytest

from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_submitter import ProposalSubmitter
from src.domain.value_objects.submitter_type import SubmitterType
from src.interfaces.web.streamlit.views.proposals.tabs.submitter_matching_tab import (
    _filter_proposals_by_match_state,
    _get_matched_name,
)


# ========== fixtures ==========


@pytest.fixture
def proposals() -> list[Proposal]:
    """テスト用議案リスト."""
    return [
        Proposal(id=1, title="予算案", meeting_id=100),
        Proposal(id=2, title="条例案", meeting_id=100),
        Proposal(id=3, title="意見書", meeting_id=100),
    ]


@pytest.fixture
def matched_submitter() -> ProposalSubmitter:
    """マッチ済み提出者."""
    return ProposalSubmitter(
        id=10,
        proposal_id=1,
        submitter_type=SubmitterType.POLITICIAN,
        politician_id=100,
        raw_name="山田太郎",
    )


@pytest.fixture
def unmatched_submitter() -> ProposalSubmitter:
    """未マッチ提出者."""
    return ProposalSubmitter(
        id=11,
        proposal_id=2,
        submitter_type=SubmitterType.POLITICIAN,
        politician_id=None,
        raw_name="佐藤花子",
    )


@pytest.fixture
def mayor_submitter() -> ProposalSubmitter:
    """市長提出者."""
    return ProposalSubmitter(
        id=12,
        proposal_id=3,
        submitter_type=SubmitterType.MAYOR,
        raw_name="市長",
    )


# ========== _filter_proposals_by_match_state テスト ==========


class TestFilterProposalsByMatchState:
    """_filter_proposals_by_match_state のテスト."""

    def test_filter_all_returns_all(
        self, proposals: list[Proposal], matched_submitter: ProposalSubmitter
    ) -> None:
        """「全て」フィルタで全議案が返ること."""
        submitters_map = {1: [matched_submitter]}
        result = _filter_proposals_by_match_state(proposals, submitters_map, "全て")
        assert len(result) == 3

    def test_filter_unmatched_returns_proposals_with_unmatched(
        self,
        proposals: list[Proposal],
        matched_submitter: ProposalSubmitter,
        unmatched_submitter: ProposalSubmitter,
    ) -> None:
        """「未マッチ」で未マッチ提出者がある議案のみ返ること."""
        submitters_map = {1: [matched_submitter], 2: [unmatched_submitter]}
        result = _filter_proposals_by_match_state(proposals, submitters_map, "未マッチ")
        result_ids = [p.id for p in result]
        assert 2 in result_ids
        assert 1 not in result_ids

    def test_filter_unmatched_includes_proposals_without_submitters(
        self, proposals: list[Proposal], matched_submitter: ProposalSubmitter
    ) -> None:
        """「未マッチ」で提出者なし議案も含まれること."""
        submitters_map: dict[int, list[ProposalSubmitter]] = {1: [matched_submitter]}
        result = _filter_proposals_by_match_state(proposals, submitters_map, "未マッチ")
        result_ids = [p.id for p in result]
        # 議案ID 2, 3は提出者なし → 未マッチ扱い
        assert 2 in result_ids
        assert 3 in result_ids

    def test_filter_matched_returns_fully_matched_proposals(
        self,
        proposals: list[Proposal],
        matched_submitter: ProposalSubmitter,
        unmatched_submitter: ProposalSubmitter,
    ) -> None:
        """「マッチ済」で全提出者がマッチ済みの議案のみ返ること."""
        submitters_map = {1: [matched_submitter], 2: [unmatched_submitter]}
        result = _filter_proposals_by_match_state(proposals, submitters_map, "マッチ済")
        result_ids = [p.id for p in result]
        assert 1 in result_ids
        assert 2 not in result_ids
        # 提出者なし議案はマッチ済に含まれない
        assert 3 not in result_ids

    def test_filter_empty_proposals(self) -> None:
        """空の議案リストで空リストが返ること."""
        result = _filter_proposals_by_match_state([], {}, "未マッチ")
        assert result == []

    def test_filter_mixed_submitters_in_single_proposal(
        self,
        proposals: list[Proposal],
        matched_submitter: ProposalSubmitter,
    ) -> None:
        """1議案に複数提出者があり、一部未マッチの場合."""
        unmatched = ProposalSubmitter(
            id=20,
            proposal_id=1,
            submitter_type=SubmitterType.POLITICIAN,
            politician_id=None,
            raw_name="未マッチ議員",
        )
        submitters_map = {1: [matched_submitter, unmatched]}
        # 未マッチが1件でもあれば「未マッチ」に含まれる
        result = _filter_proposals_by_match_state(proposals, submitters_map, "未マッチ")
        assert any(p.id == 1 for p in result)
        # 「マッチ済」には含まれない
        result2 = _filter_proposals_by_match_state(
            proposals, submitters_map, "マッチ済"
        )
        assert not any(p.id == 1 for p in result2)


# ========== _get_matched_name テスト ==========


class TestGetMatchedName:
    """_get_matched_name のテスト."""

    def test_politician_with_name(self) -> None:
        """POLITICIAN + politician_id有りで政治家名を返すこと."""
        sub = ProposalSubmitter(
            proposal_id=1,
            submitter_type=SubmitterType.POLITICIAN,
            politician_id=100,
            raw_name="山田",
        )
        result = _get_matched_name(sub, {100: "山田太郎"}, {})
        assert result == "山田太郎"

    def test_politician_id_not_in_map(self) -> None:
        """politician_idが辞書に存在しない場合のフォールバック."""
        sub = ProposalSubmitter(
            proposal_id=1,
            submitter_type=SubmitterType.POLITICIAN,
            politician_id=999,
            raw_name="不明",
        )
        result = _get_matched_name(sub, {}, {})
        assert "999" in result

    def test_parliamentary_group_with_name(self) -> None:
        """PARLIAMENTARY_GROUP + pg_id有りで会派名を返すこと."""
        sub = ProposalSubmitter(
            proposal_id=1,
            submitter_type=SubmitterType.PARLIAMENTARY_GROUP,
            parliamentary_group_id=50,
            raw_name="自民",
        )
        result = _get_matched_name(sub, {}, {50: "自由民主党"})
        assert result == "自由民主党"

    def test_parliamentary_group_id_not_in_map(self) -> None:
        """pg_idが辞書に存在しない場合のフォールバック."""
        sub = ProposalSubmitter(
            proposal_id=1,
            submitter_type=SubmitterType.PARLIAMENTARY_GROUP,
            parliamentary_group_id=999,
            raw_name="不明会派",
        )
        result = _get_matched_name(sub, {}, {})
        assert "999" in result

    def test_mayor_returns_raw_name(self) -> None:
        """MAYORでraw_nameを返すこと."""
        sub = ProposalSubmitter(
            proposal_id=1,
            submitter_type=SubmitterType.MAYOR,
            raw_name="市長",
        )
        result = _get_matched_name(sub, {}, {})
        assert result == "市長"

    def test_committee_returns_raw_name(self) -> None:
        """COMMITTEEでraw_nameを返すこと."""
        sub = ProposalSubmitter(
            proposal_id=1,
            submitter_type=SubmitterType.COMMITTEE,
            raw_name="総務委員会",
        )
        result = _get_matched_name(sub, {}, {})
        assert result == "総務委員会"

    def test_mayor_without_raw_name(self) -> None:
        """MAYORでraw_nameがNoneの場合のフォールバック."""
        sub = ProposalSubmitter(
            proposal_id=1,
            submitter_type=SubmitterType.MAYOR,
            raw_name=None,
        )
        result = _get_matched_name(sub, {}, {})
        assert result == "MAYOR"

    def test_other_type_returns_raw_name(self) -> None:
        """OTHERタイプでraw_nameを返すこと."""
        sub = ProposalSubmitter(
            proposal_id=1,
            submitter_type=SubmitterType.OTHER,
            raw_name="その他提出者",
        )
        result = _get_matched_name(sub, {}, {})
        assert result == "その他提出者"

    def test_other_type_without_raw_name(self) -> None:
        """OTHERタイプでraw_nameがNoneの場合のデフォルト値."""
        sub = ProposalSubmitter(
            proposal_id=1,
            submitter_type=SubmitterType.OTHER,
            raw_name=None,
        )
        result = _get_matched_name(sub, {}, {})
        assert result == "（不明）"
