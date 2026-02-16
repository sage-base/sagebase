"""RuleBasedProposalSubmitterAnalyzerのテスト."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.entities.conference import Conference
from src.domain.entities.conference_member import ConferenceMember
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.politician import Politician
from src.domain.repositories.conference_member_repository import (
    ConferenceMemberRepository,
)
from src.domain.repositories.conference_repository import ConferenceRepository
from src.domain.repositories.parliamentary_group_repository import (
    ParliamentaryGroupRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.value_objects.submitter_analysis_result import (
    SubmitterCandidateType,
)
from src.domain.value_objects.submitter_type import SubmitterType
from src.infrastructure.external.proposal_submitter_analyzer.rule_based_proposal_submitter_analyzer import (  # noqa: E501
    RuleBasedProposalSubmitterAnalyzer,
)


def _make_politician(id: int, name: str) -> Politician:
    """テスト用Politicianエンティティを作成."""
    p = MagicMock(spec=Politician)
    p.id = id
    p.name = name
    return p


def _make_conference_member(politician_id: int, conference_id: int) -> ConferenceMember:
    """テスト用ConferenceMemberを作成."""
    from datetime import date

    return ConferenceMember(
        politician_id=politician_id,
        conference_id=conference_id,
        start_date=date(2024, 1, 1),
        id=politician_id * 100,
    )


def _make_parliamentary_group(id: int, name: str) -> ParliamentaryGroup:
    """テスト用ParliamentaryGroupを作成."""
    pg = MagicMock(spec=ParliamentaryGroup)
    pg.id = id
    pg.name = name
    return pg


def _make_conference(id: int, governing_body_id: int) -> Conference:
    """テスト用Conferenceを作成."""
    c = MagicMock(spec=Conference)
    c.id = id
    c.governing_body_id = governing_body_id
    return c


class TestRuleBasedProposalSubmitterAnalyzer:
    """RuleBasedProposalSubmitterAnalyzerのテスト."""

    @pytest.fixture()
    def mock_repos(self) -> dict[str, AsyncMock]:
        return {
            "politician": AsyncMock(spec=PoliticianRepository),
            "conference_member": AsyncMock(spec=ConferenceMemberRepository),
            "parliamentary_group": AsyncMock(spec=ParliamentaryGroupRepository),
            "conference": AsyncMock(spec=ConferenceRepository),
        }

    @pytest.fixture()
    def analyzer(
        self, mock_repos: dict[str, AsyncMock]
    ) -> RuleBasedProposalSubmitterAnalyzer:
        return RuleBasedProposalSubmitterAnalyzer(
            politician_repository=mock_repos["politician"],
            conference_member_repository=mock_repos["conference_member"],
            parliamentary_group_repository=mock_repos["parliamentary_group"],
            conference_repository=mock_repos["conference"],
        )

    # ========== MAYOR判定テスト ==========

    @pytest.mark.asyncio()
    async def test_mayor_exact_match(
        self, analyzer: RuleBasedProposalSubmitterAnalyzer
    ) -> None:
        """「市長」は MAYOR として判定される."""
        result = await analyzer.analyze("市長", conference_id=1)
        assert result.submitter_type == SubmitterType.MAYOR
        assert result.confidence == 1.0

    @pytest.mark.asyncio()
    async def test_mayor_keywords(
        self, analyzer: RuleBasedProposalSubmitterAnalyzer
    ) -> None:
        """市長系キーワードはすべてMAYOR."""
        for keyword in ["市長", "町長", "村長", "区長", "知事", "副市長", "副知事"]:
            result = await analyzer.analyze(keyword, conference_id=1)
            assert result.submitter_type == SubmitterType.MAYOR, (
                f"{keyword}がMAYORでない"
            )

    @pytest.mark.asyncio()
    async def test_mayor_suffix_match(
        self, analyzer: RuleBasedProposalSubmitterAnalyzer
    ) -> None:
        """「〇〇市長」のような接尾辞もMAYOR."""
        result = await analyzer.analyze("東京都知事", conference_id=1)
        assert result.submitter_type == SubmitterType.MAYOR

    # ========== COMMITTEE判定テスト ==========

    @pytest.mark.asyncio()
    async def test_committee_keyword(
        self, analyzer: RuleBasedProposalSubmitterAnalyzer
    ) -> None:
        """「委員会」を含む文字列はCOMMITTEE."""
        result = await analyzer.analyze("総務委員会", conference_id=1)
        assert result.submitter_type == SubmitterType.COMMITTEE
        assert result.confidence == 1.0

    @pytest.mark.asyncio()
    async def test_committee_chairman(
        self, analyzer: RuleBasedProposalSubmitterAnalyzer
    ) -> None:
        """「委員長」を含む文字列はCOMMITTEE."""
        result = await analyzer.analyze("予算委員長", conference_id=1)
        assert result.submitter_type == SubmitterType.COMMITTEE

    # ========== 議員マッチングテスト ==========

    @pytest.mark.asyncio()
    async def test_politician_exact_match(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """議員名完全一致でconfidence=1.0."""
        # 会派なし（空リスト）
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = []

        # 議員データ
        mock_repos["conference_member"].get_by_conference.return_value = [
            _make_conference_member(1, 1),
            _make_conference_member(2, 1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            _make_politician(1, "田中太郎"),
            _make_politician(2, "鈴木花子"),
        ]

        result = await analyzer.analyze("田中太郎", conference_id=1)
        assert result.submitter_type == SubmitterType.POLITICIAN
        assert result.confidence == 1.0
        assert result.matched_politician_id == 1

    @pytest.mark.asyncio()
    async def test_politician_partial_match(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """議員名の部分一致でconfidence=0.8."""
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = []
        mock_repos["conference_member"].get_by_conference.return_value = [
            _make_conference_member(1, 1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            _make_politician(1, "田中太郎"),
        ]

        # 「田中」は「田中太郎」に含まれる → 部分一致
        result = await analyzer.analyze("田中", conference_id=1)
        assert result.submitter_type == SubmitterType.POLITICIAN
        assert result.confidence == 0.8
        assert result.matched_politician_id == 1

    @pytest.mark.asyncio()
    async def test_politician_multiple_candidates(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """複数候補がある場合は信頼度順にソートされる."""
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = []
        mock_repos["conference_member"].get_by_conference.return_value = [
            _make_conference_member(1, 1),
            _make_conference_member(2, 1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            _make_politician(1, "田中太郎"),
            _make_politician(2, "田中次郎"),
        ]

        result = await analyzer.analyze("田中太郎", conference_id=1)
        assert result.submitter_type == SubmitterType.POLITICIAN
        # 完全一致の田中太郎が最高信頼度
        assert result.matched_politician_id == 1
        assert result.confidence == 1.0
        # 田中次郎も候補に含まれる（部分一致で0.7以上）
        assert len(result.candidates) >= 1

    @pytest.mark.asyncio()
    async def test_politician_honorific_stripped(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """敬称付きの名前でも正規化後にマッチする."""
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = []
        mock_repos["conference_member"].get_by_conference.return_value = [
            _make_conference_member(1, 1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            _make_politician(1, "田中太郎"),
        ]

        result = await analyzer.analyze("田中太郎議員", conference_id=1)
        assert result.submitter_type == SubmitterType.POLITICIAN
        assert result.matched_politician_id == 1

    # ========== 会派マッチングテスト ==========

    @pytest.mark.asyncio()
    async def test_parliamentary_group_exact_match(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """会派名完全一致でconfidence=1.0."""
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = [
            _make_parliamentary_group(10, "自由民主党"),
            _make_parliamentary_group(11, "公明党"),
        ]

        result = await analyzer.analyze("自由民主党", conference_id=1)
        assert result.submitter_type == SubmitterType.PARLIAMENTARY_GROUP
        assert result.confidence == 1.0
        assert result.matched_parliamentary_group_id == 10

    @pytest.mark.asyncio()
    async def test_parliamentary_group_partial_match(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """会派名の部分一致でconfidence=0.8."""
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = [
            _make_parliamentary_group(10, "自由民主党議員団"),
        ]

        # 「自由民主党」は「自由民主党議員団」に含まれる
        result = await analyzer.analyze("自由民主党", conference_id=1)
        assert result.submitter_type == SubmitterType.PARLIAMENTARY_GROUP
        assert result.confidence == 0.8
        assert result.matched_parliamentary_group_id == 10

    # ========== OTHER判定テスト ==========

    @pytest.mark.asyncio()
    async def test_no_match_returns_other(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """マッチなしの場合はOTHER."""
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = []
        mock_repos["conference_member"].get_by_conference.return_value = []
        mock_repos["politician"].get_by_ids.return_value = []

        result = await analyzer.analyze("不明な提出者", conference_id=1)
        assert result.submitter_type == SubmitterType.OTHER
        assert result.confidence == 0.0

    @pytest.mark.asyncio()
    async def test_empty_name_returns_other(
        self, analyzer: RuleBasedProposalSubmitterAnalyzer
    ) -> None:
        """空文字列はOTHER."""
        result = await analyzer.analyze("", conference_id=1)
        assert result.submitter_type == SubmitterType.OTHER
        assert result.confidence == 0.0

    @pytest.mark.asyncio()
    async def test_whitespace_only_returns_other(
        self, analyzer: RuleBasedProposalSubmitterAnalyzer
    ) -> None:
        """空白のみはOTHER."""
        result = await analyzer.analyze("   ", conference_id=1)
        assert result.submitter_type == SubmitterType.OTHER
        assert result.confidence == 0.0

    # ========== 異常系テスト ==========

    @pytest.mark.asyncio()
    async def test_conference_not_found(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """conference_idが不正でも例外は発生しない."""
        mock_repos["conference"].get_by_id.return_value = None
        mock_repos["conference_member"].get_by_conference.return_value = []
        mock_repos["politician"].get_by_ids.return_value = []

        result = await analyzer.analyze("田中太郎", conference_id=9999)
        assert result.submitter_type == SubmitterType.OTHER

    @pytest.mark.asyncio()
    async def test_no_members_in_conference(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """メンバー0件の会議体でも正常に動作."""
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = []
        mock_repos["conference_member"].get_by_conference.return_value = []
        mock_repos["politician"].get_by_ids.return_value = []

        result = await analyzer.analyze("田中太郎", conference_id=1)
        assert result.submitter_type == SubmitterType.OTHER

    # ========== 判定優先順位テスト ==========

    @pytest.mark.asyncio()
    async def test_mayor_takes_priority_over_politician(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """MAYORキーワードは議員マッチングより優先される."""
        mock_repos["conference_member"].get_by_conference.return_value = [
            _make_conference_member(1, 1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            _make_politician(1, "市長"),
        ]

        result = await analyzer.analyze("市長", conference_id=1)
        assert result.submitter_type == SubmitterType.MAYOR

    @pytest.mark.asyncio()
    async def test_committee_takes_priority_over_parliamentary_group(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """COMMITTEEキーワードは会派マッチングより優先される."""
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = [
            _make_parliamentary_group(10, "総務委員会"),
        ]

        result = await analyzer.analyze("総務委員会", conference_id=1)
        assert result.submitter_type == SubmitterType.COMMITTEE

    @pytest.mark.asyncio()
    async def test_parliamentary_group_priority_over_politician(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """会派マッチングが議員マッチングより先に実行される."""
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = [
            _make_parliamentary_group(10, "新進党"),
        ]

        result = await analyzer.analyze("新進党", conference_id=1)
        assert result.submitter_type == SubmitterType.PARLIAMENTARY_GROUP
        assert result.matched_parliamentary_group_id == 10

    # ========== 候補のソートテスト ==========

    @pytest.mark.asyncio()
    async def test_candidates_sorted_by_confidence_desc(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """候補は信頼度降順にソートされる."""
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = [
            _make_parliamentary_group(10, "自由民主党議員団"),
            _make_parliamentary_group(11, "自由民主党"),
        ]

        result = await analyzer.analyze("自由民主党", conference_id=1)
        assert len(result.candidates) == 2
        # 完全一致の方が先
        assert result.candidates[0].confidence >= result.candidates[1].confidence
        assert result.candidates[0].entity_id == 11

    @pytest.mark.asyncio()
    async def test_candidate_type_is_correct(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """候補のcandidate_typeが正しく設定される."""
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = [
            _make_parliamentary_group(10, "自由民主党"),
        ]

        result = await analyzer.analyze("自由民主党", conference_id=1)
        assert (
            result.candidates[0].candidate_type
            == SubmitterCandidateType.PARLIAMENTARY_GROUP
        )

    # ========== 正規化テスト ==========

    @pytest.mark.asyncio()
    async def test_fullwidth_space_normalized(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """全角スペースが正規化されてマッチする."""
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = []
        mock_repos["conference_member"].get_by_conference.return_value = [
            _make_conference_member(1, 1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            _make_politician(1, "田中 太郎"),
        ]

        # 全角スペース入りの名前
        result = await analyzer.analyze("田中　太郎", conference_id=1)
        assert result.submitter_type == SubmitterType.POLITICIAN
        assert result.matched_politician_id == 1
