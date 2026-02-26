"""Tests for ParliamentaryGroupParty entity."""

from src.domain.entities.base import BaseEntity
from src.domain.entities.parliamentary_group_party import ParliamentaryGroupParty


class TestParliamentaryGroupParty:
    """Test cases for ParliamentaryGroupParty entity."""

    def test_initialization_with_required_fields(self) -> None:
        entity = ParliamentaryGroupParty(
            parliamentary_group_id=1,
            political_party_id=2,
        )

        assert entity.parliamentary_group_id == 1
        assert entity.political_party_id == 2
        assert entity.is_primary is False
        assert entity.id is None

    def test_initialization_with_all_fields(self) -> None:
        entity = ParliamentaryGroupParty(
            id=10,
            parliamentary_group_id=5,
            political_party_id=3,
            is_primary=True,
        )

        assert entity.id == 10
        assert entity.parliamentary_group_id == 5
        assert entity.political_party_id == 3
        assert entity.is_primary is True

    def test_is_primary_default_false(self) -> None:
        entity = ParliamentaryGroupParty(
            parliamentary_group_id=1,
            political_party_id=1,
        )
        assert entity.is_primary is False

    def test_is_primary_explicit_true(self) -> None:
        entity = ParliamentaryGroupParty(
            parliamentary_group_id=1,
            political_party_id=1,
            is_primary=True,
        )
        assert entity.is_primary is True

    def test_inherits_from_base_entity(self) -> None:
        entity = ParliamentaryGroupParty(
            parliamentary_group_id=1,
            political_party_id=1,
            id=42,
        )
        assert isinstance(entity, BaseEntity)
        assert entity.id == 42

    def test_base_entity_timestamps(self) -> None:
        entity = ParliamentaryGroupParty(
            parliamentary_group_id=1,
            political_party_id=1,
        )
        assert entity.created_at is None
        assert entity.updated_at is None

    def test_equality_by_id(self) -> None:
        entity1 = ParliamentaryGroupParty(
            parliamentary_group_id=1,
            political_party_id=2,
            id=1,
        )
        entity2 = ParliamentaryGroupParty(
            parliamentary_group_id=3,
            political_party_id=4,
            id=1,
        )
        assert entity1 == entity2

    def test_inequality_by_id(self) -> None:
        entity1 = ParliamentaryGroupParty(
            parliamentary_group_id=1,
            political_party_id=2,
            id=1,
        )
        entity2 = ParliamentaryGroupParty(
            parliamentary_group_id=1,
            political_party_id=2,
            id=2,
        )
        assert entity1 != entity2

    def test_multiple_parties_per_group(self) -> None:
        primary = ParliamentaryGroupParty(
            parliamentary_group_id=10,
            political_party_id=1,
            is_primary=True,
            id=1,
        )
        secondary = ParliamentaryGroupParty(
            parliamentary_group_id=10,
            political_party_id=2,
            is_primary=False,
            id=2,
        )
        assert primary.parliamentary_group_id == secondary.parliamentary_group_id
        assert primary.is_primary is True
        assert secondary.is_primary is False
