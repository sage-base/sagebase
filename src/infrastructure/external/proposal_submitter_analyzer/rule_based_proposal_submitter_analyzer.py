"""ルールベースの議案提出者分析サービス.

キーワード判定と名前マッチングにより、提出者文字列の種別判定および
議員/会派とのマッチングを行う。LLMは使用しない。
"""

from src.common.logging import get_logger
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.repositories.conference_member_repository import (
    ConferenceMemberRepository,
)
from src.domain.repositories.conference_repository import ConferenceRepository
from src.domain.repositories.parliamentary_group_repository import (
    ParliamentaryGroupRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.services.proposal_judge_extraction_service import (
    ProposalJudgeExtractionService,
)
from src.domain.services.submitter_string_parser import parse_submitter_string
from src.domain.value_objects.submitter_analysis_result import (
    SubmitterAnalysisResult,
    SubmitterCandidate,
    SubmitterCandidateType,
)
from src.domain.value_objects.submitter_type import SubmitterType


# 市長系キーワード（長いものを先にチェック）
_MAYOR_KEYWORDS = [
    "内閣総理大臣",
    "副市長",
    "副町長",
    "副村長",
    "副区長",
    "副知事",
    "内閣",
    "市長",
    "町長",
    "村長",
    "区長",
    "知事",
]

# 委員会系キーワード
_COMMITTEE_KEYWORDS = [
    "委員会",
    "委員長",
]

# 候補として採用する最低信頼度
_MIN_CANDIDATE_CONFIDENCE = 0.7


class RuleBasedProposalSubmitterAnalyzer:
    """ルールベースの議案提出者分析サービス.

    IProposalSubmitterAnalyzerServiceのProtocolに適合する。
    """

    def __init__(
        self,
        politician_repository: PoliticianRepository,
        conference_member_repository: ConferenceMemberRepository,
        parliamentary_group_repository: ParliamentaryGroupRepository,
        conference_repository: ConferenceRepository,
    ) -> None:
        self._politician_repository = politician_repository
        self._conference_member_repository = conference_member_repository
        self._parliamentary_group_repository = parliamentary_group_repository
        self._conference_repository = conference_repository
        self._logger = get_logger(self.__class__.__name__)

    async def analyze(
        self,
        submitter_name: str,
        conference_id: int,
    ) -> list[SubmitterAnalysisResult]:
        """提出者文字列を解析してマッチングする.

        提出者文字列をパースし、各名前に対して種別判定・マッチングを行う。
        カンマ区切りの場合は複数の結果を返す。
        """
        raw = submitter_name.strip()
        if not raw:
            return [
                SubmitterAnalysisResult(
                    submitter_type=SubmitterType.OTHER,
                    confidence=0.0,
                )
            ]

        # パース前にMAYOR/COMMITTEE判定（raw_name全体で判定）
        mayor_result = self._check_mayor(raw)
        if mayor_result is not None:
            return [mayor_result]

        committee_result = self._check_committee(raw)
        if committee_result is not None:
            return [committee_result]

        # 提出者文字列をパース
        parsed = parse_submitter_string(raw)
        if not parsed.names:
            return [
                SubmitterAnalysisResult(
                    submitter_type=SubmitterType.OTHER,
                    confidence=0.0,
                )
            ]

        # 各名前に対して個別分析
        results: list[SubmitterAnalysisResult] = []
        for name in parsed.names:
            result = await self._analyze_single_name(name, conference_id)
            results.append(result)

        return results

    async def _analyze_single_name(
        self, name: str, conference_id: int
    ) -> SubmitterAnalysisResult:
        """単一の名前に対して種別判定・マッチングを行う."""
        if not name:
            return SubmitterAnalysisResult(
                submitter_type=SubmitterType.OTHER,
                confidence=0.0,
                parsed_name=name,
            )

        # MAYOR判定（パース後の個別名前でも再チェック）
        mayor_result = self._check_mayor(name)
        if mayor_result is not None:
            return SubmitterAnalysisResult(
                submitter_type=mayor_result.submitter_type,
                confidence=mayor_result.confidence,
                parsed_name=name,
            )

        # COMMITTEE判定
        committee_result = self._check_committee(name)
        if committee_result is not None:
            return SubmitterAnalysisResult(
                submitter_type=committee_result.submitter_type,
                confidence=committee_result.confidence,
                parsed_name=name,
            )

        # 会派マッチング
        pg_result = await self._match_parliamentary_group(name, conference_id)
        if pg_result is not None:
            return SubmitterAnalysisResult(
                submitter_type=pg_result.submitter_type,
                confidence=pg_result.confidence,
                matched_parliamentary_group_id=pg_result.matched_parliamentary_group_id,
                parsed_name=name,
                candidates=pg_result.candidates,
            )

        # 議員マッチング
        politician_result = await self._match_politician(name, conference_id)
        if politician_result is not None:
            return SubmitterAnalysisResult(
                submitter_type=politician_result.submitter_type,
                confidence=politician_result.confidence,
                matched_politician_id=politician_result.matched_politician_id,
                parsed_name=name,
                candidates=politician_result.candidates,
            )

        # 判定不能
        return SubmitterAnalysisResult(
            submitter_type=SubmitterType.OTHER,
            confidence=0.0,
            parsed_name=name,
        )

    def _check_mayor(self, name: str) -> SubmitterAnalysisResult | None:
        """市長系キーワードで判定する."""
        for keyword in _MAYOR_KEYWORDS:
            if name == keyword or name.endswith(keyword):
                return SubmitterAnalysisResult(
                    submitter_type=SubmitterType.MAYOR,
                    confidence=1.0,
                    parsed_name=name,
                )
        return None

    def _check_committee(self, name: str) -> SubmitterAnalysisResult | None:
        """委員会系キーワードで判定する."""
        for keyword in _COMMITTEE_KEYWORDS:
            if keyword in name:
                return SubmitterAnalysisResult(
                    submitter_type=SubmitterType.COMMITTEE,
                    confidence=1.0,
                    parsed_name=name,
                )
        return None

    async def _match_parliamentary_group(
        self, name: str, conference_id: int
    ) -> SubmitterAnalysisResult | None:
        """会派名マッチングを行う."""
        groups = await self._get_parliamentary_groups(conference_id)
        if not groups:
            return None

        normalized_name = _normalize_name(name)
        candidates: list[SubmitterCandidate] = []

        for group in groups:
            if group.id is None:
                continue
            confidence = _calculate_group_confidence(normalized_name, group.name)
            if confidence >= _MIN_CANDIDATE_CONFIDENCE:
                candidates.append(
                    SubmitterCandidate(
                        candidate_type=SubmitterCandidateType.PARLIAMENTARY_GROUP,
                        entity_id=group.id,
                        name=group.name,
                        confidence=confidence,
                    )
                )

        if not candidates:
            return None

        # 信頼度降順でソート
        candidates.sort(key=lambda c: c.confidence, reverse=True)
        best = candidates[0]

        return SubmitterAnalysisResult(
            submitter_type=SubmitterType.PARLIAMENTARY_GROUP,
            confidence=best.confidence,
            matched_parliamentary_group_id=best.entity_id,
            parsed_name=name,
            candidates=candidates,
        )

    async def _match_politician(
        self, name: str, conference_id: int
    ) -> SubmitterAnalysisResult | None:
        """議員名マッチングを行う."""
        # 会議体メンバーを一括取得
        members = await self._conference_member_repository.get_by_conference(
            conference_id, active_only=True
        )
        if not members:
            return None

        # 議員情報をバッチ取得（N+1回避）
        politician_ids = [m.politician_id for m in members]
        politicians = await self._politician_repository.get_by_ids(politician_ids)
        if not politicians:
            return None

        normalized_name = _normalize_name(name)
        candidates: list[SubmitterCandidate] = []

        for politician in politicians:
            if politician.id is None:
                continue
            confidence = ProposalJudgeExtractionService.calculate_matching_confidence(
                normalized_name, politician.name
            )
            if confidence >= _MIN_CANDIDATE_CONFIDENCE:
                candidates.append(
                    SubmitterCandidate(
                        candidate_type=SubmitterCandidateType.POLITICIAN,
                        entity_id=politician.id,
                        name=politician.name,
                        confidence=confidence,
                    )
                )

        if not candidates:
            return None

        # 信頼度降順でソート
        candidates.sort(key=lambda c: c.confidence, reverse=True)
        best = candidates[0]

        return SubmitterAnalysisResult(
            submitter_type=SubmitterType.POLITICIAN,
            confidence=best.confidence,
            matched_politician_id=best.entity_id,
            parsed_name=name,
            candidates=candidates,
        )

    async def _get_parliamentary_groups(
        self, conference_id: int
    ) -> list[ParliamentaryGroup]:
        """会議体IDからgoverning_body_idを解決して会派一覧を取得する."""
        conference = await self._conference_repository.get_by_id(conference_id)
        if not conference:
            self._logger.warning(f"会議体ID {conference_id} が見つかりません")
            return []
        groups = await self._parliamentary_group_repository.get_by_governing_body_id(
            conference.governing_body_id, active_only=True
        )
        return list(groups)


def _normalize_name(name: str) -> str:
    """名前を正規化する（敬称除去・スペース正規化）."""
    return ProposalJudgeExtractionService.normalize_politician_name(name)


def _calculate_group_confidence(normalized_name: str, group_name: str) -> float:
    """会派名のマッチング信頼度を計算する."""
    normalized_group = _normalize_name(group_name)

    # 完全一致
    if normalized_name == normalized_group:
        return 1.0

    # 一方が他方を含む（部分一致）
    if normalized_name in normalized_group or normalized_group in normalized_name:
        return 0.8

    # 文字の共通率
    common_chars = sum(1 for c in normalized_name if c in normalized_group)
    max_len = max(len(normalized_name), len(normalized_group))
    if max_len == 0:
        return 0.0

    return common_chars / max_len
