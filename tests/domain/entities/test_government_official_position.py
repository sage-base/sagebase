"""GovernmentOfficialPositionエンティティのテスト."""

from datetime import date

from src.domain.entities.government_official_position import GovernmentOfficialPosition


class TestGovernmentOfficialPosition:
    """GovernmentOfficialPositionの基本テスト."""

    def test_init_with_required_fields(self) -> None:
        pos = GovernmentOfficialPosition(
            government_official_id=1,
            organization="法務省",
            position="刑事局長",
        )
        assert pos.government_official_id == 1
        assert pos.organization == "法務省"
        assert pos.position == "刑事局長"
        assert pos.start_date is None
        assert pos.end_date is None
        assert pos.source_note is None
        assert pos.id is None

    def test_init_with_all_fields(self) -> None:
        pos = GovernmentOfficialPosition(
            government_official_id=1,
            organization="法務省",
            position="刑事局長",
            start_date=date(2020, 1, 1),
            end_date=date(2023, 12, 31),
            source_note="法務省刑事局長",
            id=10,
        )
        assert pos.id == 10
        assert pos.start_date == date(2020, 1, 1)
        assert pos.end_date == date(2023, 12, 31)
        assert pos.source_note == "法務省刑事局長"


class TestIsActive:
    """is_active()メソッドのテスト."""

    def test_no_end_date_no_as_of_date_returns_true(self) -> None:
        """end_dateがNoneかつas_of_dateなし → 有効."""
        pos = GovernmentOfficialPosition(
            government_official_id=1, organization="法務省", position="局長"
        )
        assert pos.is_active() is True

    def test_has_end_date_no_as_of_date_returns_false(self) -> None:
        """end_dateがありas_of_dateなし → 終了済み."""
        pos = GovernmentOfficialPosition(
            government_official_id=1,
            organization="法務省",
            position="局長",
            end_date=date(2023, 12, 31),
        )
        assert pos.is_active() is False

    def test_as_of_date_before_start_date_returns_false(self) -> None:
        """as_of_dateがstart_dateより前 → 無効."""
        pos = GovernmentOfficialPosition(
            government_official_id=1,
            organization="法務省",
            position="局長",
            start_date=date(2020, 4, 1),
        )
        assert pos.is_active(as_of_date=date(2020, 3, 31)) is False

    def test_as_of_date_after_end_date_returns_false(self) -> None:
        """as_of_dateがend_dateより後 → 無効."""
        pos = GovernmentOfficialPosition(
            government_official_id=1,
            organization="法務省",
            position="局長",
            start_date=date(2020, 4, 1),
            end_date=date(2023, 3, 31),
        )
        assert pos.is_active(as_of_date=date(2023, 4, 1)) is False

    def test_as_of_date_within_range_returns_true(self) -> None:
        """as_of_dateがstart_date〜end_dateの範囲内 → 有効."""
        pos = GovernmentOfficialPosition(
            government_official_id=1,
            organization="法務省",
            position="局長",
            start_date=date(2020, 4, 1),
            end_date=date(2023, 3, 31),
        )
        assert pos.is_active(as_of_date=date(2022, 1, 1)) is True

    def test_as_of_date_equals_start_date_returns_true(self) -> None:
        """as_of_dateがstart_dateと同日 → 有効."""
        pos = GovernmentOfficialPosition(
            government_official_id=1,
            organization="法務省",
            position="局長",
            start_date=date(2020, 4, 1),
            end_date=date(2023, 3, 31),
        )
        assert pos.is_active(as_of_date=date(2020, 4, 1)) is True

    def test_as_of_date_equals_end_date_returns_true(self) -> None:
        """as_of_dateがend_dateと同日 → 有効."""
        pos = GovernmentOfficialPosition(
            government_official_id=1,
            organization="法務省",
            position="局長",
            start_date=date(2020, 4, 1),
            end_date=date(2023, 3, 31),
        )
        assert pos.is_active(as_of_date=date(2023, 3, 31)) is True

    def test_start_date_none_with_as_of_date_returns_true(self) -> None:
        """start_dateがNoneでas_of_date指定 → 開始日不明=いつからでも有効."""
        pos = GovernmentOfficialPosition(
            government_official_id=1,
            organization="法務省",
            position="局長",
            start_date=None,
            end_date=date(2023, 3, 31),
        )
        assert pos.is_active(as_of_date=date(2022, 1, 1)) is True

    def test_both_dates_none_with_as_of_date_returns_true(self) -> None:
        """start_dateもend_dateもNoneでas_of_date指定 → 有効."""
        pos = GovernmentOfficialPosition(
            government_official_id=1,
            organization="法務省",
            position="局長",
        )
        assert pos.is_active(as_of_date=date(2022, 1, 1)) is True
