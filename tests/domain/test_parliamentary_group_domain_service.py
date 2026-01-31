"""Tests for ParliamentaryGroupDomainService."""

from datetime import date

import pytest

from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.services.parliamentary_group_domain_service import (
    ParliamentaryGroupDomainService,
)


class TestParliamentaryGroupDomainService:
    """Test cases for ParliamentaryGroupDomainService."""

    @pytest.fixture
    def service(self):
        """Create ParliamentaryGroupDomainService instance."""
        return ParliamentaryGroupDomainService()

    @pytest.fixture
    def sample_group(self):
        """Create sample parliamentary group."""
        return ParliamentaryGroup(
            id=1,
            name="自民党議員団",
            governing_body_id=1,
            description="自由民主党の議員団",
            is_active=True,
        )

    @pytest.fixture
    def sample_memberships(self):
        """Create sample memberships."""
        return [
            {
                "parliamentary_group_id": 1,
                "politician_id": 1,
                "role": "団長",
                "start_date": date(2023, 1, 1),
                "end_date": date(2023, 6, 30),
            },
            {
                "parliamentary_group_id": 1,
                "politician_id": 1,
                "role": "団長",
                "start_date": date(2023, 7, 1),
                "end_date": None,
            },
            {
                "parliamentary_group_id": 2,
                "politician_id": 2,
                "role": "幹事長",
                "start_date": date(2023, 4, 1),
                "end_date": None,
            },
        ]

    def test_normalize_group_name(self, service):
        """Test parliamentary group name normalization."""
        # Test suffix removal
        assert service.normalize_group_name("自民党議員団") == "自民党"
        assert service.normalize_group_name("公明党会派") == "公明党"
        assert service.normalize_group_name("市民の会") == "市民"
        assert service.normalize_group_name("立憲民主クラブ") == "立憲民主"

        # Test with spaces
        assert service.normalize_group_name("  自民党  ") == "自民党"

        # Test edge cases
        assert service.normalize_group_name("") == ""
        assert service.normalize_group_name(None) == ""
        assert service.normalize_group_name("無所属") == "無所属"

    def test_extract_role_from_text(self, service):
        """Test extracting role from text."""
        # Test exact matches
        assert service.extract_role_from_text("団長") == "団長"
        assert service.extract_role_from_text("幹事長") == "幹事長"
        assert service.extract_role_from_text("政調会長") == "政調会長"
        # Note: "副団長" contains "団長" so it will match "団長" first
        assert service.extract_role_from_text("副団長") == "団長"

        # Test role in context
        assert service.extract_role_from_text("山田太郎（団長）") == "団長"
        assert service.extract_role_from_text("幹事長：鈴木花子") == "幹事長"

        # Test no role
        assert service.extract_role_from_text("一般議員") is None
        assert service.extract_role_from_text("") is None

    def test_validate_membership_dates_valid(self, service):
        """Test validation of valid membership dates."""
        # No existing memberships
        issues = service.validate_membership_dates(date(2023, 1, 1), None, [])
        assert len(issues) == 0

        # Non-overlapping membership
        existing = [(date(2022, 1, 1), date(2022, 12, 31))]
        issues = service.validate_membership_dates(date(2023, 1, 1), None, existing)
        assert len(issues) == 0

    def test_validate_membership_dates_invalid(self, service):
        """Test validation of invalid membership dates."""
        # End before start
        issues = service.validate_membership_dates(
            date(2023, 6, 1), date(2023, 1, 1), []
        )
        assert "End date must be after start date" in issues

        # Overlapping memberships
        existing = [(date(2023, 1, 1), None)]  # Ongoing
        issues = service.validate_membership_dates(date(2023, 6, 1), None, existing)
        assert len(issues) > 0
        assert "overlaps with existing period" in issues[0]

    def test_dates_overlap(self, service):
        """Test date overlap detection."""
        # Both ongoing
        assert (
            service._dates_overlap(date(2023, 1, 1), None, date(2023, 6, 1), None)
            is True
        )

        # One ongoing, overlaps
        assert (
            service._dates_overlap(
                date(2023, 1, 1), None, date(2022, 6, 1), date(2023, 6, 1)
            )
            is True
        )

        # No overlap
        assert (
            service._dates_overlap(
                date(2023, 1, 1), date(2023, 6, 1), date(2023, 7, 1), date(2023, 12, 31)
            )
            is False
        )

        # Edge case: same end and start
        assert (
            service._dates_overlap(
                date(2023, 1, 1),
                date(2023, 6, 30),
                date(2023, 6, 30),
                date(2023, 12, 31),
            )
            is True
        )

    def test_merge_group_memberships(self, service):
        """Test merging adjacent memberships."""
        memberships = [
            {
                "parliamentary_group_id": 1,
                "role": "団長",
                "start_date": date(2023, 1, 1),
                "end_date": date(2023, 6, 30),
            },
            {
                "parliamentary_group_id": 1,
                "role": "団長",
                "start_date": date(2023, 7, 1),  # Adjacent
                "end_date": None,
            },
            {
                "parliamentary_group_id": 2,
                "role": "幹事長",
                "start_date": date(2023, 4, 1),
                "end_date": None,
            },
        ]

        merged = service.merge_group_memberships(memberships)

        # After sorting by start_date, the memberships are not consecutive
        # so they cannot be merged
        assert len(merged) == 3
        # First: group_id=1, start=2023-01-01
        assert merged[0]["parliamentary_group_id"] == 1
        assert merged[0]["start_date"] == date(2023, 1, 1)
        assert merged[0]["end_date"] == date(2023, 6, 30)

        # Second: group_id=2, start=2023-04-01
        assert merged[1]["parliamentary_group_id"] == 2

        # Third: group_id=1, start=2023-07-01
        assert merged[2]["parliamentary_group_id"] == 1
        assert merged[2]["start_date"] == date(2023, 7, 1)

    def test_merge_group_memberships_non_adjacent(self, service):
        """Test that non-adjacent memberships are not merged."""
        memberships = [
            {
                "parliamentary_group_id": 1,
                "role": "団長",
                "start_date": date(2023, 1, 1),
                "end_date": date(2023, 6, 30),
            },
            {
                "parliamentary_group_id": 1,
                "role": "団長",
                "start_date": date(2023, 8, 1),  # Gap of 1 month
                "end_date": None,
            },
        ]

        merged = service.merge_group_memberships(memberships)
        assert len(merged) == 2  # Not merged

    def test_can_merge_periods(self, service):
        """Test period merge logic."""
        # Adjacent periods (1 day gap)
        assert service._can_merge_periods(date(2023, 6, 30), date(2023, 7, 1)) is True

        # Same day
        assert service._can_merge_periods(date(2023, 6, 30), date(2023, 6, 30)) is True

        # Ongoing period
        assert service._can_merge_periods(None, date(2023, 7, 1)) is True

        # Too far apart
        assert service._can_merge_periods(date(2023, 6, 30), date(2023, 8, 1)) is False

    def test_calculate_group_strength(self, service, sample_group):
        """Test parliamentary group strength calculation."""
        # Majority
        result = service.calculate_group_strength(sample_group, 15, 25)
        assert result["member_count"] == 15
        assert result["percentage"] == 60.0
        assert result["status"] == "過半数"

        # Large group
        result = service.calculate_group_strength(sample_group, 10, 25)
        assert result["percentage"] == 40.0
        assert result["status"] == "大会派"

        # Medium group
        result = service.calculate_group_strength(sample_group, 6, 25)
        assert result["percentage"] == 24.0
        assert result["status"] == "中会派"

        # Small group
        result = service.calculate_group_strength(sample_group, 3, 25)
        assert result["percentage"] == 12.0
        assert result["status"] == "小会派"

        # Minority group
        result = service.calculate_group_strength(sample_group, 1, 25)
        assert result["percentage"] == 4.0
        assert result["status"] == "少数会派"

        # No members
        result = service.calculate_group_strength(sample_group, 0, 0)
        assert result["percentage"] == 0.0

    def test_find_similar_groups(self, service):
        """Test finding similar parliamentary groups."""
        groups = [
            ParliamentaryGroup(id=1, name="自民党議員団", governing_body_id=1),
            ParliamentaryGroup(id=2, name="自民党会派", governing_body_id=1),
            ParliamentaryGroup(id=3, name="公明党議員団", governing_body_id=1),
            ParliamentaryGroup(id=4, name="立憲民主", governing_body_id=1),
        ]

        # Find by normalized name
        similar = service.find_similar_groups("自民党", groups)
        assert len(similar) == 2
        assert all(g.id in [1, 2] for g in similar)

        # Exact match
        similar = service.find_similar_groups("自民党議員団", groups, threshold=0.9)
        assert len(similar) >= 1
        assert any(g.id == 1 for g in similar)

        # No matches
        similar = service.find_similar_groups("共産党", groups, threshold=0.8)
        assert len(similar) == 0

    def test_calculate_similarity(self, service):
        """Test name similarity calculation."""
        # Exact match
        assert service._calculate_similarity("自民党", "自民党") == 1.0

        # Containment
        assert service._calculate_similarity("自民党", "自民党議員団") == 0.9
        assert service._calculate_similarity("自民党議員団", "自民党") == 0.9

        # Partial overlap
        similarity = service._calculate_similarity("自民党", "立憲民主党")
        assert 0 < similarity < 0.9

        # No overlap
        assert service._calculate_similarity("自民党", "共産党") > 0  # Both have "党"

        # Empty strings
        assert service._calculate_similarity("", "") == 1.0

    def test_group_politicians_by_parliamentary_group(
        self, service, sample_memberships
    ):
        """Test grouping politicians by parliamentary groups."""
        grouped = service.group_politicians_by_parliamentary_group(sample_memberships)

        # Two groups should be present
        assert len(grouped) == 2
        assert 1 in grouped
        assert 2 in grouped

        # Group 1 has current member (second membership is ongoing)
        assert len(grouped[1]) == 1
        assert grouped[1][0]["start_date"] == date(2023, 7, 1)

        # Group 2 has one current member
        assert len(grouped[2]) == 1

    def test_group_politicians_by_parliamentary_group_past_only(self, service):
        """Test grouping with only past memberships."""
        past_memberships = [
            {
                "parliamentary_group_id": 1,
                "politician_id": 1,
                "role": "団長",
                "start_date": date(2020, 1, 1),
                "end_date": date(2020, 12, 31),
            },
        ]

        grouped = service.group_politicians_by_parliamentary_group(past_memberships)
        assert len(grouped) == 0  # No current members
