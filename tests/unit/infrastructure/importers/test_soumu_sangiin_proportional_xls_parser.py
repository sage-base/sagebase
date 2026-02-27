"""総務省参議院比例代表XLSパーサーのテスト."""

from src.infrastructure.importers.soumu_sangiin_proportional_xls_parser import (
    _clean_cell,
    _clean_name,
    _detect_header_columns,
    _find_section_starts,
    _is_elected,
    _is_meibo_torokusha_file,
    _parse_fallback,
    _parse_int,
    _parse_meibo_torokusha,
    _parse_with_header,
)


class TestCleanCell:
    """セル値クリーンアップのテスト."""

    def test_none(self) -> None:
        assert _clean_cell(None) == ""

    def test_empty_string(self) -> None:
        assert _clean_cell("") == ""

    def test_whitespace(self) -> None:
        assert _clean_cell("  ") == ""

    def test_normal_string(self) -> None:
        assert _clean_cell("自由民主党") == "自由民主党"

    def test_full_width_numbers(self) -> None:
        assert _clean_cell("１２３") == "123"


class TestParseInt:
    """int変換のテスト."""

    def test_none(self) -> None:
        assert _parse_int(None) == 0

    def test_int_value(self) -> None:
        assert _parse_int(3) == 3

    def test_float_value(self) -> None:
        assert _parse_int(3.0) == 3

    def test_string_with_comma(self) -> None:
        assert _parse_int("1,234") == 1234

    def test_invalid_string(self) -> None:
        assert _parse_int("abc") == 0


class TestCleanName:
    """候補者名クリーンアップのテスト."""

    def test_normal_name(self) -> None:
        assert _clean_name("山田太郎") == "山田太郎"

    def test_name_with_spaces(self) -> None:
        assert _clean_name("山田 太郎") == "山田太郎"

    def test_name_with_fullwidth_space(self) -> None:
        assert _clean_name("山田\u3000太郎") == "山田太郎"

    def test_empty(self) -> None:
        assert _clean_name("") == ""

    def test_digit_only(self) -> None:
        assert _clean_name("123") == ""


class TestIsElected:
    """当選判定のテスト."""

    def test_elected_mark(self) -> None:
        assert _is_elected("当") is True

    def test_elected_full(self) -> None:
        assert _is_elected("当選") is True

    def test_circle(self) -> None:
        assert _is_elected("○") is True

    def test_not_elected(self) -> None:
        assert _is_elected("落") is False

    def test_empty(self) -> None:
        assert _is_elected("") is False


class TestIsMeiboTorokusha:
    """名簿登載者ファイル判定のテスト."""

    def test_matches(self) -> None:
        rows: list[tuple[object, ...]] = [
            ("（１０）党派別名簿登載者別得票数、当選人数（比例代表）", "", ""),
        ]
        assert _is_meibo_torokusha_file(rows) is True

    def test_not_matches(self) -> None:
        rows: list[tuple[object, ...]] = [
            ("（３）党派別得票数（比例代表）", "", ""),
        ]
        assert _is_meibo_torokusha_file(rows) is False


class TestFindSectionStarts:
    """セクション開始行検出のテスト."""

    def test_finds_sections(self) -> None:
        rows: list[tuple[object, ...]] = [
            ("タイトル", ""),
            ("", ""),
            ("政党等の名称", ""),
            ("", ""),
            ("データ", ""),
            ("政党等の名称", ""),
        ]
        assert _find_section_starts(rows) == [2, 5]

    def test_no_sections(self) -> None:
        rows: list[tuple[object, ...]] = [("foo", ""), ("bar", "")]
        assert _find_section_starts(rows) == []


class TestParseMeiboTorokusha:
    """名簿登載者別パーサーのテスト."""

    def test_basic_parse(self) -> None:
        """基本的な横並びセクション構造をパースできる."""
        # 6列幅 x 2政党
        rows: list[tuple[object, ...]] = [
            (
                "（１０）党派別名簿登載者別得票数",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ),
            ("", "", "", "", "", "", "", "", "", "", "", ""),
            ("政党等の名称", "", "", "", "", "", "政党等の名称", "", "", "", "", ""),
            # +1: 政党名（offset+3列）
            ("", "", "", "自由民主党", "", "", "", "", "", "立憲民主党", "", ""),
            # +2〜+8: メタ行
            ("", "", "", "", "", "", "", "", "", "", "", ""),
            ("得票総数", "", "", "100000", "", "", "得票総数", "", "", "80000", "", ""),
            (
                "政党等の得票総数(a)",
                "",
                "",
                "",
                "",
                "60000",
                "政党等の得票総数(a)",
                "",
                "",
                "",
                "",
                "50000",
            ),
            (
                "名簿登載者の得票総数(b)",
                "",
                "",
                "",
                "",
                "40000",
                "名簿登載者の得票総数(b)",
                "",
                "",
                "",
                "",
                "30000",
            ),
            ("名簿登載者数", "", "", "", "3", "", "名簿登載者数", "", "", "", "2", ""),
            ("当選人数", "", "", "2", "", "", "当選人数", "", "", "1", "", ""),
            ("", "", "", "", "", "", "", "", "", "", "", ""),
            # +9: ヘッダー（得票順位 当落 名簿登載者名 ...）
            (
                "得票順位",
                "当落",
                "名簿登載者名",
                "",
                "得票数",
                "",
                "得票順位",
                "当落",
                "名簿登載者名",
                "",
                "得票数",
                "",
            ),
            ("", "", "", "", "", "", "", "", "", "", "", ""),
            # +11: データ行
            (
                "1",
                "当",
                "山田\u3000太郎",
                "",
                "",
                "50000",
                "1",
                "当",
                "鈴木\u3000花子",
                "",
                "",
                "40000",
            ),
            (
                "2",
                "当",
                "佐藤\u3000次郎",
                "",
                "",
                "30000",
                "2",
                "",
                "田中\u3000三郎",
                "",
                "",
                "20000",
            ),
            ("3", "", "高橋\u3000四郎", "", "", "20000", "", "", "", "", "", ""),
        ]

        candidates = _parse_meibo_torokusha(rows)
        assert len(candidates) == 5

        # 自由民主党
        assert candidates[0].name == "山田太郎"
        assert candidates[0].party_name == "自由民主党"
        assert candidates[0].is_elected is True
        assert candidates[1].name == "佐藤次郎"
        assert candidates[1].party_name == "自由民主党"
        assert candidates[1].is_elected is True
        assert candidates[2].name == "高橋四郎"
        assert candidates[2].party_name == "自由民主党"
        assert candidates[2].is_elected is False

        # 立憲民主党
        assert candidates[3].name == "鈴木花子"
        assert candidates[3].party_name == "立憲民主党"
        assert candidates[3].is_elected is True
        assert candidates[4].name == "田中三郎"
        assert candidates[4].party_name == "立憲民主党"
        assert candidates[4].is_elected is False

    def test_all_candidates_have_proportional_block(self) -> None:
        """全候補者のblock_nameが「比例代表」."""
        rows: list[tuple[object, ...]] = [
            ("（１０）党派別名簿登載者別得票数", "", "", "", "", ""),
            ("", "", "", "", "", ""),
            ("政党等の名称", "", "", "", "", ""),
            ("", "", "", "テスト党", "", ""),
            ("", "", "", "", "", ""),
            ("得票総数", "", "", "100", "", ""),
            ("政党等の得票総数(a)", "", "", "", "", "60"),
            ("名簿登載者の得票総数(b)", "", "", "", "", "40"),
            ("名簿登載者数", "", "", "", "1", ""),
            ("当選人数", "", "", "1", "", ""),
            ("", "", "", "", "", ""),
            ("得票順位", "当落", "名簿登載者名", "", "得票数", ""),
            ("", "", "", "", "", ""),
            ("1", "当", "テスト太郎", "", "", "100"),
        ]
        candidates = _parse_meibo_torokusha(rows)
        assert len(candidates) == 1
        assert candidates[0].block_name == "比例代表"


class TestDetectHeaderColumns:
    """ヘッダー検出のテスト."""

    def test_standard_header(self) -> None:
        rows: list[tuple[object, ...]] = [
            ("回次", "候補者名", "政党名", "当落", "得票数"),
        ]
        result = _detect_header_columns(rows)
        assert result is not None
        assert result["name"] == 1
        assert result["party"] == 2
        assert result["elected"] == 3

    def test_header_with_shimei(self) -> None:
        rows: list[tuple[object, ...]] = [
            ("", "氏名", "", "当選", ""),
        ]
        result = _detect_header_columns(rows)
        assert result is not None
        assert result["name"] == 1
        assert result["elected"] == 3

    def test_no_header(self) -> None:
        rows: list[tuple[object, ...]] = [
            ("foo", "bar", "baz"),
            (1, 2, 3),
        ]
        result = _detect_header_columns(rows)
        assert result is None


class TestParseWithHeader:
    """ヘッダーベースパーサーのテスト."""

    def test_basic_parse(self) -> None:
        rows: list[tuple[object, ...]] = [
            ("No", "候補者名", "政党名", "当落", "得票数"),
            (1, "山田太郎", "自由民主党", "当", 50000),
            (2, "鈴木花子", "立憲民主党", "", 30000),
            (3, "佐藤一郎", "公明党", "当", 40000),
        ]
        columns = _detect_header_columns(rows)
        assert columns is not None
        candidates = _parse_with_header(rows, columns)

        assert len(candidates) == 3
        assert candidates[0].name == "山田太郎"
        assert candidates[0].party_name == "自由民主党"
        assert candidates[0].is_elected is True
        assert candidates[1].name == "鈴木花子"
        assert candidates[1].is_elected is False
        assert candidates[2].name == "佐藤一郎"
        assert candidates[2].is_elected is True

    def test_party_inheritance_from_section(self) -> None:
        """政党名がない行は直前の政党名を引き継ぐ."""
        rows: list[tuple[object, ...]] = [
            ("No", "候補者名", "政党名", "当落", "得票数"),
            ("", "", "自由民主党", "", ""),
            (1, "山田太郎", "", "当", 50000),
            (2, "鈴木花子", "", "当", 40000),
        ]
        columns = _detect_header_columns(rows)
        assert columns is not None
        candidates = _parse_with_header(rows, columns)
        assert len(candidates) == 2
        assert candidates[0].party_name == "自由民主党"
        assert candidates[1].party_name == "自由民主党"


class TestParseFallback:
    """フォールバックパーサーのテスト."""

    def test_basic_fallback(self) -> None:
        rows: list[tuple[object, ...]] = [
            ("自由民主党", "", "", "", ""),
            ("当", "山田太郎", "", "50000", ""),
            ("", "鈴木花子", "", "30000", ""),
        ]
        candidates = _parse_fallback(rows)
        assert len(candidates) == 2
        assert candidates[0].name == "山田太郎"
        assert candidates[0].party_name == "自由民主党"
        assert candidates[0].is_elected is True
        assert candidates[1].name == "鈴木花子"
        assert candidates[1].party_name == "自由民主党"
        assert candidates[1].is_elected is False

    def test_party_section_detection(self) -> None:
        rows: list[tuple[object, ...]] = [
            ("自由民主党", "", ""),
            ("当", "山田太郎", ""),
            ("立憲民主党", "", ""),
            ("当", "佐藤次郎", ""),
        ]
        candidates = _parse_fallback(rows)
        assert len(candidates) == 2
        assert candidates[0].party_name == "自由民主党"
        assert candidates[1].party_name == "立憲民主党"
