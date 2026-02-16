"""AnalyzeProposalSubmittersUseCaseのテスト."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.usecases.analyze_proposal_submitters_usecase import (
    AnalyzeProposalSubmittersUseCase,
)
from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_submitter import ProposalSubmitter
from src.domain.repositories.proposal_repository import ProposalRepository
from src.domain.repositories.proposal_submitter_repository import (
    ProposalSubmitterRepository,
)
from src.domain.value_objects.submitter_analysis_result import (
    SubmitterAnalysisResult,
    SubmitterCandidate,
    SubmitterCandidateType,
)
from src.domain.value_objects.submitter_type import SubmitterType


def _make_proposal(id: int, conference_id: int | None = 1) -> Proposal:
    """テスト用Proposalを作成."""
    p = MagicMock(spec=Proposal)
    p.id = id
    p.conference_id = conference_id
    return p


def _make_submitter(
    id: int,
    proposal_id: int,
    raw_name: str,
    submitter_type: SubmitterType = SubmitterType.OTHER,
    politician_id: int | None = None,
    parliamentary_group_id: int | None = None,
) -> ProposalSubmitter:
    """テスト用ProposalSubmitterを作成."""
    return ProposalSubmitter(
        proposal_id=proposal_id,
        submitter_type=submitter_type,
        raw_name=raw_name,
        politician_id=politician_id,
        parliamentary_group_id=parliamentary_group_id,
        id=id,
    )


class TestAnalyzeProposalSubmittersUseCase:
    """AnalyzeProposalSubmittersUseCaseのテスト."""

    @pytest.fixture()
    def mock_repos(self) -> dict[str, AsyncMock]:
        return {
            "proposal": AsyncMock(spec=ProposalRepository),
            "proposal_submitter": AsyncMock(spec=ProposalSubmitterRepository),
        }

    @pytest.fixture()
    def mock_analyzer(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture()
    def use_case(
        self, mock_repos: dict[str, AsyncMock], mock_analyzer: AsyncMock
    ) -> AnalyzeProposalSubmittersUseCase:
        return AnalyzeProposalSubmittersUseCase(
            proposal_repository=mock_repos["proposal"],
            proposal_submitter_repository=mock_repos["proposal_submitter"],
            analyzer_service=mock_analyzer,
        )

    @pytest.mark.asyncio()
    async def test_empty_proposal_ids(
        self, use_case: AnalyzeProposalSubmittersUseCase
    ) -> None:
        """空のproposal_idsは正常に処理される."""
        result = await use_case.execute([])
        assert result.success is True
        assert result.total_analyzed == 0

    @pytest.mark.asyncio()
    async def test_analyze_mayor_submitter(
        self,
        use_case: AnalyzeProposalSubmittersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_analyzer: AsyncMock,
    ) -> None:
        """市長提出者の自動判定."""
        submitter = _make_submitter(1, 100, "市長")
        mock_repos["proposal_submitter"].get_by_proposal_ids.return_value = {
            100: [submitter],
        }
        mock_repos["proposal"].get_by_ids.return_value = [_make_proposal(100)]

        mock_analyzer.analyze.return_value = [
            SubmitterAnalysisResult(
                submitter_type=SubmitterType.MAYOR,
                confidence=1.0,
            ),
        ]

        result = await use_case.execute([100])
        assert result.success is True
        assert result.total_analyzed == 1
        assert result.total_matched == 1
        mock_repos["proposal_submitter"].update.assert_called_once()

    @pytest.mark.asyncio()
    async def test_analyze_politician_submitter(
        self,
        use_case: AnalyzeProposalSubmittersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_analyzer: AsyncMock,
    ) -> None:
        """議員提出者の自動マッチング."""
        submitter = _make_submitter(1, 100, "田中太郎")
        mock_repos["proposal_submitter"].get_by_proposal_ids.return_value = {
            100: [submitter],
        }
        mock_repos["proposal"].get_by_ids.return_value = [_make_proposal(100)]

        mock_analyzer.analyze.return_value = [
            SubmitterAnalysisResult(
                submitter_type=SubmitterType.POLITICIAN,
                confidence=1.0,
                matched_politician_id=5,
                parsed_name="田中太郎",
                candidates=[
                    SubmitterCandidate(
                        candidate_type=SubmitterCandidateType.POLITICIAN,
                        entity_id=5,
                        name="田中太郎",
                        confidence=1.0,
                    )
                ],
            ),
        ]

        result = await use_case.execute([100])
        assert result.success is True
        assert result.total_matched == 1
        assert submitter.politician_id == 5
        assert submitter.submitter_type == SubmitterType.POLITICIAN

    @pytest.mark.asyncio()
    async def test_analyze_parliamentary_group_submitter(
        self,
        use_case: AnalyzeProposalSubmittersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_analyzer: AsyncMock,
    ) -> None:
        """会派提出者の自動マッチング."""
        submitter = _make_submitter(1, 100, "自由民主党")
        mock_repos["proposal_submitter"].get_by_proposal_ids.return_value = {
            100: [submitter],
        }
        mock_repos["proposal"].get_by_ids.return_value = [_make_proposal(100)]

        mock_analyzer.analyze.return_value = [
            SubmitterAnalysisResult(
                submitter_type=SubmitterType.PARLIAMENTARY_GROUP,
                confidence=1.0,
                matched_parliamentary_group_id=10,
                parsed_name="自由民主党",
                candidates=[
                    SubmitterCandidate(
                        candidate_type=SubmitterCandidateType.PARLIAMENTARY_GROUP,
                        entity_id=10,
                        name="自由民主党",
                        confidence=1.0,
                    )
                ],
            ),
        ]

        result = await use_case.execute([100])
        assert result.success is True
        assert result.total_matched == 1
        assert submitter.parliamentary_group_id == 10

    @pytest.mark.asyncio()
    async def test_skip_already_matched_submitter(
        self,
        use_case: AnalyzeProposalSubmittersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_analyzer: AsyncMock,
    ) -> None:
        """既にマッチ済みの提出者はスキップされる."""
        submitter = _make_submitter(
            1,
            100,
            "田中太郎",
            submitter_type=SubmitterType.POLITICIAN,
            politician_id=5,
        )
        mock_repos["proposal_submitter"].get_by_proposal_ids.return_value = {
            100: [submitter],
        }
        mock_repos["proposal"].get_by_ids.return_value = [_make_proposal(100)]

        result = await use_case.execute([100])
        assert result.success is True
        assert result.total_analyzed == 0
        mock_analyzer.analyze.assert_not_called()

    @pytest.mark.asyncio()
    async def test_skip_submitter_without_raw_name(
        self,
        use_case: AnalyzeProposalSubmittersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_analyzer: AsyncMock,
    ) -> None:
        """raw_nameがない提出者はスキップされる."""
        submitter = ProposalSubmitter(
            proposal_id=100,
            submitter_type=SubmitterType.OTHER,
            raw_name=None,
            id=1,
        )
        mock_repos["proposal_submitter"].get_by_proposal_ids.return_value = {
            100: [submitter],
        }
        mock_repos["proposal"].get_by_ids.return_value = [_make_proposal(100)]

        result = await use_case.execute([100])
        assert result.success is True
        assert result.total_analyzed == 0
        mock_analyzer.analyze.assert_not_called()

    @pytest.mark.asyncio()
    async def test_low_confidence_not_updated(
        self,
        use_case: AnalyzeProposalSubmittersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_analyzer: AsyncMock,
    ) -> None:
        """信頼度が0.7未満の場合は更新されない."""
        submitter = _make_submitter(1, 100, "不明な名前")
        mock_repos["proposal_submitter"].get_by_proposal_ids.return_value = {
            100: [submitter],
        }
        mock_repos["proposal"].get_by_ids.return_value = [_make_proposal(100)]

        mock_analyzer.analyze.return_value = [
            SubmitterAnalysisResult(
                submitter_type=SubmitterType.OTHER,
                confidence=0.3,
            ),
        ]

        result = await use_case.execute([100])
        assert result.success is True
        assert result.total_analyzed == 1
        assert result.total_matched == 0
        mock_repos["proposal_submitter"].update.assert_not_called()

    @pytest.mark.asyncio()
    async def test_proposal_without_conference_id(
        self,
        use_case: AnalyzeProposalSubmittersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_analyzer: AsyncMock,
    ) -> None:
        """conference_idが未設定の議案はスキップされる."""
        submitter = _make_submitter(1, 100, "田中太郎")
        mock_repos["proposal_submitter"].get_by_proposal_ids.return_value = {
            100: [submitter],
        }
        mock_repos["proposal"].get_by_ids.return_value = [
            _make_proposal(100, conference_id=None)
        ]

        result = await use_case.execute([100])
        assert result.success is True
        assert result.total_analyzed == 0
        mock_analyzer.analyze.assert_not_called()

    @pytest.mark.asyncio()
    async def test_multiple_proposals(
        self,
        use_case: AnalyzeProposalSubmittersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_analyzer: AsyncMock,
    ) -> None:
        """複数議案の一括分析."""
        submitter1 = _make_submitter(1, 100, "市長")
        submitter2 = _make_submitter(2, 200, "田中太郎")

        mock_repos["proposal_submitter"].get_by_proposal_ids.return_value = {
            100: [submitter1],
            200: [submitter2],
        }
        mock_repos["proposal"].get_by_ids.return_value = [
            _make_proposal(100, conference_id=1),
            _make_proposal(200, conference_id=1),
        ]

        mock_analyzer.analyze.side_effect = [
            [
                SubmitterAnalysisResult(
                    submitter_type=SubmitterType.MAYOR,
                    confidence=1.0,
                ),
            ],
            [
                SubmitterAnalysisResult(
                    submitter_type=SubmitterType.POLITICIAN,
                    confidence=1.0,
                    matched_politician_id=5,
                    parsed_name="田中太郎",
                ),
            ],
        ]

        result = await use_case.execute([100, 200])
        assert result.success is True
        assert result.total_analyzed == 2
        assert result.total_matched == 2

    @pytest.mark.asyncio()
    async def test_exception_returns_failure(
        self,
        use_case: AnalyzeProposalSubmittersUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """例外発生時はfailure."""
        mock_repos["proposal_submitter"].get_by_proposal_ids.side_effect = Exception(
            "DB Error"
        )

        result = await use_case.execute([100])
        assert result.success is False
        assert "エラー" in result.message

    @pytest.mark.asyncio()
    async def test_comma_separated_creates_additional_submitters(
        self,
        use_case: AnalyzeProposalSubmittersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_analyzer: AsyncMock,
    ) -> None:
        """カンマ区切りで複数結果の場合、追加submitterが作成される."""
        submitter = _make_submitter(1, 100, "熊代昭彦,谷畑孝")
        mock_repos["proposal_submitter"].get_by_proposal_ids.return_value = {
            100: [submitter],
        }
        mock_repos["proposal"].get_by_ids.return_value = [_make_proposal(100)]

        mock_analyzer.analyze.return_value = [
            SubmitterAnalysisResult(
                submitter_type=SubmitterType.POLITICIAN,
                confidence=1.0,
                matched_politician_id=1,
                parsed_name="熊代昭彦",
            ),
            SubmitterAnalysisResult(
                submitter_type=SubmitterType.POLITICIAN,
                confidence=1.0,
                matched_politician_id=2,
                parsed_name="谷畑孝",
            ),
        ]

        result = await use_case.execute([100])
        assert result.success is True
        assert result.total_matched == 2
        mock_repos["proposal_submitter"].update.assert_called_once()
        mock_repos["proposal_submitter"].bulk_create.assert_called_once()
        created = mock_repos["proposal_submitter"].bulk_create.call_args[0][0]
        assert len(created) == 1
        assert created[0].raw_name == "谷畑孝"
        assert created[0].politician_id == 2

    @pytest.mark.asyncio()
    async def test_mixed_confidence_index_mapping(
        self,
        use_case: AnalyzeProposalSubmittersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_analyzer: AsyncMock,
    ) -> None:
        """低信頼度の結果がフィルタされてもインデックスが正しくマッピングされる."""
        submitter = _make_submitter(1, 100, "A,B,C")
        mock_repos["proposal_submitter"].get_by_proposal_ids.return_value = {
            100: [submitter],
        }
        mock_repos["proposal"].get_by_ids.return_value = [_make_proposal(100)]

        mock_analyzer.analyze.return_value = [
            SubmitterAnalysisResult(
                submitter_type=SubmitterType.POLITICIAN,
                confidence=1.0,
                matched_politician_id=1,
                parsed_name="A",
            ),
            # Bは低信頼度でフィルタされる
            SubmitterAnalysisResult(
                submitter_type=SubmitterType.OTHER,
                confidence=0.3,
                parsed_name="B",
            ),
            # Cは高信頼度で採用される
            SubmitterAnalysisResult(
                submitter_type=SubmitterType.POLITICIAN,
                confidence=1.0,
                matched_politician_id=3,
                parsed_name="C",
            ),
        ]

        result = await use_case.execute([100])
        assert result.success is True
        # A(update) + C(bulk_create) = 2件マッチ
        assert result.total_matched == 2
        mock_repos["proposal_submitter"].bulk_create.assert_called_once()
        created = mock_repos["proposal_submitter"].bulk_create.call_args[0][0]
        assert len(created) == 1
        assert created[0].raw_name == "C"
        assert created[0].politician_id == 3
        # resultsのanalysisも正しいことを確認
        assert len(result.results) == 2
        assert result.results[1].analysis.parsed_name == "C"
        assert result.results[1].analysis.matched_politician_id == 3

    @pytest.mark.asyncio()
    async def test_additional_submitters_have_incremental_display_order(
        self,
        use_case: AnalyzeProposalSubmittersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_analyzer: AsyncMock,
    ) -> None:
        """追加submitterのdisplay_orderが連番になる."""
        submitter = _make_submitter(1, 100, "A,B,C")
        submitter.display_order = 0
        mock_repos["proposal_submitter"].get_by_proposal_ids.return_value = {
            100: [submitter],
        }
        mock_repos["proposal"].get_by_ids.return_value = [_make_proposal(100)]

        mock_analyzer.analyze.return_value = [
            SubmitterAnalysisResult(
                submitter_type=SubmitterType.POLITICIAN,
                confidence=1.0,
                matched_politician_id=1,
                parsed_name="A",
            ),
            SubmitterAnalysisResult(
                submitter_type=SubmitterType.POLITICIAN,
                confidence=1.0,
                matched_politician_id=2,
                parsed_name="B",
            ),
            SubmitterAnalysisResult(
                submitter_type=SubmitterType.POLITICIAN,
                confidence=1.0,
                matched_politician_id=3,
                parsed_name="C",
            ),
        ]

        await use_case.execute([100])
        created = mock_repos["proposal_submitter"].bulk_create.call_args[0][0]
        assert len(created) == 2
        assert created[0].display_order == 1
        assert created[1].display_order == 2
