"""Tests for ExtractedConferenceMember entity."""

from datetime import datetime

from tests.fixtures.entity_factories import create_extracted_conference_member

from src.domain.entities.extracted_conference_member import ExtractedConferenceMember


class TestExtractedConferenceMember:
    """Test cases for ExtractedConferenceMember entity.

    ExtractedConferenceMemberはBronze Layer（抽出ログ層）のエンティティです。
    政治家との紐付けはGold Layer（ConferenceMember）で管理されます。
    """

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        member = ExtractedConferenceMember(
            conference_id=1,
            extracted_name="山田太郎",
            source_url="https://example.com/members",
        )

        assert member.conference_id == 1
        assert member.extracted_name == "山田太郎"
        assert member.source_url == "https://example.com/members"
        assert member.extracted_role is None
        assert member.extracted_party_name is None
        assert member.additional_data is None
        assert isinstance(member.extracted_at, datetime)

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        extracted_at = datetime(2023, 1, 1, 12, 0, 0)

        member = ExtractedConferenceMember(
            id=1,
            conference_id=1,
            extracted_name="山田太郎",
            source_url="https://example.com/members",
            extracted_role="議員",
            extracted_party_name="自由民主党",
            extracted_at=extracted_at,
            additional_data='{"district": "東京1区"}',
        )

        assert member.id == 1
        assert member.conference_id == 1
        assert member.extracted_name == "山田太郎"
        assert member.source_url == "https://example.com/members"
        assert member.extracted_role == "議員"
        assert member.extracted_party_name == "自由民主党"
        assert member.extracted_at == extracted_at
        assert member.additional_data == '{"district": "東京1区"}'

    def test_str_representation(self) -> None:
        """Test string representation of the entity."""
        member = create_extracted_conference_member(
            id=123,
            extracted_name="鈴木一郎",
        )

        expected = "ExtractedConferenceMember(name=鈴木一郎, id=123)"
        assert str(member) == expected

    def test_entity_factory(self) -> None:
        """Test entity creation using factory."""
        member = create_extracted_conference_member()

        assert member.id == 1
        assert member.conference_id == 1
        assert member.extracted_name == "山田太郎"
        assert member.source_url == "https://example.com/members"
        assert member.extracted_role == "議員"
        assert member.extracted_party_name == "自由民主党"

    def test_factory_with_overrides(self) -> None:
        """Test entity factory with custom values."""
        member = create_extracted_conference_member(
            id=99,
            extracted_name="佐藤花子",
        )

        assert member.id == 99
        assert member.extracted_name == "佐藤花子"
        # Verify defaults are still applied
        assert member.conference_id == 1
        assert member.source_url == "https://example.com/members"

    def test_extracted_at_default_value(self) -> None:
        """Test that extracted_at is set to current time by default."""
        before = datetime.now()
        member = ExtractedConferenceMember(
            conference_id=1, extracted_name="Test", source_url="https://example.com"
        )
        after = datetime.now()

        assert before <= member.extracted_at <= after

    def test_update_from_extraction_log(self) -> None:
        """Test updating extraction log reference."""
        member = create_extracted_conference_member()
        assert member.latest_extraction_log_id is None

        member.update_from_extraction_log(123)
        assert member.latest_extraction_log_id == 123

        member.update_from_extraction_log(456)
        assert member.latest_extraction_log_id == 456

    def test_can_be_updated_by_ai_always_returns_true(self) -> None:
        """Test that Bronze Layer entity is always updatable by AI."""
        member = create_extracted_conference_member()

        # Bronze Layer（抽出ログ層）は常に更新可能
        assert member.can_be_updated_by_ai() is True
