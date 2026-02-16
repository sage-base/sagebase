"""議案提出者の自動分析UseCase.

議案の提出者文字列を解析し、提出者種別の自動判定および
議員/会派マッチングを行う。
"""

from dataclasses import dataclass, field

from src.common.logging import get_logger
from src.domain.entities.proposal_submitter import ProposalSubmitter
from src.domain.repositories.proposal_repository import ProposalRepository
from src.domain.repositories.proposal_submitter_repository import (
    ProposalSubmitterRepository,
)
from src.domain.services.interfaces.proposal_submitter_analyzer_service import (
    IProposalSubmitterAnalyzerService,
)
from src.domain.value_objects.submitter_analysis_result import SubmitterAnalysisResult
from src.domain.value_objects.submitter_type import SubmitterType


_MAYOR_OR_COMMITTEE_TYPES = {SubmitterType.MAYOR, SubmitterType.COMMITTEE}


@dataclass
class SubmitterMatchResultDTO:
    """提出者1件の分析結果DTO."""

    submitter_id: int
    raw_name: str
    analysis: SubmitterAnalysisResult
    updated: bool


@dataclass
class AnalyzeProposalSubmittersOutputDTO:
    """提出者一括分析の結果DTO."""

    success: bool
    message: str
    total_analyzed: int = 0
    total_matched: int = 0
    results: list[SubmitterMatchResultDTO] = field(default_factory=list)


class AnalyzeProposalSubmittersUseCase:
    """議案提出者の自動分析UseCase.

    複数議案の未マッチ提出者を一括分析し、マッチング結果を保存する。
    """

    def __init__(
        self,
        proposal_repository: ProposalRepository,
        proposal_submitter_repository: ProposalSubmitterRepository,
        analyzer_service: IProposalSubmitterAnalyzerService,
    ) -> None:
        self._proposal_repository = proposal_repository
        self._proposal_submitter_repository = proposal_submitter_repository
        self._analyzer_service = analyzer_service
        self._logger = get_logger(self.__class__.__name__)

    async def execute(
        self, proposal_ids: list[int]
    ) -> AnalyzeProposalSubmittersOutputDTO:
        """指定された議案の未マッチ提出者を一括分析する.

        Args:
            proposal_ids: 分析対象の議案IDリスト

        Returns:
            分析結果DTO
        """
        if not proposal_ids:
            return AnalyzeProposalSubmittersOutputDTO(
                success=True,
                message="分析対象の議案がありません",
            )

        try:
            # 議案の提出者を一括取得
            submitters_by_proposal = (
                await self._proposal_submitter_repository.get_by_proposal_ids(
                    proposal_ids
                )
            )

            # 議案情報をキャッシュ（conference_id取得用）
            proposal_conference_map: dict[int, int | None] = {}
            for proposal_id in proposal_ids:
                proposal = await self._proposal_repository.get_by_id(proposal_id)
                if proposal:
                    proposal_conference_map[proposal_id] = proposal.conference_id

            results: list[SubmitterMatchResultDTO] = []
            total_analyzed = 0
            total_matched = 0

            for proposal_id, submitters in submitters_by_proposal.items():
                conference_id = proposal_conference_map.get(proposal_id)
                if conference_id is None:
                    self._logger.warning(
                        f"議案ID {proposal_id} のconference_idが未設定です"
                    )
                    continue

                for submitter in submitters:
                    # raw_nameがない場合はスキップ
                    if not submitter.raw_name:
                        continue

                    # 分析不要な場合はスキップ
                    if not self._needs_analysis(submitter):
                        continue

                    total_analyzed += 1

                    # 分析実行
                    analysis = await self._analyzer_service.analyze(
                        submitter.raw_name, conference_id
                    )

                    # 結果に基づいてエンティティを更新
                    updated = False
                    if analysis.confidence >= 0.7:
                        submitter.submitter_type = analysis.submitter_type
                        if analysis.matched_politician_id is not None:
                            submitter.politician_id = analysis.matched_politician_id
                            updated = True
                        if analysis.matched_parliamentary_group_id is not None:
                            submitter.parliamentary_group_id = (
                                analysis.matched_parliamentary_group_id
                            )
                            updated = True
                        # MAYOR/COMMITTEEの場合はtype設定のみで更新
                        if analysis.submitter_type in _MAYOR_OR_COMMITTEE_TYPES:
                            updated = True

                        if updated:
                            await self._proposal_submitter_repository.update(submitter)
                            total_matched += 1

                    results.append(
                        SubmitterMatchResultDTO(
                            submitter_id=submitter.id or 0,
                            raw_name=submitter.raw_name,
                            analysis=analysis,
                            updated=updated,
                        )
                    )

            return AnalyzeProposalSubmittersOutputDTO(
                success=True,
                message=(
                    f"{total_analyzed}件の提出者を分析し、"
                    f"{total_matched}件をマッチングしました"
                ),
                total_analyzed=total_analyzed,
                total_matched=total_matched,
                results=results,
            )

        except Exception as e:
            self._logger.error(f"提出者分析エラー: {e}", exc_info=True)
            return AnalyzeProposalSubmittersOutputDTO(
                success=False,
                message=f"分析中にエラーが発生しました: {e!s}",
            )

    @staticmethod
    def _needs_analysis(submitter: ProposalSubmitter) -> bool:
        """提出者が分析を必要とするかを判定する.

        - OTHER（未分類）: 分析が必要
        - POLITICIAN: politician_idが未設定なら分析が必要
        - PARLIAMENTARY_GROUP: parliamentary_group_idが未設定なら分析が必要
        - MAYOR, COMMITTEE: 分析不要（キーワードで確定済み）
        """
        if submitter.submitter_type == SubmitterType.OTHER:
            return True
        if submitter.submitter_type == SubmitterType.POLITICIAN:
            return submitter.politician_id is None
        if submitter.submitter_type == SubmitterType.PARLIAMENTARY_GROUP:
            return submitter.parliamentary_group_id is None
        return False
