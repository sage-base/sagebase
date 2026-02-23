"""政党所属履歴のDTO."""

from dataclasses import dataclass
from datetime import date, datetime

from src.domain.entities.party_membership_history import PartyMembershipHistory


@dataclass
class PartyMembershipHistoryOutputItem:
    """政党所属履歴の出力アイテム."""

    id: int | None
    politician_id: int
    political_party_id: int
    start_date: date
    end_date: date | None
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_entity(
        cls, entity: PartyMembershipHistory
    ) -> "PartyMembershipHistoryOutputItem":
        return cls(
            id=entity.id,
            politician_id=entity.politician_id,
            political_party_id=entity.political_party_id,
            start_date=entity.start_date,
            end_date=entity.end_date,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


@dataclass
class GetHistoryByPoliticianInputDto:
    """政治家別の所属履歴取得の入力DTO."""

    politician_id: int


@dataclass
class GetHistoryByPoliticianOutputDto:
    """政治家別の所属履歴取得の出力DTO."""

    items: list[PartyMembershipHistoryOutputItem]


@dataclass
class GetCurrentPartyInputDto:
    """現在の政党所属取得の入力DTO."""

    politician_id: int
    as_of_date: date | None = None


@dataclass
class GetCurrentPartyOutputDto:
    """現在の政党所属取得の出力DTO."""

    item: PartyMembershipHistoryOutputItem | None


@dataclass
class CreateMembershipInputDto:
    """所属履歴作成の入力DTO."""

    politician_id: int
    political_party_id: int
    start_date: date
    end_date: date | None = None


@dataclass
class CreateMembershipOutputDto:
    """所属履歴作成の出力DTO."""

    success: bool
    message: str
    item: PartyMembershipHistoryOutputItem | None = None


@dataclass
class EndMembershipInputDto:
    """所属終了の入力DTO."""

    membership_id: int
    end_date: date


@dataclass
class EndMembershipOutputDto:
    """所属終了の出力DTO."""

    success: bool
    message: str
    item: PartyMembershipHistoryOutputItem | None = None
