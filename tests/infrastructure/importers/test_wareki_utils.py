"""和暦パースユーティリティのテスト."""

from datetime import date

import pytest

from src.infrastructure.importers._utils import parse_wareki_date, zen_to_han


class TestZenToHan:
    def test_fullwidth_digits(self) -> None:
        assert zen_to_han("０１２３４５６７８９") == "0123456789"

    def test_fullwidth_dot(self) -> None:
        assert zen_to_han("１．５") == "1.5"

    def test_halfwidth_passthrough(self) -> None:
        assert zen_to_han("abc123") == "abc123"

    def test_mixed(self) -> None:
        assert zen_to_han("令和６年") == "令和6年"


class TestParseWarekiDate:
    def test_reiwa(self) -> None:
        assert parse_wareki_date("令和6年10月27日") == date(2024, 10, 27)

    def test_heisei(self) -> None:
        assert parse_wareki_date("平成31年4月30日") == date(2019, 4, 30)

    def test_showa(self) -> None:
        assert parse_wareki_date("昭和64年1月7日") == date(1989, 1, 7)

    def test_taisho(self) -> None:
        assert parse_wareki_date("大正15年12月25日") == date(1926, 12, 25)

    def test_meiji(self) -> None:
        assert parse_wareki_date("明治45年7月30日") == date(1912, 7, 30)

    def test_fullwidth_digits(self) -> None:
        assert parse_wareki_date("令和６年１０月２７日") == date(2024, 10, 27)

    def test_trailing_text(self) -> None:
        assert parse_wareki_date("令和６年１０月２７日執行") == date(2024, 10, 27)

    def test_empty_string(self) -> None:
        assert parse_wareki_date("") is None

    def test_gannen(self) -> None:
        """「元年」を1年として扱う."""
        assert parse_wareki_date("令和元年5月1日") == date(2019, 5, 1)

    def test_gannen_heisei(self) -> None:
        """平成元年のパース."""
        assert parse_wareki_date("平成元年1月8日") == date(1989, 1, 8)

    def test_invalid_month_day(self) -> None:
        """不正な月日でNoneを返す."""
        assert parse_wareki_date("令和6年13月40日") is None

    def test_invalid_day(self) -> None:
        """不正な日でNoneを返す."""
        assert parse_wareki_date("令和6年2月30日") is None

    def test_no_match(self) -> None:
        assert parse_wareki_date("2024年10月27日") is None

    def test_incomplete_date(self) -> None:
        assert parse_wareki_date("令和6年10月") is None

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("平成10年 3月19日", date(1998, 3, 19)),
            ("平成10年 3月19日／可決", date(1998, 3, 19)),
        ],
    )
    def test_with_spaces_and_suffix(self, text: str, expected: date) -> None:
        """スペースやスラッシュ付きの入力でも日付部分を正しくパースする.

        re.searchで日付部分のみ抽出するため、後続テキストがあっても動作する。
        インポーター側でも安全のため「／」前で切り出している。
        """
        result = parse_wareki_date(text)
        assert result == expected
