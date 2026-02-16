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
        results = await analyzer.analyze("市長", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.MAYOR
        assert results[0].confidence == 1.0

    @pytest.mark.asyncio()
    async def test_mayor_keywords(
        self, analyzer: RuleBasedProposalSubmitterAnalyzer
    ) -> None:
        """市長系キーワードはすべてMAYOR."""
        for keyword in [
            "市長",
            "町長",
            "村長",
            "区長",
            "知事",
            "副市長",
            "副知事",
            "内閣",
            "内閣総理大臣",
        ]:
            results = await analyzer.analyze(keyword, conference_id=1)
            assert len(results) == 1
            assert results[0].submitter_type == SubmitterType.MAYOR, (
                f"{keyword}がMAYORでない"
            )

    @pytest.mark.asyncio()
    async def test_mayor_suffix_match(
        self, analyzer: RuleBasedProposalSubmitterAnalyzer
    ) -> None:
        """「〇〇市長」のような接尾辞もMAYOR."""
        results = await analyzer.analyze("東京都知事", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.MAYOR

    # ========== COMMITTEE判定テスト ==========

    @pytest.mark.asyncio()
    async def test_committee_keyword(
        self, analyzer: RuleBasedProposalSubmitterAnalyzer
    ) -> None:
        """「委員会」を含む文字列はCOMMITTEE."""
        results = await analyzer.analyze("総務委員会", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.COMMITTEE
        assert results[0].confidence == 1.0

    @pytest.mark.asyncio()
    async def test_committee_chairman(
        self, analyzer: RuleBasedProposalSubmitterAnalyzer
    ) -> None:
        """「委員長」を含む文字列はCOMMITTEE."""
        results = await analyzer.analyze("予算委員長", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.COMMITTEE

    # ========== 議員マッチングテスト ==========

    @pytest.mark.asyncio()
    async def test_politician_exact_match(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """議員名完全一致でconfidence=1.0."""
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = []

        mock_repos["conference_member"].get_by_conference.return_value = [
            _make_conference_member(1, 1),
            _make_conference_member(2, 1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            _make_politician(1, "田中太郎"),
            _make_politician(2, "鈴木花子"),
        ]

        results = await analyzer.analyze("田中太郎", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.POLITICIAN
        assert results[0].confidence == 1.0
        assert results[0].matched_politician_id == 1

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

        results = await analyzer.analyze("田中", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.POLITICIAN
        assert results[0].confidence == 0.8
        assert results[0].matched_politician_id == 1

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

        results = await analyzer.analyze("田中太郎", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.POLITICIAN
        assert results[0].matched_politician_id == 1
        assert results[0].confidence == 1.0
        assert len(results[0].candidates) >= 1

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

        results = await analyzer.analyze("田中太郎議員", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.POLITICIAN
        assert results[0].matched_politician_id == 1

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

        results = await analyzer.analyze("自由民主党", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.PARLIAMENTARY_GROUP
        assert results[0].confidence == 1.0
        assert results[0].matched_parliamentary_group_id == 10

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

        results = await analyzer.analyze("自由民主党", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.PARLIAMENTARY_GROUP
        assert results[0].confidence == 0.8
        assert results[0].matched_parliamentary_group_id == 10

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

        results = await analyzer.analyze("不明な提出者", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.OTHER
        assert results[0].confidence == 0.0

    @pytest.mark.asyncio()
    async def test_empty_name_returns_other(
        self, analyzer: RuleBasedProposalSubmitterAnalyzer
    ) -> None:
        """空文字列はOTHER."""
        results = await analyzer.analyze("", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.OTHER
        assert results[0].confidence == 0.0

    @pytest.mark.asyncio()
    async def test_whitespace_only_returns_other(
        self, analyzer: RuleBasedProposalSubmitterAnalyzer
    ) -> None:
        """空白のみはOTHER."""
        results = await analyzer.analyze("   ", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.OTHER
        assert results[0].confidence == 0.0

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

        results = await analyzer.analyze("田中太郎", conference_id=9999)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.OTHER

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

        results = await analyzer.analyze("田中太郎", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.OTHER

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

        results = await analyzer.analyze("市長", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.MAYOR

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

        results = await analyzer.analyze("総務委員会", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.COMMITTEE

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

        results = await analyzer.analyze("新進党", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.PARLIAMENTARY_GROUP
        assert results[0].matched_parliamentary_group_id == 10

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

        results = await analyzer.analyze("自由民主党", conference_id=1)
        assert len(results) == 1
        assert len(results[0].candidates) == 2
        assert (
            results[0].candidates[0].confidence >= results[0].candidates[1].confidence
        )
        assert results[0].candidates[0].entity_id == 11

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

        results = await analyzer.analyze("自由民主党", conference_id=1)
        assert len(results) == 1
        assert (
            results[0].candidates[0].candidate_type
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

        results = await analyzer.analyze("田中　太郎", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.POLITICIAN
        assert results[0].matched_politician_id == 1

    # ========== パーサー統合テスト ==========

    @pytest.mark.asyncio()
    async def test_soto_pattern_extracts_representative(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """「外N名」パターンから代表者名を抽出してマッチングする."""
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = []
        mock_repos["conference_member"].get_by_conference.return_value = [
            _make_conference_member(1, 1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            _make_politician(1, "熊代昭彦"),
        ]

        results = await analyzer.analyze("熊代昭彦君外四名", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.POLITICIAN
        assert results[0].matched_politician_id == 1
        assert results[0].parsed_name == "熊代昭彦"

    @pytest.mark.asyncio()
    async def test_comma_separated_returns_multiple_results(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """カンマ区切りで複数の結果を返す."""
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = []
        mock_repos["conference_member"].get_by_conference.return_value = [
            _make_conference_member(1, 1),
            _make_conference_member(2, 1),
            _make_conference_member(3, 1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            _make_politician(1, "熊代昭彦"),
            _make_politician(2, "谷畑孝"),
            _make_politician(3, "棚橋泰文"),
        ]

        results = await analyzer.analyze("熊代昭彦,谷畑孝,棚橋泰文", conference_id=1)
        assert len(results) == 3
        assert results[0].matched_politician_id == 1
        assert results[0].parsed_name == "熊代昭彦"
        assert results[1].matched_politician_id == 2
        assert results[1].parsed_name == "谷畑孝"
        assert results[2].matched_politician_id == 3
        assert results[2].parsed_name == "棚橋泰文"

    @pytest.mark.asyncio()
    async def test_naikaku_mayor_keyword(
        self, analyzer: RuleBasedProposalSubmitterAnalyzer
    ) -> None:
        """「内閣」はMAYOR."""
        results = await analyzer.analyze("内閣", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.MAYOR

    @pytest.mark.asyncio()
    async def test_naikaku_souri_daijin_mayor_keyword(
        self, analyzer: RuleBasedProposalSubmitterAnalyzer
    ) -> None:
        """「内閣総理大臣」はMAYOR."""
        results = await analyzer.analyze("内閣総理大臣", conference_id=1)
        assert len(results) == 1
        assert results[0].submitter_type == SubmitterType.MAYOR

    @pytest.mark.asyncio()
    async def test_parsed_name_set_on_result(
        self,
        analyzer: RuleBasedProposalSubmitterAnalyzer,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """結果にparsed_nameが設定される."""
        mock_repos["conference"].get_by_id.return_value = _make_conference(1, 100)
        mock_repos["parliamentary_group"].get_by_governing_body_id.return_value = []
        mock_repos["conference_member"].get_by_conference.return_value = [
            _make_conference_member(1, 1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            _make_politician(1, "田中太郎"),
        ]

        results = await analyzer.analyze("田中太郎", conference_id=1)
        assert len(results) == 1
        assert results[0].parsed_name == "田中太郎"
