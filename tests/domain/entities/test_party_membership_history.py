"""PartyMembershipHistory エンティティのテスト."""

from datetime import date, datetime

from src.domain.entities.party_membership_history import PartyMembershipHistory


class TestPartyMembershipHistory:
    def test_initialization_with_required_fields(self) -> None:
        membership = PartyMembershipHistory(
            politician_id=1,
            political_party_id=2,
            start_date=date(2024, 1, 1),
        )

        assert membership.politician_id == 1
        assert membership.political_party_id == 2
        assert membership.start_date == date(2024, 1, 1)
        assert membership.end_date is None
        assert membership.created_at is None
        assert membership.updated_at is None
        assert membership.id is None

    def test_initialization_with_all_fields(self) -> None:
        created_time = datetime(2024, 1, 1, 10, 0, 0)
        updated_time = datetime(2024, 1, 15, 14, 30, 0)

        membership = PartyMembershipHistory(
            id=10,
            politician_id=5,
            political_party_id=3,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            created_at=created_time,
            updated_at=updated_time,
        )

        assert membership.id == 10
        assert membership.politician_id == 5
        assert membership.political_party_id == 3
        assert membership.start_date == date(2024, 1, 1)
        assert membership.end_date == date(2024, 12, 31)
        assert membership.created_at == created_time
        assert membership.updated_at == updated_time

    def test_is_active_current_membership(self) -> None:
        membership = PartyMembershipHistory(
            politician_id=1,
            political_party_id=2,
            start_date=date(2024, 1, 1),
            end_date=None,
        )

        assert membership.is_active() is True
        assert membership.is_active(date.today()) is True

    def test_is_active_with_end_date_in_future(self) -> None:
        membership = PartyMembershipHistory(
            politician_id=1,
            political_party_id=2,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert membership.is_active(date(2024, 6, 15)) is True
        assert membership.is_active(date(2024, 1, 1)) is True
        assert membership.is_active(date(2024, 12, 31)) is True

    def test_is_active_with_end_date_in_past(self) -> None:
        membership = PartyMembershipHistory(
            politician_id=1,
            political_party_id=2,
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
        )

        assert membership.is_active() is False
        assert membership.is_active(date(2021, 1, 1)) is False

    def test_is_active_before_start_date(self) -> None:
        membership = PartyMembershipHistory(
            politician_id=1,
            political_party_id=2,
            start_date=date(2024, 6, 1),
            end_date=None,
        )

        assert membership.is_active(date(2024, 5, 31)) is False

    def test_overlaps_with_no_overlap(self) -> None:
        membership = PartyMembershipHistory(
            politician_id=1,
            political_party_id=2,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert membership.overlaps_with(date(2023, 1, 1), date(2023, 12, 31)) is False
        assert membership.overlaps_with(date(2025, 1, 1), date(2025, 12, 31)) is False

    def test_overlaps_with_full_overlap(self) -> None:
        membership = PartyMembershipHistory(
            politician_id=1,
            political_party_id=2,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert membership.overlaps_with(date(2023, 1, 1), date(2025, 12, 31)) is True
        assert membership.overlaps_with(date(2024, 1, 1), date(2024, 12, 31)) is True

    def test_overlaps_with_partial_overlap(self) -> None:
        membership = PartyMembershipHistory(
            politician_id=1,
            political_party_id=2,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert membership.overlaps_with(date(2023, 6, 1), date(2024, 6, 30)) is True
        assert membership.overlaps_with(date(2024, 6, 1), date(2025, 6, 30)) is True

    def test_overlaps_with_no_end_date(self) -> None:
        membership = PartyMembershipHistory(
            politician_id=1,
            political_party_id=2,
            start_date=date(2024, 1, 1),
            end_date=None,
        )

        assert membership.overlaps_with(date(2024, 6, 1), date(2024, 12, 31)) is True
        assert membership.overlaps_with(date(2025, 1, 1), date(2025, 12, 31)) is True
        assert membership.overlaps_with(date(2023, 1, 1), date(2023, 12, 31)) is False

    def test_overlaps_with_no_range_end_date(self) -> None:
        membership = PartyMembershipHistory(
            politician_id=1,
            political_party_id=2,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert membership.overlaps_with(date(2024, 6, 1), None) is True
        assert membership.overlaps_with(date(2025, 1, 1), None) is False

    def test_inheritance_from_base_entity(self) -> None:
        membership = PartyMembershipHistory(
            id=42,
            politician_id=1,
            political_party_id=2,
            start_date=date(2024, 1, 1),
        )
        assert membership.id == 42

        membership_no_id = PartyMembershipHistory(
            politician_id=1,
            political_party_id=2,
            start_date=date(2024, 1, 1),
        )
        assert membership_no_id.id is None

    def test_same_start_and_end_date(self) -> None:
        same_day = PartyMembershipHistory(
            politician_id=1,
            political_party_id=2,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
        )
        assert same_day.is_active(date(2024, 1, 1)) is True
        assert same_day.is_active(date(2024, 1, 2)) is False

    def test_politician_changes_parties(self) -> None:
        politician_id = 10

        first = PartyMembershipHistory(
            politician_id=politician_id,
            political_party_id=1,
            start_date=date(2020, 1, 1),
            end_date=date(2022, 12, 31),
        )
        second = PartyMembershipHistory(
            politician_id=politician_id,
            political_party_id=2,
            start_date=date(2023, 1, 1),
            end_date=None,
        )

        assert first.is_active(date(2021, 6, 1)) is True
        assert first.is_active(date(2023, 6, 1)) is False
        assert second.is_active(date(2021, 6, 1)) is False
        assert second.is_active(date(2023, 6, 1)) is True
