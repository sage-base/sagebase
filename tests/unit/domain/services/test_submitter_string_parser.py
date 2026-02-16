"""提出者文字列パーサーのテスト."""

import pytest

from src.domain.services.submitter_string_parser import (
    kansuji_to_int,
    parse_submitter_string,
)


class TestKansujiToInt:
    """漢数字→整数変換のテスト."""

    @pytest.mark.parametrize(
        ("input_text", "expected"),
        [
            ("一", 1),
            ("二", 2),
            ("三", 3),
            ("四", 4),
            ("五", 5),
            ("六", 6),
            ("七", 7),
            ("八", 8),
            ("九", 9),
            ("十", 10),
            ("十一", 11),
            ("十二", 12),
            ("二十", 20),
            ("二十三", 23),
            ("三十五", 35),
            ("九十九", 99),
            ("百", 100),
        ],
    )
    def test_kanji_numerals(self, input_text: str, expected: int) -> None:
        """漢数字が正しく変換される."""
        assert kansuji_to_int(input_text) == expected

    @pytest.mark.parametrize(
        ("input_text", "expected"),
        [
            ("1", 1),
            ("4", 4),
            ("12", 12),
            ("99", 99),
        ],
    )
    def test_arabic_numerals(self, input_text: str, expected: int) -> None:
        """算用数字がそのまま変換される."""
        assert kansuji_to_int(input_text) == expected

    @pytest.mark.parametrize(
        ("input_text", "expected"),
        [
            ("１", 1),
            ("４", 4),
            ("１２", 12),
        ],
    )
    def test_fullwidth_numerals(self, input_text: str, expected: int) -> None:
        """全角数字が変換される."""
        assert kansuji_to_int(input_text) == expected

    def test_invalid_input_raises_error(self) -> None:
        """無効な入力でValueError."""
        with pytest.raises(ValueError, match="変換できない文字"):
            kansuji_to_int("あ")


class TestParseSubmitterString:
    """提出者文字列パーサーのテスト."""

    def test_soto_pattern_kanji(self) -> None:
        """「外N名」パターン（漢数字）."""
        result = parse_submitter_string("熊代昭彦君外四名")
        assert result.names == ["熊代昭彦"]
        assert result.total_count == 5

    def test_soto_pattern_arabic(self) -> None:
        """「外N名」パターン（算用数字）."""
        result = parse_submitter_string("熊代昭彦君外4名")
        assert result.names == ["熊代昭彦"]
        assert result.total_count == 5

    def test_soto_pattern_fullwidth(self) -> None:
        """「外N名」パターン（全角数字）."""
        result = parse_submitter_string("熊代昭彦君外４名")
        assert result.names == ["熊代昭彦"]
        assert result.total_count == 5

    def test_soto_pattern_no_honorific(self) -> None:
        """「外N名」パターン（敬称なし）."""
        result = parse_submitter_string("田中太郎外三名")
        assert result.names == ["田中太郎"]
        assert result.total_count == 4

    def test_soto_pattern_shi_honorific(self) -> None:
        """「外N名」パターン（氏）."""
        result = parse_submitter_string("山田花子氏外二名")
        assert result.names == ["山田花子"]
        assert result.total_count == 3

    def test_soto_pattern_giin_honorific(self) -> None:
        """「外N名」パターン（議員）."""
        result = parse_submitter_string("佐藤一郎議員外十名")
        assert result.names == ["佐藤一郎"]
        assert result.total_count == 11

    def test_comma_separated(self) -> None:
        """カンマ区切り."""
        result = parse_submitter_string("熊代昭彦,谷畑孝,棚橋泰文")
        assert result.names == ["熊代昭彦", "谷畑孝", "棚橋泰文"]
        assert result.total_count == 3

    def test_fullwidth_comma_separated(self) -> None:
        """全角カンマ区切り."""
        result = parse_submitter_string("熊代昭彦，谷畑孝，棚橋泰文")
        assert result.names == ["熊代昭彦", "谷畑孝", "棚橋泰文"]
        assert result.total_count == 3

    def test_touten_separated(self) -> None:
        """読点区切り."""
        result = parse_submitter_string("熊代昭彦、谷畑孝、棚橋泰文")
        assert result.names == ["熊代昭彦", "谷畑孝", "棚橋泰文"]
        assert result.total_count == 3

    def test_single_name(self) -> None:
        """単一名."""
        result = parse_submitter_string("田中太郎")
        assert result.names == ["田中太郎"]
        assert result.total_count == 1

    def test_single_name_with_honorific_kun(self) -> None:
        """敬称「君」付き単一名."""
        result = parse_submitter_string("田中太郎君")
        assert result.names == ["田中太郎"]
        assert result.total_count == 1

    def test_single_name_with_honorific_shi(self) -> None:
        """敬称「氏」付き単一名."""
        result = parse_submitter_string("田中太郎氏")
        assert result.names == ["田中太郎"]
        assert result.total_count == 1

    def test_single_name_with_honorific_giin(self) -> None:
        """敬称「議員」付き単一名."""
        result = parse_submitter_string("田中太郎議員")
        assert result.names == ["田中太郎"]
        assert result.total_count == 1

    def test_empty_string(self) -> None:
        """空文字列."""
        result = parse_submitter_string("")
        assert result.names == []
        assert result.total_count == 0

    def test_whitespace_only(self) -> None:
        """空白のみ."""
        result = parse_submitter_string("   ")
        assert result.names == []
        assert result.total_count == 0

    def test_total_count_never_less_than_names(self) -> None:
        """total_countはnames数以上."""
        result = parse_submitter_string("田中太郎,鈴木花子")
        assert result.total_count >= len(result.names)

    def test_comma_with_spaces(self) -> None:
        """カンマ区切りにスペースを含む."""
        result = parse_submitter_string("田中太郎, 鈴木花子, 佐藤一郎")
        assert result.names == ["田中太郎", "鈴木花子", "佐藤一郎"]
        assert result.total_count == 3
