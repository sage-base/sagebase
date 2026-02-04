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
        assert conference.type is None
        assert conference.members_introduction_url is None
        assert conference.prefecture is None
        assert conference.term is None
        assert conference.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        conference = Conference(
            id=10,
            name="大阪市議会",
            governing_body_id=5,
            type="地方議会全体",
            members_introduction_url="https://example.com/members",
            prefecture="大阪府",
        )

        assert conference.id == 10
        assert conference.name == "大阪市議会"
        assert conference.governing_body_id == 5
        assert conference.type == "地方議会全体"
        assert conference.members_introduction_url == "https://example.com/members"
        assert conference.prefecture == "大阪府"

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
        assert conference.type == "地方議会全体"
        assert conference.members_introduction_url is None
        assert conference.prefecture is None
        assert conference.term is None

    def test_factory_with_overrides(self) -> None:
        """Test entity factory with custom values."""
        conference = create_conference(
            id=99,
            name="愛知県議会",
            governing_body_id=10,
            type="都道府県議会",
            members_introduction_url="https://aichi.example.com/members",
            prefecture="愛知県",
        )

        assert conference.id == 99
        assert conference.name == "愛知県議会"
        assert conference.governing_body_id == 10
        assert conference.type == "都道府県議会"
        assert (
            conference.members_introduction_url == "https://aichi.example.com/members"
        )
        assert conference.prefecture == "愛知県"

    def test_different_conference_types(self) -> None:
        """Test different types of conferences."""
        types = [
            "地方議会全体",
            "都道府県議会",
            "市区町村議会",
            "常任委員会",
            "特別委員会",
            "議会運営委員会",
            None,
        ]

        for conf_type in types:
            conference = Conference(
                name="Test Conference",
                governing_body_id=1,
                type=conf_type,
            )
            assert conference.type == conf_type

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

    def test_members_introduction_url_formats(self) -> None:
        """Test various URL formats for members introduction."""
        urls = [
            "https://example.com/members",
            "http://city.jp/council/members",
            "https://www.prefecture.go.jp/members.html",
            None,
        ]

        for url in urls:
            conference = Conference(
                name="Test Conference",
                governing_body_id=1,
                members_introduction_url=url,
            )
            assert conference.members_introduction_url == url

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

    def test_complex_conference_scenarios(self) -> None:
        """Test complex real-world conference scenarios."""
        # Prefectural assembly
        prefectural = Conference(
            id=1,
            name="東京都議会",
            governing_body_id=13,
            type="都道府県議会",
            members_introduction_url="https://tokyo.example.com/members",
            prefecture="東京都",
        )
        assert str(prefectural) == "東京都議会"
        assert prefectural.type == "都道府県議会"
        assert prefectural.prefecture == "東京都"

        # City council
        city_council = Conference(
            id=2,
            name="横浜市議会",
            governing_body_id=141,
            type="市区町村議会",
            members_introduction_url="https://yokohama.example.com/members",
            prefecture="神奈川県",
        )
        assert str(city_council) == "横浜市議会"
        assert city_council.type == "市区町村議会"
        assert city_council.prefecture == "神奈川県"

        # Committee
        committee = Conference(
            id=3,
            name="総務委員会",
            governing_body_id=13,
            type="常任委員会",
            members_introduction_url=None,
            prefecture="東京都",
        )
        assert str(committee) == "総務委員会"
        assert committee.type == "常任委員会"
        assert committee.prefecture == "東京都"

    def test_prefecture_for_national_parliament(self) -> None:
        """Test prefecture set to '全国' for national parliament."""
        # National Diet (衆議院)
        house_of_representatives = Conference(
            id=1,
            name="衆議院本会議",
            governing_body_id=1,
            type="国会",
            prefecture="全国",
        )
        assert house_of_representatives.prefecture == "全国"

        # National Diet (参議院)
        house_of_councillors = Conference(
            id=2,
            name="参議院本会議",
            governing_body_id=1,
            type="国会",
            prefecture="全国",
        )
        assert house_of_councillors.prefecture == "全国"

    def test_all_prefectures(self) -> None:
        """Test all 47 prefectures plus '全国'."""
        prefectures = [
            "全国",
            "北海道",
            "青森県",
            "岩手県",
            "宮城県",
            "秋田県",
            "山形県",
            "福島県",
            "茨城県",
            "栃木県",
            "群馬県",
            "埼玉県",
            "千葉県",
            "東京都",
            "神奈川県",
            "新潟県",
            "富山県",
            "石川県",
            "福井県",
            "山梨県",
            "長野県",
            "岐阜県",
            "静岡県",
            "愛知県",
            "三重県",
            "滋賀県",
            "京都府",
            "大阪府",
            "兵庫県",
            "奈良県",
            "和歌山県",
            "鳥取県",
            "島根県",
            "岡山県",
            "広島県",
            "山口県",
            "徳島県",
            "香川県",
            "愛媛県",
            "高知県",
            "福岡県",
            "佐賀県",
            "長崎県",
            "熊本県",
            "大分県",
            "宮崎県",
            "鹿児島県",
            "沖縄県",
        ]

        for pref in prefectures:
            conference = Conference(
                name=f"{pref}議会",
                governing_body_id=1,
                prefecture=pref,
            )
            assert conference.prefecture == pref

    def test_prefecture_none_by_default(self) -> None:
        """Test prefecture is None by default when not specified."""
        conference = Conference(
            name="Test Conference",
            governing_body_id=1,
        )
        assert conference.prefecture is None

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
            type="国会",
            term="第220回",
        )
        assert conference_kokkai.term == "第220回"

        # 地方議会の年度パターン
        conference_local = Conference(
            id=2,
            name="東京都議会",
            governing_body_id=13,
            type="都道府県議会",
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
        # Empty strings
        conference_empty = Conference(
            name="Name",
            governing_body_id=1,
            type="",
            members_introduction_url="",
        )
        assert conference_empty.name == "Name"
        assert conference_empty.type == ""
        assert conference_empty.members_introduction_url == ""

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

        # Very long URL
        long_url = "https://example.com/" + "a" * 200
        conference_long_url = Conference(
            name="Test",
            governing_body_id=1,
            members_introduction_url=long_url,
        )
        assert conference_long_url.members_introduction_url == long_url

    def test_optional_fields_none_behavior(self) -> None:
        """Test behavior when optional fields are explicitly set to None."""
        conference = Conference(
            name="Test Conference",
            governing_body_id=1,
            type=None,
            members_introduction_url=None,
            prefecture=None,
        )

        assert conference.type is None
        assert conference.members_introduction_url is None
        assert conference.prefecture is None

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

    def test_committee_types(self) -> None:
        """Test various committee types."""
        committee_types = [
            ("総務委員会", "常任委員会"),
            ("文教委員会", "常任委員会"),
            ("予算特別委員会", "特別委員会"),
            ("決算特別委員会", "特別委員会"),
            ("議会運営委員会", "議会運営委員会"),
        ]

        for name, conf_type in committee_types:
            conference = Conference(
                name=name,
                governing_body_id=1,
                type=conf_type,
            )
            assert conference.name == name
            assert conference.type == conf_type
