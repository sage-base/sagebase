"""選挙結果メンバー管理に関するDTO.

このモジュールは選挙結果メンバー管理に関するDTOを定義します。
ManageElectionMembersUseCaseから移動。
"""

from dataclasses import dataclass

from src.domain.entities import ElectionMember


# =============================================================================
# Output Item
# =============================================================================


@dataclass
class ElectionMemberOutputItem:
    """選挙結果メンバーの出力アイテム."""

    id: int | None
    election_id: int
    politician_id: int
    result: str
    votes: int | None
    rank: int | None

    @classmethod
    def from_entity(cls, entity: ElectionMember) -> "ElectionMemberOutputItem":
        """エンティティから出力アイテムを生成する."""
        return cls(
            id=entity.id,
            election_id=entity.election_id,
            politician_id=entity.politician_id,
            result=entity.result,
            votes=entity.votes,
            rank=entity.rank,
        )


# =============================================================================
# Input DTOs
# =============================================================================


@dataclass
class ListElectionMembersByElectionInputDto:
    """選挙ID別メンバー一覧取得の入力DTO."""

    election_id: int


@dataclass
class ListElectionMembersByPoliticianInputDto:
    """政治家ID別選挙結果一覧取得の入力DTO."""

    politician_id: int


@dataclass
class CreateElectionMemberInputDto:
    """選挙結果メンバー作成の入力DTO."""

    election_id: int
    politician_id: int
    result: str
    votes: int | None = None
    rank: int | None = None


@dataclass
class UpdateElectionMemberInputDto:
    """選挙結果メンバー更新の入力DTO."""

    id: int
    election_id: int
    politician_id: int
    result: str
    votes: int | None = None
    rank: int | None = None


@dataclass
class DeleteElectionMemberInputDto:
    """選挙結果メンバー削除の入力DTO."""

    id: int


# =============================================================================
# Output DTOs
# =============================================================================


@dataclass
class ListElectionMembersOutputDto:
    """選挙結果メンバー一覧取得の出力DTO."""

    election_members: list[ElectionMemberOutputItem]
    success: bool = True
    error_message: str | None = None


@dataclass
class CreateElectionMemberOutputDto:
    """選挙結果メンバー作成の出力DTO."""

    success: bool
    election_member_id: int | None = None
    error_message: str | None = None


@dataclass
class UpdateElectionMemberOutputDto:
    """選挙結果メンバー更新の出力DTO."""

    success: bool
    error_message: str | None = None


@dataclass
class DeleteElectionMemberOutputDto:
    """選挙結果メンバー削除の出力DTO."""

    success: bool
    error_message: str | None = None
