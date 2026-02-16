"""議案提出者分析結果のDTO."""

from dataclasses import dataclass, field

from src.domain.value_objects.submitter_analysis_result import SubmitterAnalysisResult


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
