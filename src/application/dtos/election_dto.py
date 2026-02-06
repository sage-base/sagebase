"""選挙管理に関するDTO.

このモジュールは選挙管理に関するDTOを定義します。
ManageElectionsUseCaseから移動。
"""

from dataclasses import dataclass
from datetime import date

from src.domain.entities import Election


# =============================================================================
# Input DTOs
# =============================================================================


@dataclass
class ListElectionsInputDto:
    """選挙一覧取得の入力DTO."""

    governing_body_id: int


@dataclass
class CreateElectionInputDto:
    """選挙作成の入力DTO."""

    governing_body_id: int
    term_number: int
    election_date: date
    election_type: str | None = None


@dataclass
class UpdateElectionInputDto:
    """選挙更新の入力DTO."""

    id: int
    governing_body_id: int
    term_number: int
    election_date: date
    election_type: str | None = None


@dataclass
class DeleteElectionInputDto:
    """選挙削除の入力DTO."""

    id: int


# =============================================================================
# Output DTOs
# =============================================================================


@dataclass
class ElectionOutputItem:
    """選挙の出力アイテム."""

    id: int | None
    governing_body_id: int
    term_number: int
    election_date: date
    election_type: str | None

    @classmethod
    def from_entity(cls, entity: Election) -> "ElectionOutputItem":
        """エンティティから出力アイテムを生成する."""
        return cls(
            id=entity.id,
            governing_body_id=entity.governing_body_id,
            term_number=entity.term_number,
            election_date=entity.election_date,
            election_type=entity.election_type,
        )


@dataclass
class ListElectionsOutputDto:
    """選挙一覧取得の出力DTO."""

    elections: list[ElectionOutputItem]
    success: bool = True
    error_message: str | None = None


@dataclass
class CreateElectionOutputDto:
    """選挙作成の出力DTO."""

    success: bool
    election_id: int | None = None
    error_message: str | None = None


@dataclass
class UpdateElectionOutputDto:
    """選挙更新の出力DTO."""

    success: bool
    error_message: str | None = None


@dataclass
class DeleteElectionOutputDto:
    """選挙削除の出力DTO."""

    success: bool
    error_message: str | None = None


@dataclass
class GenerateSeedFileOutputDto:
    """SEEDファイル生成の出力DTO."""

    success: bool
    seed_content: str | None = None
    file_path: str | None = None
    error_message: str | None = None
