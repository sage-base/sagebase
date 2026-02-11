"""和暦⇔西暦変換ユーティリティのテスト"""

from datetime import date

import pytest

from src.domain.utils.japanese_era import JapaneseEraConverter


@pytest.fixture
def converter() -> JapaneseEraConverter:
    return JapaneseEraConverter()


class TestToWesternYear:
    """to_western_year のテスト"""

    def test_reiwa_5_to_2023(self, converter: JapaneseEraConverter) -> None:
        assert converter.to_western_year("令和", 5) == 2023

    def test_reiwa_1_to_2019(self, converter: JapaneseEraConverter) -> None:
        assert converter.to_western_year("令和", 1) == 2019

    def test_heisei_30_to_2018(self, converter: JapaneseEraConverter) -> None:
        assert converter.to_western_year("平成", 30) == 2018

    def test_heisei_1_to_1989(self, converter: JapaneseEraConverter) -> None:
        assert converter.to_western_year("平成", 1) == 1989

    def test_showa_64_out_of_range(self, converter: JapaneseEraConverter) -> None:
        # 昭和の終了年は1989年なので、昭和64年(=1989)はend_year以上で範囲外
        with pytest.raises(ValueError, match="範囲外"):
            converter.to_western_year("昭和", 64)

    def test_showa_63_to_1988(self, converter: JapaneseEraConverter) -> None:
        assert converter.to_western_year("昭和", 63) == 1988

    def test_showa_1_to_1926(self, converter: JapaneseEraConverter) -> None:
        assert converter.to_western_year("昭和", 1) == 1926

    def test_taisho_15_out_of_range(self, converter: JapaneseEraConverter) -> None:
        # 大正の終了年は1926年なので、大正15年(=1926)はend_year以上で範囲外
        with pytest.raises(ValueError, match="範囲外"):
            converter.to_western_year("大正", 15)

    def test_taisho_14_to_1925(self, converter: JapaneseEraConverter) -> None:
        assert converter.to_western_year("大正", 14) == 1925

    def test_taisho_1_to_1912(self, converter: JapaneseEraConverter) -> None:
        assert converter.to_western_year("大正", 1) == 1912

    def test_invalid_era_name_raises_value_error(
        self, converter: JapaneseEraConverter
    ) -> None:
        with pytest.raises(ValueError, match="不正な元号名"):
            converter.to_western_year("明治", 1)

    def test_era_year_zero_raises_value_error(
        self, converter: JapaneseEraConverter
    ) -> None:
        with pytest.raises(ValueError, match="1以上"):
            converter.to_western_year("令和", 0)

    def test_negative_era_year_raises_value_error(
        self, converter: JapaneseEraConverter
    ) -> None:
        with pytest.raises(ValueError, match="1以上"):
            converter.to_western_year("令和", -1)


class TestToJapaneseEra:
    """to_japanese_era のテスト"""

    def test_2023_to_reiwa_5(self, converter: JapaneseEraConverter) -> None:
        assert converter.to_japanese_era(2023) == ("令和", 5)

    def test_2019_to_reiwa_1(self, converter: JapaneseEraConverter) -> None:
        # 境界年は新しい元号を優先
        assert converter.to_japanese_era(2019) == ("令和", 1)

    def test_2018_to_heisei_30(self, converter: JapaneseEraConverter) -> None:
        assert converter.to_japanese_era(2018) == ("平成", 30)

    def test_1989_to_heisei_1(self, converter: JapaneseEraConverter) -> None:
        # 境界年は新しい元号を優先
        assert converter.to_japanese_era(1989) == ("平成", 1)

    def test_1988_to_showa_63(self, converter: JapaneseEraConverter) -> None:
        assert converter.to_japanese_era(1988) == ("昭和", 63)

    def test_1926_to_showa_1(self, converter: JapaneseEraConverter) -> None:
        assert converter.to_japanese_era(1926) == ("昭和", 1)

    def test_1925_to_taisho_14(self, converter: JapaneseEraConverter) -> None:
        assert converter.to_japanese_era(1925) == ("大正", 14)

    def test_1912_to_taisho_1(self, converter: JapaneseEraConverter) -> None:
        assert converter.to_japanese_era(1912) == ("大正", 1)

    def test_1911_out_of_range_raises_value_error(
        self, converter: JapaneseEraConverter
    ) -> None:
        with pytest.raises(ValueError, match="対応範囲外"):
            converter.to_japanese_era(1911)


class TestParseDate:
    """parse_date のテスト"""

    def test_reiwa_full_date(self, converter: JapaneseEraConverter) -> None:
        assert converter.parse_date("令和5年3月15日") == date(2023, 3, 15)

    def test_heisei_full_date(self, converter: JapaneseEraConverter) -> None:
        assert converter.parse_date("平成30年12月1日") == date(2018, 12, 1)

    def test_showa_full_date(self, converter: JapaneseEraConverter) -> None:
        assert converter.parse_date("昭和50年6月20日") == date(1975, 6, 20)

    def test_taisho_full_date(self, converter: JapaneseEraConverter) -> None:
        assert converter.parse_date("大正10年1月1日") == date(1921, 1, 1)

    def test_year_only_defaults_to_jan_1(self, converter: JapaneseEraConverter) -> None:
        assert converter.parse_date("令和5年") == date(2023, 1, 1)

    def test_year_month_defaults_to_day_1(
        self, converter: JapaneseEraConverter
    ) -> None:
        assert converter.parse_date("令和5年3月") == date(2023, 3, 1)

    def test_gannen_reiwa(self, converter: JapaneseEraConverter) -> None:
        # 「元年」は1年と同じ
        assert converter.parse_date("令和元年5月1日") == date(2019, 5, 1)

    def test_gannen_heisei(self, converter: JapaneseEraConverter) -> None:
        assert converter.parse_date("平成元年1月8日") == date(1989, 1, 8)

    def test_gannen_year_only(self, converter: JapaneseEraConverter) -> None:
        assert converter.parse_date("令和元年") == date(2019, 1, 1)

    def test_gannen_and_numeric_1_are_equivalent(
        self, converter: JapaneseEraConverter
    ) -> None:
        # 「平成元年」と「平成1年」は同じ結果
        assert converter.parse_date("平成元年1月8日") == converter.parse_date(
            "平成1年1月8日"
        )

    def test_strips_whitespace(self, converter: JapaneseEraConverter) -> None:
        assert converter.parse_date("  令和5年3月15日  ") == date(2023, 3, 15)

    def test_western_date_raises_value_error(
        self, converter: JapaneseEraConverter
    ) -> None:
        with pytest.raises(ValueError, match="パースできません"):
            converter.parse_date("2023年3月15日")

    def test_invalid_date_raises_value_error(
        self, converter: JapaneseEraConverter
    ) -> None:
        with pytest.raises(ValueError, match="不正な日付"):
            converter.parse_date("令和5年2月30日")

    def test_empty_string_raises_value_error(
        self, converter: JapaneseEraConverter
    ) -> None:
        with pytest.raises(ValueError, match="パースできません"):
            converter.parse_date("")


class TestFormatDate:
    """format_date のテスト"""

    def test_reiwa_date(self, converter: JapaneseEraConverter) -> None:
        assert converter.format_date(date(2023, 3, 15)) == "令和5年3月15日"

    def test_heisei_date(self, converter: JapaneseEraConverter) -> None:
        assert converter.format_date(date(2018, 12, 1)) == "平成30年12月1日"

    def test_showa_date(self, converter: JapaneseEraConverter) -> None:
        assert converter.format_date(date(1975, 6, 20)) == "昭和50年6月20日"

    def test_taisho_date(self, converter: JapaneseEraConverter) -> None:
        assert converter.format_date(date(1921, 1, 1)) == "大正10年1月1日"

    def test_out_of_range_raises_value_error(
        self, converter: JapaneseEraConverter
    ) -> None:
        with pytest.raises(ValueError, match="対応範囲外"):
            converter.format_date(date(1900, 1, 1))


class TestRoundTrip:
    """parse_date と format_date の往復変換テスト"""

    @pytest.mark.parametrize(
        "wareki_str",
        [
            "令和5年3月15日",
            "平成30年12月1日",
            "昭和50年6月20日",
            "大正10年1月1日",
        ],
    )
    def test_round_trip_preserves_value(
        self, converter: JapaneseEraConverter, wareki_str: str
    ) -> None:
        d = converter.parse_date(wareki_str)
        assert converter.format_date(d) == wareki_str
