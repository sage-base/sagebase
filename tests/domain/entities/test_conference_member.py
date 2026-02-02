"""Tests for ConferenceMember entity."""

from datetime import date

from tests.fixtures.entity_factories import create_conference_member

from src.domain.entities.conference_member import ConferenceMember


class TestConferenceMember:
    """Test cases for ConferenceMember entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        member = ConferenceMember(
            politician_id=1, conference_id=2, start_date=date(2023, 1, 1)
        )

        assert member.politician_id == 1
        assert member.conference_id == 2
        assert member.start_date == date(2023, 1, 1)
        assert member.end_date is None
        assert member.role is None
        assert member.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        member = ConferenceMember(
            id=1,
            politician_id=10,
            conference_id=20,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            role="議長",
        )

        assert member.id == 1
        assert member.politician_id == 10
        assert member.conference_id == 20
        assert member.start_date == date(2023, 1, 1)
        assert member.end_date == date(2023, 12, 31)
        assert member.role == "議長"

    def test_is_active_method(self) -> None:
        """Test is_active method for current and ended memberships."""
        # Test active membership (no end date)
        active_member = create_conference_member(end_date=None)
        assert active_member.is_active() is True

        # Test ended membership
        ended_member = create_conference_member(end_date=date(2023, 12, 31))
        assert ended_member.is_active() is False

    def test_str_representation_active(self) -> None:
        """Test string representation for active membership."""
        member = create_conference_member(
            politician_id=5, conference_id=10, end_date=None
        )

        expected = "ConferenceMember(politician=5, conference=10, active)"
        assert str(member) == expected

    def test_str_representation_ended(self) -> None:
        """Test string representation for ended membership."""
        end_date = date(2023, 12, 31)
        member = create_conference_member(
            politician_id=5, conference_id=10, end_date=end_date
        )

        expected = f"ConferenceMember(politician=5, conference=10, ended {end_date})"
        assert str(member) == expected

    def test_entity_factory(self) -> None:
        """Test entity creation using factory."""
        member = create_conference_member()

        assert member.id == 1
        assert member.politician_id == 1
        assert member.conference_id == 1
        assert member.start_date == date(2023, 1, 1)
        assert member.end_date is None
        assert member.role == "議員"

    def test_factory_with_overrides(self) -> None:
        """Test entity factory with custom values."""
        member = create_conference_member(
            id=99,
            politician_id=50,
            conference_id=30,
            start_date=date(2022, 4, 1),
            end_date=date(2023, 3, 31),
            role="委員長",
        )

        assert member.id == 99
        assert member.politician_id == 50
        assert member.conference_id == 30
        assert member.start_date == date(2022, 4, 1)
        assert member.end_date == date(2023, 3, 31)
        assert member.role == "委員長"

    def test_different_roles(self) -> None:
        """Test membership with different roles."""
        roles = ["議員", "議長", "副議長", "委員長", "副委員長", "幹事長", None]

        for role in roles:
            member = create_conference_member(role=role)
            assert member.role == role

    def test_membership_timeline(self) -> None:
        """Test different membership timelines."""
        # Past membership
        past_member = ConferenceMember(
            politician_id=1,
            conference_id=1,
            start_date=date(2020, 1, 1),
            end_date=date(2021, 12, 31),
        )
        assert past_member.is_active() is False

        # Current membership (started in past, no end)
        current_member = ConferenceMember(
            politician_id=1, conference_id=1, start_date=date(2022, 1, 1), end_date=None
        )
        assert current_member.is_active() is True

        # Future start date (still active if no end date)
        future_member = ConferenceMember(
            politician_id=1, conference_id=1, start_date=date(2025, 1, 1), end_date=None
        )
        assert future_member.is_active() is True

    def test_multiple_memberships(self) -> None:
        """Test creating multiple memberships for the same politician."""
        # Politician can have multiple memberships to different conferences
        member1 = create_conference_member(
            id=1, politician_id=100, conference_id=1, role="議員"
        )

        member2 = create_conference_member(
            id=2, politician_id=100, conference_id=2, role="委員長"
        )

        assert member1.politician_id == member2.politician_id
        assert member1.conference_id != member2.conference_id
        assert member1.role != member2.role

    def test_membership_with_same_start_end_date(self) -> None:
        """Test membership that starts and ends on the same date."""
        same_date = date(2023, 6, 1)
        member = ConferenceMember(
            politician_id=1, conference_id=1, start_date=same_date, end_date=same_date
        )

        assert member.start_date == member.end_date
        assert member.is_active() is False

    def test_inheritance_from_base_entity(self) -> None:
        """Test that ConferenceMember properly inherits from BaseEntity."""
        member = create_conference_member(id=42)

        # Check that id is properly set through BaseEntity
        assert member.id == 42

        # Create without id
        member_no_id = ConferenceMember(
            politician_id=1, conference_id=1, start_date=date(2023, 1, 1)
        )
        assert member_no_id.id is None
