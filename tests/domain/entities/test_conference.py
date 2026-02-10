"""Tests for Conference entity."""

from tests.fixtures.entity_factories import create_conference

from src.domain.entities.conference import Conference


class TestConference:
    """Test cases for Conference entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        conference = Conference(
            name="東京都議会",
            governing_body_id=1,
        )

        assert conference.name == "東京都議会"
        assert conference.governing_body_id == 1
        assert conference.term is None
        assert conference.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        conference = Conference(
            id=10,
            name="大阪市議会",
            governing_body_id=5,
            term="令和5年度",
        )

        assert conference.id == 10
        assert conference.name == "大阪市議会"
        assert conference.governing_body_id == 5
        assert conference.term == "令和5年度"

    def test_str_representation(self) -> None:
        """Test string representation."""
        conference = Conference(name="北海道議会", governing_body_id=1)
        assert str(conference) == "北海道議会"

        conference_with_id = Conference(
            id=42,
            name="福岡市議会",
            governing_body_id=2,
        )
        assert str(conference_with_id) == "福岡市議会"

    def test_entity_factory(self) -> None:
        """Test entity creation using factory."""
        conference = create_conference()

        assert conference.id == 1
        assert conference.governing_body_id == 1
        assert conference.name == "議会全体"
        assert conference.term is None

    def test_factory_with_overrides(self) -> None:
        """Test entity factory with custom values."""
        conference = create_conference(
            id=99,
            name="愛知県議会",
            governing_body_id=10,
            term="令和6年度",
        )

        assert conference.id == 99
        assert conference.name == "愛知県議会"
        assert conference.governing_body_id == 10
        assert conference.term == "令和6年度"

    def test_various_conference_names(self) -> None:
        """Test various conference names."""
        names = [
            "東京都議会",
            "大阪市議会",
            "札幌市議会",
            "福岡市議会本会議",
            "総務委員会",
            "予算特別委員会",
            "決算特別委員会",
            "文教委員会",
        ]

        for name in names:
            conference = Conference(name=name, governing_body_id=1)
            assert conference.name == name
            assert str(conference) == name

    def test_governing_body_id_variations(self) -> None:
        """Test various governing body IDs."""
        ids = [1, 10, 100, 1000, 9999]

        for gb_id in ids:
            conference = Conference(
                name="Test Conference",
                governing_body_id=gb_id,
            )
            assert conference.governing_body_id == gb_id

    def test_inheritance_from_base_entity(self) -> None:
        """Test that Conference properly inherits from BaseEntity."""
        conference = create_conference(id=42)

        # Check that id is properly set through BaseEntity
        assert conference.id == 42

        # Create without id
        conference_no_id = Conference(
            name="Test Conference",
            governing_body_id=1,
        )
        assert conference_no_id.id is None

    def test_term_none_by_default(self) -> None:
        """Test term is None by default when not specified."""
        conference = Conference(
            name="Test Conference",
            governing_body_id=1,
        )
        assert conference.term is None

    def test_initialization_with_term(self) -> None:
        """Test entity initialization with term field."""
        # 国会の会期パターン
        conference_kokkai = Conference(
            id=1,
            name="衆議院本会議",
            governing_body_id=1,
            term="第220回",
        )
        assert conference_kokkai.term == "第220回"

        # 地方議会の年度パターン
        conference_local = Conference(
            id=2,
            name="東京都議会",
            governing_body_id=13,
            term="令和5年度",
        )
        assert conference_local.term == "令和5年度"

        # termがNoneの場合
        conference_no_term = Conference(
            id=3,
            name="委員会",
            governing_body_id=1,
            term=None,
        )
        assert conference_no_term.term is None

    def test_edge_cases(self) -> None:
        """Test edge cases for Conference entity."""
        # Very long names
        long_name = "東京都" * 50
        conference_long = Conference(
            name=long_name,
            governing_body_id=1,
        )
        assert conference_long.name == long_name
        assert str(conference_long) == long_name

        # Special characters in name
        special_name = "東京都議会（第1回定例会）"
        conference_special = Conference(
            name=special_name,
            governing_body_id=1,
        )
        assert conference_special.name == special_name
        assert str(conference_special) == special_name

    def test_optional_fields_none_behavior(self) -> None:
        """Test behavior when optional fields are explicitly set to None."""
        conference = Conference(
            name="Test Conference",
            governing_body_id=1,
            term=None,
        )

        assert conference.term is None

    def test_id_assignment(self) -> None:
        """Test ID assignment behavior."""
        # Without ID
        conference1 = Conference(name="Test 1", governing_body_id=1)
        assert conference1.id is None

        # With ID
        conference2 = Conference(name="Test 2", governing_body_id=1, id=100)
        assert conference2.id == 100

        # ID can be any integer
        conference3 = Conference(name="Test 3", governing_body_id=1, id=999999)
        assert conference3.id == 999999
