"""議員団メンバーシップDTO

議員団メンバーシップに関連するDTOを定義します。
リポジトリコントラクトで使用されます。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from src.application.dtos.politician_dto import PoliticianOutputItem


if TYPE_CHECKING:
    from src.domain.entities.parliamentary_group import ParliamentaryGroup
    from src.domain.entities.parliamentary_group_membership import (
        ParliamentaryGroupMembership,
    )


@dataclass
class ParliamentaryGroupMembershipOutputItem:
    """議員団メンバーシップの出力アイテム."""

    id: int | None
    politician_id: int
    parliamentary_group_id: int
    start_date: date
    end_date: date | None
    role: str | None
    created_by_user_id: UUID | None
    is_manually_verified: bool
    latest_extraction_log_id: int | None
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_entity(
        cls, entity: ParliamentaryGroupMembership
    ) -> ParliamentaryGroupMembershipOutputItem:
        """エンティティから出力アイテムを生成する."""
        return cls(
            id=entity.id,
            politician_id=entity.politician_id,
            parliamentary_group_id=entity.parliamentary_group_id,
            start_date=entity.start_date,
            end_date=entity.end_date,
            role=entity.role,
            created_by_user_id=entity.created_by_user_id,
            is_manually_verified=entity.is_manually_verified,
            latest_extraction_log_id=entity.latest_extraction_log_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


@dataclass
class ParliamentaryGroupOutputItem:
    """議員団（会派）の出力アイテム."""

    id: int | None
    name: str
    governing_body_id: int
    url: str | None
    description: str | None
    is_active: bool

    @classmethod
    def from_entity(cls, entity: ParliamentaryGroup) -> ParliamentaryGroupOutputItem:
        """エンティティから出力アイテムを生成する."""
        return cls(
            id=entity.id,
            name=entity.name,
            governing_body_id=entity.governing_body_id,
            url=entity.url,
            description=entity.description,
            is_active=entity.is_active,
        )


@dataclass
class ParliamentaryGroupMembershipWithRelationsDTO:
    """議員団メンバーシップと関連エンティティのDTO

    議員団メンバーシップを関連する政治家・議員団データと一緒に
    取得する際に使用します。ドメインエンティティへの動的属性
    追加を避けることでClean Architectureを維持します。
    """

    membership: ParliamentaryGroupMembershipOutputItem
    politician: PoliticianOutputItem | None
    parliamentary_group: ParliamentaryGroupOutputItem | None
