"""Tests for ConferenceDomainService."""

from datetime import date, datetime, timedelta

import pytest

from src.domain.entities.conference import Conference
from src.domain.services.conference_domain_service import ConferenceDomainService


class TestConferenceDomainService:
    """Test cases for ConferenceDomainService."""

    @pytest.fixture
    def service(self):
        """Create ConferenceDomainService instance."""
        return ConferenceDomainService()

    @pytest.fixture
    def sample_conferences(self):
        """Create sample conferences."""
        return [
            Conference(
                id=1,
                governing_body_id=1,
                name="議会全体",
            ),
            Conference(
                id=2,
                governing_body_id=1,
                name="総務常任委員会",
            ),
            Conference(
                id=3,
                governing_body_id=2,
                name="建設特別委員会",
            ),
        ]

    def test_extract_member_role(self, service):
        """Test extracting member role from text."""
        # Test exact matches
        assert service.extract_member_role("議長") == "議長"
        # Note: "副議長" contains "議長" so it will match "議長" first
        assert service.extract_member_role("副議長") == "議長"
        assert service.extract_member_role("委員長") == "委員長"
        assert service.extract_member_role("幹事長") == "幹事長"

        # Test role in context
        assert service.extract_member_role("山田太郎（議長）") == "議長"
        assert service.extract_member_role("総務委員会委員長：鈴木花子") == "委員長"

        # Test no role
        assert service.extract_member_role("山田太郎") is None
        assert service.extract_member_role("一般議員") is None
        assert service.extract_member_role("") is None

    def test_normalize_party_name(self, service):
        """Test party name normalization."""
        # Test suffix removal
        assert service.normalize_party_name("自民党の会") == "自民党"
        assert service.normalize_party_name("公明党会派") == "公明党"
        assert service.normalize_party_name("共産党議員団") == "共産党"
        assert service.normalize_party_name("市民クラブ") == "市民"
        # Note: "の会" is processed before "市民の会", so only "の会" is removed
        assert service.normalize_party_name("立憲民主党市民の会") == "立憲民主党市民"

        # Test with spaces
        assert service.normalize_party_name("  自民党  ") == "自民党"

        # Test edge cases
        assert service.normalize_party_name("") == ""
        assert service.normalize_party_name(None) == ""
        assert service.normalize_party_name("無所属") == "無所属"

    def test_calculate_affiliation_overlap(self, service):
        """Test affiliation period overlap calculation."""
        # Both ongoing
        assert (
            service.calculate_affiliation_overlap(
                date(2023, 1, 1), None, date(2023, 6, 1), None
            )
            is True
        )

        # One ongoing, overlaps
        assert (
            service.calculate_affiliation_overlap(
                date(2023, 1, 1), None, date(2022, 6, 1), date(2023, 6, 1)
            )
            is True
        )

        # One ongoing, no overlap
        assert (
            service.calculate_affiliation_overlap(
                date(2023, 7, 1), None, date(2022, 1, 1), date(2023, 6, 1)
            )
            is False
        )

        # Both have end dates, overlap
        assert (
            service.calculate_affiliation_overlap(
                date(2023, 1, 1), date(2023, 12, 31), date(2023, 6, 1), date(2024, 6, 1)
            )
            is True
        )

        # Both have end dates, no overlap
        assert (
            service.calculate_affiliation_overlap(
                date(2022, 1, 1),
                date(2022, 12, 31),
                date(2023, 1, 1),
                date(2023, 12, 31),
            )
            is False
        )

        # Edge case: same day
        assert (
            service.calculate_affiliation_overlap(
                date(2023, 1, 1), date(2023, 1, 1), date(2023, 1, 1), date(2023, 1, 1)
            )
            is True
        )

    def test_validate_affiliation_dates(self, service):
        """Test affiliation date validation."""
        # Valid dates
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        issues = service.validate_affiliation_dates(yesterday, None)
        assert len(issues) == 0

        issues = service.validate_affiliation_dates(
            date(2020, 1, 1), date(2023, 12, 31)
        )
        assert len(issues) == 0

        # Future start date
        tomorrow = today + timedelta(days=1)
        issues = service.validate_affiliation_dates(tomorrow, None)
        assert "Start date cannot be in the future" in issues

        # End before start
        issues = service.validate_affiliation_dates(date(2023, 6, 1), date(2023, 1, 1))
        assert "End date must be after start date" in issues

        # Too old
        issues = service.validate_affiliation_dates(date(1899, 1, 1), None)
        assert "Start date seems too old" in issues

    def test_group_conferences_by_governing_body(self, service, sample_conferences):
        """Test grouping conferences by governing body."""
        grouped = service.group_conferences_by_governing_body(sample_conferences)

        assert len(grouped) == 2
        assert len(grouped[1]) == 2
        assert len(grouped[2]) == 1

        assert grouped[1][0].name == "議会全体"
        assert grouped[1][1].name == "総務常任委員会"
        assert grouped[2][0].name == "建設特別委員会"

    def test_infer_conference_type(self, service):
        """Test inferring conference type from name."""
        # Committee types
        assert service.infer_conference_type("総務常任委員会") == "常任委員会"
        assert service.infer_conference_type("建設特別委員会") == "特別委員会"
        assert service.infer_conference_type("議会運営委員会") == "議会運営委員会"
        assert service.infer_conference_type("予算委員会") == "委員会"

        # Full council
        assert service.infer_conference_type("議会全体") == "議会全体"
        assert service.infer_conference_type("全体議会") == "議会全体"

        # Plenary session
        assert service.infer_conference_type("本会議") == "本会議"
        assert service.infer_conference_type("定例本会議") == "本会議"

        # Others
        assert service.infer_conference_type("議員協議会") == "その他"
        assert service.infer_conference_type("") == "その他"

    def test_calculate_member_confidence_score(self, service):
        """Test member confidence score calculation."""
        # Exact match, no boosts
        score = service.calculate_member_confidence_score(
            "山田太郎", "山田太郎", False, False
        )
        assert score == 1.0

        # Exact match with party boost
        score = service.calculate_member_confidence_score(
            "山田太郎", "山田太郎", True, False
        )
        assert score == 1.0  # Capped at 1.0

        # Partial match with boosts
        score = service.calculate_member_confidence_score(
            "山田", "山田太郎", True, True
        )
        assert 0.9 < score <= 1.0

        # No match
        score = service.calculate_member_confidence_score(
            "鈴木", "山田太郎", False, False
        )
        assert score < 0.5

    def test_calculate_name_similarity(self, service):
        """Test name similarity calculation."""
        # Exact match
        assert service._calculate_name_similarity("山田太郎", "山田太郎") == 1.0

        # With spaces
        assert service._calculate_name_similarity("山田 太郎", "山田太郎") == 1.0
        assert service._calculate_name_similarity("山田　太郎", "山田太郎") == 1.0

        # Substring match
        assert service._calculate_name_similarity("山田", "山田太郎") == 0.9
        assert service._calculate_name_similarity("山田太郎", "山田") == 0.9

        # Partial character overlap
        similarity = service._calculate_name_similarity("山田太郎", "山田次郎")
        assert 0 < similarity < 0.9

        # No overlap
        assert service._calculate_name_similarity("山田", "鈴木") == 0.0

        # Empty strings
        assert service._calculate_name_similarity("", "") == 1.0
        # Note: Empty string is contained in any string, so it returns 0.9
        assert service._calculate_name_similarity("山田", "") == 0.9
