"""SubmitterAnalysisResult値オブジェクトのテスト."""

import pytest

from src.domain.value_objects.submitter_analysis_result import (
    SubmitterAnalysisResult,
    SubmitterCandidate,
    SubmitterCandidateType,
)
from src.domain.value_objects.submitter_type import SubmitterType


class TestSubmitterCandidateType:
    """SubmitterCandidateTypeのテスト."""

    def test_politician_value(self) -> None:
        assert SubmitterCandidateType.POLITICIAN.value == "politician"

    def test_parliamentary_group_value(self) -> None:
        assert SubmitterCandidateType.PARLIAMENTARY_GROUP.value == "parliamentary_group"


class TestSubmitterCandidate:
    """SubmitterCandidateのテスト."""

    def test_create_politician_candidate(self) -> None:
        candidate = SubmitterCandidate(
            candidate_type=SubmitterCandidateType.POLITICIAN,
            entity_id=1,
            name="田中太郎",
            confidence=0.95,
        )
        assert candidate.candidate_type == SubmitterCandidateType.POLITICIAN
        assert candidate.entity_id == 1
        assert candidate.name == "田中太郎"
        assert candidate.confidence == 0.95

    def test_create_parliamentary_group_candidate(self) -> None:
        candidate = SubmitterCandidate(
            candidate_type=SubmitterCandidateType.PARLIAMENTARY_GROUP,
            entity_id=10,
            name="自由民主党",
            confidence=1.0,
        )
        assert candidate.candidate_type == SubmitterCandidateType.PARLIAMENTARY_GROUP
        assert candidate.entity_id == 10

    def test_frozen(self) -> None:
        """frozen=Trueにより属性変更不可."""
        candidate = SubmitterCandidate(
            candidate_type=SubmitterCandidateType.POLITICIAN,
            entity_id=1,
            name="test",
            confidence=0.9,
        )
        with pytest.raises(AttributeError):
            candidate.name = "changed"  # type: ignore[misc]


class TestSubmitterAnalysisResult:
    """SubmitterAnalysisResultのテスト."""

    def test_create_mayor_result(self) -> None:
        result = SubmitterAnalysisResult(
            submitter_type=SubmitterType.MAYOR,
            confidence=1.0,
        )
        assert result.submitter_type == SubmitterType.MAYOR
        assert result.confidence == 1.0
        assert result.matched_politician_id is None
        assert result.matched_parliamentary_group_id is None
        assert result.candidates == []

    def test_create_politician_result_with_candidates(self) -> None:
        candidates = [
            SubmitterCandidate(
                candidate_type=SubmitterCandidateType.POLITICIAN,
                entity_id=1,
                name="田中太郎",
                confidence=1.0,
            ),
            SubmitterCandidate(
                candidate_type=SubmitterCandidateType.POLITICIAN,
                entity_id=2,
                name="田中次郎",
                confidence=0.8,
            ),
        ]
        result = SubmitterAnalysisResult(
            submitter_type=SubmitterType.POLITICIAN,
            confidence=1.0,
            matched_politician_id=1,
            candidates=candidates,
        )
        assert result.matched_politician_id == 1
        assert len(result.candidates) == 2

    def test_create_parliamentary_group_result(self) -> None:
        result = SubmitterAnalysisResult(
            submitter_type=SubmitterType.PARLIAMENTARY_GROUP,
            confidence=1.0,
            matched_parliamentary_group_id=5,
            candidates=[
                SubmitterCandidate(
                    candidate_type=SubmitterCandidateType.PARLIAMENTARY_GROUP,
                    entity_id=5,
                    name="自由民主党",
                    confidence=1.0,
                ),
            ],
        )
        assert result.matched_parliamentary_group_id == 5

    def test_create_other_result(self) -> None:
        result = SubmitterAnalysisResult(
            submitter_type=SubmitterType.OTHER,
            confidence=0.0,
        )
        assert result.submitter_type == SubmitterType.OTHER
        assert result.confidence == 0.0
