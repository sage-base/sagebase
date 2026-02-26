"""Tests for ParliamentaryGroup entity."""

from datetime import date

import pytest

from tests.fixtures.entity_factories import create_parliamentary_group

from src.domain.entities.parliamentary_group import ParliamentaryGroup


class TestParliamentaryGroup:
    """Test cases for ParliamentaryGroup entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        group = ParliamentaryGroup(
            name="自民党議員団",
            governing_body_id=1,
        )

        assert group.name == "自民党議員団"
        assert group.governing_body_id == 1
        assert group.url is None
        assert group.description is None
        assert group.is_active is True  # Default value
        assert group.chamber == ""
        assert group.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        group = ParliamentaryGroup(
            id=10,
            name="立憲民主党会派",
            governing_body_id=5,
            url="https://example.com/group",
            description="立憲民主党所属の議員で構成される会派",
            is_active=False,
            chamber="衆議院",
        )

        assert group.id == 10
        assert group.name == "立憲民主党会派"
        assert group.governing_body_id == 5
        assert group.url == "https://example.com/group"
        assert group.description == "立憲民主党所属の議員で構成される会派"
        assert group.is_active is False
        assert group.chamber == "衆議院"

    def test_chamber_field(self) -> None:
        """Test chamber field variations."""
        group_shuugiin = ParliamentaryGroup(
            name="公明党", governing_body_id=1, chamber="衆議院"
        )
        assert group_shuugiin.chamber == "衆議院"

        group_sangiin = ParliamentaryGroup(
            name="公明党", governing_body_id=1, chamber="参議院"
        )
        assert group_sangiin.chamber == "参議院"

        group_local = ParliamentaryGroup(
            name="公明党京都市会議員団", governing_body_id=2
        )
        assert group_local.chamber == ""

    def test_str_representation(self) -> None:
        """Test string representation."""
        group = ParliamentaryGroup(
            name="公明党議員団",
            governing_body_id=1,
        )
        assert str(group) == "公明党議員団"

        group_with_id = ParliamentaryGroup(
            id=42,
            name="日本維新の会",
            governing_body_id=2,
        )
        assert str(group_with_id) == "日本維新の会"

    def test_entity_factory(self) -> None:
        """Test entity creation using factory."""
        group = create_parliamentary_group()

        assert group.id == 1
        assert group.name == "自民党議員団"
        assert group.governing_body_id == 1
        assert group.description is None
        assert group.is_active is True

    def test_factory_with_overrides(self) -> None:
        """Test entity factory with custom values."""
        group = create_parliamentary_group(
            id=99,
            name="国民民主党会派",
            governing_body_id=10,
            url="https://example.com/kokumin",
            description="国民民主党の議員団",
            is_active=False,
        )

        assert group.id == 99
        assert group.name == "国民民主党会派"
        assert group.governing_body_id == 10
        assert group.url == "https://example.com/kokumin"
        assert group.description == "国民民主党の議員団"
        assert group.is_active is False

    def test_various_group_names(self) -> None:
        """Test various parliamentary group names."""
        names = [
            "自由民主党議員団",
            "立憲民主党会派",
            "公明党議員団",
            "日本維新の会",
            "国民民主党会派",
            "日本共産党議員団",
            "れいわ新選組",
            "無所属の会",
            "市民クラブ",
            "改革ネット",
        ]

        for name in names:
            group = ParliamentaryGroup(name=name, governing_body_id=1)
            assert group.name == name
            assert str(group) == name

    def test_is_active_flag(self) -> None:
        """Test is_active flag variations."""
        # Default is True
        group_default = ParliamentaryGroup(
            name="Test Group",
            governing_body_id=1,
        )
        assert group_default.is_active is True

        # Explicitly set to True
        group_active = ParliamentaryGroup(
            name="Active Group",
            governing_body_id=1,
            is_active=True,
        )
        assert group_active.is_active is True

        # Explicitly set to False
        group_inactive = ParliamentaryGroup(
            name="Inactive Group",
            governing_body_id=1,
            is_active=False,
        )
        assert group_inactive.is_active is False

    def test_url_formats(self) -> None:
        """Test various URL formats."""
        urls = [
            "https://example.com/group",
            "http://city.jp/council/groups/1",
            "https://www.group-website.com/",
            None,
        ]

        for url in urls:
            group = ParliamentaryGroup(
                name="Test Group",
                governing_body_id=1,
                url=url,
            )
            assert group.url == url

    def test_description_variations(self) -> None:
        """Test various description formats."""
        descriptions = [
            "自由民主党所属の議員で構成される会派",
            "市民の声を代表する議員団",
            "改革を目指す超党派の会派",
            "",
            None,
        ]

        for desc in descriptions:
            group = ParliamentaryGroup(
                name="Test Group",
                governing_body_id=1,
                description=desc,
            )
            assert group.description == desc

    def test_governing_body_id_variations(self) -> None:
        """Test various governing body IDs."""
        ids = [1, 10, 100, 1000, 9999]

        for gb_id in ids:
            group = ParliamentaryGroup(
                name="Test Group",
                governing_body_id=gb_id,
            )
            assert group.governing_body_id == gb_id

    def test_inheritance_from_base_entity(self) -> None:
        """Test that ParliamentaryGroup properly inherits from BaseEntity."""
        group = create_parliamentary_group(id=42)

        # Check that id is properly set through BaseEntity
        assert group.id == 42

        # Create without id
        group_no_id = ParliamentaryGroup(
            name="Test Group",
            governing_body_id=1,
        )
        assert group_no_id.id is None

    def test_complex_group_scenarios(self) -> None:
        """Test complex real-world parliamentary group scenarios."""
        # Major party group
        major_party = ParliamentaryGroup(
            id=1,
            name="自由民主党議員団",
            governing_body_id=1,
            url="https://example.com/ldp-group",
            description="自由民主党所属議員で構成される最大会派",
            is_active=True,
        )
        assert str(major_party) == "自由民主党議員団"
        assert major_party.is_active is True

        # Opposition group
        opposition = ParliamentaryGroup(
            id=2,
            name="立憲民主党・無所属の会",
            governing_body_id=1,
            url="https://example.com/cdp-group",
            description="立憲民主党と無所属議員による野党第一会派",
            is_active=True,
        )
        assert str(opposition) == "立憲民主党・無所属の会"

        # Dissolved group
        dissolved = ParliamentaryGroup(
            id=3,
            name="旧民主党会派",
            governing_body_id=1,
            description="2016年に解散した会派",
            is_active=False,
        )
        assert dissolved.is_active is False

    def test_edge_cases(self) -> None:
        """Test edge cases for ParliamentaryGroup entity."""
        # Empty strings
        group_empty = ParliamentaryGroup(
            name="Name",
            governing_body_id=1,
            url="",
            description="",
        )
        assert group_empty.name == "Name"
        assert group_empty.url == ""
        assert group_empty.description == ""

        # Very long name
        long_name = "自由民主党" * 50
        group_long = ParliamentaryGroup(
            name=long_name,
            governing_body_id=1,
        )
        assert group_long.name == long_name
        assert str(group_long) == long_name

        # Special characters in name
        special_name = "立憲民主党・無所属の会（市民派）"
        group_special = ParliamentaryGroup(
            name=special_name,
            governing_body_id=1,
        )
        assert group_special.name == special_name
        assert str(group_special) == special_name

        # Very long URL
        long_url = "https://example.com/" + "a" * 200
        group_long_url = ParliamentaryGroup(
            name="Test",
            governing_body_id=1,
            url=long_url,
        )
        assert group_long_url.url == long_url

        # Very long description
        long_desc = "説明" * 100
        group_long_desc = ParliamentaryGroup(
            name="Test",
            governing_body_id=1,
            description=long_desc,
        )
        assert group_long_desc.description == long_desc

    def test_optional_fields_none_behavior(self) -> None:
        """Test behavior when optional fields are explicitly set to None."""
        group = ParliamentaryGroup(
            name="Test Group",
            governing_body_id=1,
            url=None,
            description=None,
        )

        assert group.url is None
        assert group.description is None
        assert group.is_active is True  # Default value

    def test_id_assignment(self) -> None:
        """Test ID assignment behavior."""
        # Without ID
        group1 = ParliamentaryGroup(name="Test 1", governing_body_id=1)
        assert group1.id is None

        # With ID
        group2 = ParliamentaryGroup(name="Test 2", governing_body_id=1, id=100)
        assert group2.id == 100

        # ID can be any integer
        group3 = ParliamentaryGroup(name="Test 3", governing_body_id=1, id=999999)
        assert group3.id == 999999

    def test_coalition_and_opposition_groups(self) -> None:
        """Test coalition and opposition group patterns."""
        # Coalition group
        coalition = ParliamentaryGroup(
            name="与党会派",
            governing_body_id=1,
            description="自民党と公明党による連立与党会派",
            is_active=True,
        )
        assert coalition.is_active is True

        # Opposition group
        opposition = ParliamentaryGroup(
            name="野党統一会派",
            governing_body_id=1,
            description="野党各党による統一会派",
            is_active=True,
        )
        assert opposition.is_active is True

        # Independent group
        independent = ParliamentaryGroup(
            name="無所属の会",
            governing_body_id=1,
            description="無所属議員による会派",
            is_active=True,
        )
        assert independent.name == "無所属の会"

    def test_regional_group_patterns(self) -> None:
        """Test regional parliamentary group patterns."""
        # Prefectural group
        prefectural = ParliamentaryGroup(
            name="都民ファーストの会",
            governing_body_id=1,
            description="東京都議会における地域政党",
            is_active=True,
        )
        assert prefectural.name == "都民ファーストの会"

        # City council group
        city = ParliamentaryGroup(
            name="市民の声",
            governing_body_id=2,
            description="市民の声を代表する会派",
            is_active=True,
        )
        assert city.name == "市民の声"

        # Reform group
        reform = ParliamentaryGroup(
            name="改革ネット",
            governing_body_id=3,
            description="地方議会改革を目指す超党派の会派",
            is_active=True,
        )
        assert reform.name == "改革ネット"


class TestParliamentaryGroupTemporalManagement:
    """時代管理（start_date/end_date）のテスト."""

    def test_initialization_with_dates(self) -> None:
        """日付付きでエンティティを作成できる."""
        group = ParliamentaryGroup(
            name="公明党・改革クラブ",
            governing_body_id=1,
            start_date=date(1999, 10, 1),
            end_date=date(2003, 11, 18),
            is_active=False,
        )
        assert group.start_date == date(1999, 10, 1)
        assert group.end_date == date(2003, 11, 18)

    def test_initialization_without_dates(self) -> None:
        """日付なしのデフォルト値はNone."""
        group = ParliamentaryGroup(
            name="自民党議員団",
            governing_body_id=1,
        )
        assert group.start_date is None
        assert group.end_date is None

    def test_validation_end_date_before_start_date(self) -> None:
        """end_dateがstart_dateより前の場合ValueError."""
        with pytest.raises(ValueError, match="end_date.*start_date.*前"):
            ParliamentaryGroup(
                name="テスト会派",
                governing_body_id=1,
                start_date=date(2020, 1, 1),
                end_date=date(2019, 12, 31),
            )

    def test_validation_same_start_and_end_date(self) -> None:
        """start_dateとend_dateが同日は許容される."""
        group = ParliamentaryGroup(
            name="テスト会派",
            governing_body_id=1,
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 1),
        )
        assert group.start_date == group.end_date

    def test_validation_end_date_only(self) -> None:
        """end_dateのみ指定（start_dateなし）はバリデーションスキップ."""
        group = ParliamentaryGroup(
            name="テスト会派",
            governing_body_id=1,
            end_date=date(2020, 1, 1),
        )
        assert group.start_date is None
        assert group.end_date == date(2020, 1, 1)

    def test_is_active_as_of_with_dates(self) -> None:
        """日付が設定されている場合、日付で判定する."""
        group = ParliamentaryGroup(
            name="公明党・改革クラブ",
            governing_body_id=1,
            start_date=date(1999, 10, 1),
            end_date=date(2003, 11, 18),
            is_active=False,
        )
        # 開始前
        assert group.is_active_as_of(date(1999, 9, 30)) is False
        # 開始日
        assert group.is_active_as_of(date(1999, 10, 1)) is True
        # 期間中
        assert group.is_active_as_of(date(2001, 5, 15)) is True
        # 終了日
        assert group.is_active_as_of(date(2003, 11, 18)) is True
        # 終了後
        assert group.is_active_as_of(date(2003, 11, 19)) is False

    def test_is_active_as_of_without_dates_fallback(self) -> None:
        """日付未設定の場合、is_activeフラグにフォールバック."""
        active_group = ParliamentaryGroup(
            name="現行会派",
            governing_body_id=1,
            is_active=True,
        )
        assert active_group.is_active_as_of(date(2024, 10, 27)) is True

        inactive_group = ParliamentaryGroup(
            name="歴史的会派",
            governing_body_id=1,
            is_active=False,
        )
        assert inactive_group.is_active_as_of(date(2024, 10, 27)) is False

    def test_is_active_as_of_with_start_date_only(self) -> None:
        """start_dateのみ設定（end_dateなし）の場合."""
        group = ParliamentaryGroup(
            name="現行会派",
            governing_body_id=1,
            start_date=date(2021, 11, 1),
        )
        # 開始前
        assert group.is_active_as_of(date(2021, 10, 31)) is False
        # 開始後
        assert group.is_active_as_of(date(2024, 10, 27)) is True

    def test_is_active_as_of_with_end_date_only(self) -> None:
        """end_dateのみ設定（start_dateなし）の場合."""
        group = ParliamentaryGroup(
            name="歴史的会派",
            governing_body_id=1,
            end_date=date(2003, 11, 18),
        )
        # 終了前
        assert group.is_active_as_of(date(2001, 5, 15)) is True
        # 終了後
        assert group.is_active_as_of(date(2003, 11, 19)) is False

    def test_overlaps_with_full_overlap(self) -> None:
        """完全に重複する期間."""
        group = ParliamentaryGroup(
            name="テスト会派",
            governing_body_id=1,
            start_date=date(2000, 1, 1),
            end_date=date(2005, 12, 31),
        )
        assert group.overlaps_with(date(2002, 1, 1), date(2003, 12, 31)) is True

    def test_overlaps_with_no_overlap(self) -> None:
        """重複しない期間."""
        group = ParliamentaryGroup(
            name="テスト会派",
            governing_body_id=1,
            start_date=date(2000, 1, 1),
            end_date=date(2005, 12, 31),
        )
        assert group.overlaps_with(date(2006, 1, 1), date(2010, 12, 31)) is False

    def test_overlaps_with_partial_overlap(self) -> None:
        """部分的に重複する期間."""
        group = ParliamentaryGroup(
            name="テスト会派",
            governing_body_id=1,
            start_date=date(2000, 1, 1),
            end_date=date(2005, 12, 31),
        )
        assert group.overlaps_with(date(2004, 1, 1), date(2010, 12, 31)) is True

    def test_overlaps_with_open_ended(self) -> None:
        """end_dateなし（現在も有効）の場合."""
        group = ParliamentaryGroup(
            name="現行会派",
            governing_body_id=1,
            start_date=date(2021, 11, 1),
        )
        assert group.overlaps_with(date(2024, 1, 1), date(2024, 12, 31)) is True
        assert group.overlaps_with(date(2020, 1, 1), date(2020, 12, 31)) is False

    def test_overlaps_with_no_dates_active(self) -> None:
        """日付未設定・is_active=Trueの場合、overlaps_withはTrueを返す."""
        group = ParliamentaryGroup(
            name="現行会派",
            governing_body_id=1,
            is_active=True,
        )
        assert group.overlaps_with(date(2024, 1, 1), date(2024, 12, 31)) is True

    def test_overlaps_with_no_dates_inactive(self) -> None:
        """日付未設定・is_active=Falseの場合、overlaps_withはFalseを返す."""
        group = ParliamentaryGroup(
            name="歴史的会派",
            governing_body_id=1,
            is_active=False,
        )
        assert group.overlaps_with(date(2024, 1, 1), date(2024, 12, 31)) is False

    def test_overlaps_with_open_ended_argument(self) -> None:
        """引数のend_date=Noneの場合（開放区間）の重複判定."""
        group = ParliamentaryGroup(
            name="テスト会派",
            governing_body_id=1,
            start_date=date(2000, 1, 1),
            end_date=date(2005, 12, 31),
        )
        # 引数start_dateが会派の終了後 → 重複なし
        assert group.overlaps_with(date(2006, 1, 1)) is False
        # 引数start_dateが会派の期間中 → 重複あり
        assert group.overlaps_with(date(2003, 1, 1)) is True

    def test_overlaps_with_start_date_only(self) -> None:
        """self.start_dateのみ設定・self.end_dateなしの場合."""
        group = ParliamentaryGroup(
            name="現行会派",
            governing_body_id=1,
            start_date=date(2021, 11, 1),
        )
        # 引数end_dateが会派開始前 → 重複なし
        assert group.overlaps_with(date(2020, 1, 1), date(2021, 10, 31)) is False
        # 引数がまたがる → 重複あり
        assert group.overlaps_with(date(2020, 1, 1), date(2022, 12, 31)) is True

    def test_overlaps_with_end_date_only(self) -> None:
        """self.end_dateのみ設定・self.start_dateなしの場合."""
        group = ParliamentaryGroup(
            name="歴史的会派",
            governing_body_id=1,
            end_date=date(2005, 12, 31),
        )
        # 引数start_dateが会派終了後 → 重複なし
        assert group.overlaps_with(date(2006, 1, 1), date(2010, 12, 31)) is False
        # 引数が会派期間にかかる → 重複あり
        assert group.overlaps_with(date(2004, 1, 1), date(2010, 12, 31)) is True

    def test_update_period_valid(self) -> None:
        """update_periodで正常に期間を更新できる."""
        group = create_parliamentary_group()
        group.update_period(date(2020, 1, 1), date(2024, 12, 31))
        assert group.start_date == date(2020, 1, 1)
        assert group.end_date == date(2024, 12, 31)

    def test_update_period_invalid(self) -> None:
        """update_periodでend_date < start_dateの場合ValueError."""
        group = create_parliamentary_group()
        with pytest.raises(ValueError, match="end_date.*start_date.*前"):
            group.update_period(date(2024, 1, 1), date(2023, 12, 31))

    def test_update_period_clears_dates(self) -> None:
        """update_periodでNoneを渡すと日付をクリアできる."""
        group = create_parliamentary_group(
            start_date=date(2020, 1, 1),
            end_date=date(2024, 12, 31),
        )
        group.update_period(None, None)
        assert group.start_date is None
        assert group.end_date is None

    def test_factory_with_dates(self) -> None:
        """ファクトリで日付付きエンティティを作成."""
        group = create_parliamentary_group(
            start_date=date(2021, 11, 1),
            end_date=date(2024, 10, 26),
        )
        assert group.start_date == date(2021, 11, 1)
        assert group.end_date == date(2024, 10, 26)
