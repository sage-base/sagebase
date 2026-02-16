"""議案提出者の自動分析UseCase.

議案の提出者文字列を解析し、提出者種別の自動判定および
議員/会派マッチングを行う。
"""

from src.application.dtos.analyze_proposal_submitters_dto import (
    AnalyzeProposalSubmittersOutputDTO,
    SubmitterMatchResultDTO,
)
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

# マッチング結果を採用する最低信頼度
_MIN_MATCH_CONFIDENCE = 0.7


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

            # 議案情報をバッチ取得（N+1回避）
            proposals = await self._proposal_repository.get_by_ids(proposal_ids)
            proposal_conference_map: dict[int, int | None] = {
                p.id: p.conference_id for p in proposals if p.id is not None
            }

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

                    # 分析実行（list[SubmitterAnalysisResult]を返す）
                    analysis_results = await self._analyzer_service.analyze(
                        submitter.raw_name, conference_id
                    )

                    # 最初の結果で既存submitterを更新
                    if analysis_results:
                        first_updated = self._apply_analysis(
                            submitter, analysis_results[0]
                        )
                        if first_updated:
                            await self._proposal_submitter_repository.update(submitter)
                            total_matched += 1

                        results.append(
                            SubmitterMatchResultDTO(
                                submitter_id=submitter.id or 0,
                                raw_name=submitter.raw_name,
                                analysis=analysis_results[0],
                                updated=first_updated,
                            )
                        )

                    # 2件目以降の結果は新規ProposalSubmitterを作成
                    additional_pairs: list[
                        tuple[ProposalSubmitter, SubmitterAnalysisResult]
                    ] = []
                    for offset, analysis in enumerate(analysis_results[1:]):
                        new_submitter = self._create_additional_submitter(
                            submitter, analysis, display_offset=offset + 1
                        )
                        if new_submitter is not None:
                            additional_pairs.append((new_submitter, analysis))
                            total_matched += 1

                    if additional_pairs:
                        additional_submitters = [p[0] for p in additional_pairs]
                        await self._proposal_submitter_repository.bulk_create(
                            additional_submitters
                        )
                        for new_sub, analysis in additional_pairs:
                            results.append(
                                SubmitterMatchResultDTO(
                                    submitter_id=new_sub.id or 0,
                                    raw_name=new_sub.raw_name or "",
                                    analysis=analysis,
                                    updated=True,
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

    def _apply_analysis(
        self, submitter: ProposalSubmitter, analysis: SubmitterAnalysisResult
    ) -> bool:
        """分析結果をsubmitterに適用する."""
        if analysis.confidence < _MIN_MATCH_CONFIDENCE:
            return False

        updated = False
        submitter.submitter_type = analysis.submitter_type

        if analysis.matched_politician_id is not None:
            submitter.politician_id = analysis.matched_politician_id
            updated = True
        if analysis.matched_parliamentary_group_id is not None:
            submitter.parliamentary_group_id = analysis.matched_parliamentary_group_id
            updated = True
        if analysis.submitter_type in _MAYOR_OR_COMMITTEE_TYPES:
            updated = True

        return updated

    def _create_additional_submitter(
        self,
        original: ProposalSubmitter,
        analysis: SubmitterAnalysisResult,
        *,
        display_offset: int = 1,
    ) -> ProposalSubmitter | None:
        """追加の分析結果からProposalSubmitterを作成する."""
        if analysis.confidence < _MIN_MATCH_CONFIDENCE:
            return None

        new_submitter = ProposalSubmitter(
            proposal_id=original.proposal_id,
            submitter_type=analysis.submitter_type,
            politician_id=analysis.matched_politician_id,
            parliamentary_group_id=analysis.matched_parliamentary_group_id,
            raw_name=analysis.parsed_name,
            display_order=original.display_order + display_offset,
        )

        if analysis.submitter_type not in _MAYOR_OR_COMMITTEE_TYPES:
            if (
                analysis.matched_politician_id is None
                and analysis.matched_parliamentary_group_id is None
            ):
                return None

        return new_submitter

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
