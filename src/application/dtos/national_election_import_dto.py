"""国政選挙データインポート用DTO."""

from dataclasses import dataclass, field

from src.domain.value_objects.election_candidate import (
    CandidateRecord,
    ElectionInfo,
)


# ドメイン値オブジェクトを再エクスポート（後方互換性）
__all__ = ["CandidateRecord", "ElectionInfo"]


@dataclass
class ImportNationalElectionInputDto:
    """国政選挙インポートの入力DTO."""

    election_number: int
    governing_body_id: int
    dry_run: bool = False


@dataclass
class ImportNationalElectionOutputDto:
    """国政選挙インポートの出力DTO."""

    election_number: int
    election_id: int | None = None
    total_candidates: int = 0
    matched_politicians: int = 0
    created_politicians: int = 0
    created_parties: int = 0
    skipped_ambiguous: int = 0
    skipped_duplicate: int = 0
    election_members_created: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)
