"""提出者分析結果を表す値オブジェクト."""

from dataclasses import dataclass, field
from enum import Enum

from src.domain.value_objects.submitter_type import SubmitterType


class SubmitterCandidateType(Enum):
    """提出者候補の種別."""

    POLITICIAN = "politician"
    PARLIAMENTARY_GROUP = "parliamentary_group"


@dataclass(frozen=True)
class SubmitterCandidate:
    """提出者候補を表す値オブジェクト.

    マッチング処理で見つかった候補を表す。
    """

    candidate_type: SubmitterCandidateType
    entity_id: int
    name: str
    confidence: float


@dataclass(frozen=True)
class SubmitterAnalysisResult:
    """提出者分析結果を表す値オブジェクト.

    提出者文字列の解析結果として、種別判定・マッチング結果・候補一覧を保持する。
    """

    submitter_type: SubmitterType
    confidence: float
    matched_politician_id: int | None = None
    matched_parliamentary_group_id: int | None = None
    candidates: list[SubmitterCandidate] = field(default_factory=list)
