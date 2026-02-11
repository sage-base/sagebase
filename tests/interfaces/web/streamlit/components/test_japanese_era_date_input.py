"""和暦日付入力コンポーネントのテスト"""

from datetime import date
from unittest.mock import MagicMock, patch

from src.interfaces.web.streamlit.components.japanese_era_date_input import (
    _get_default_era_values,
    _get_max_day,
    _get_max_era_year,
    _render_japanese_era_mode,
    _render_western_mode,
    japanese_era_date_input,
)


class TestGetDefaultEraValues:
    """dateオブジェクトからデフォルト元号値を取得するテスト"""

    def test_reiwa_date(self):
        """令和の日付から元号・年を正しく取得できること"""
        era, year = _get_default_era_values(date(2025, 2, 10))
        assert era == "令和"
        assert year == 7

    def test_heisei_date(self):
        """平成の日付から元号・年を正しく取得できること"""
        era, year = _get_default_era_values(date(2018, 12, 1))
        assert era == "平成"
        assert year == 30

    def test_showa_date(self):
        """昭和の日付から元号・年を正しく取得できること"""
        era, year = _get_default_era_values(date(1988, 1, 1))
        assert era == "昭和"
        assert year == 63

    def test_taisho_date(self):
        """大正の日付から元号・年を正しく取得できること"""
        era, year = _get_default_era_values(date(1920, 6, 15))
        assert era == "大正"
        assert year == 9

    def test_out_of_range_date_returns_latest_era(self):
        """範囲外の日付はERA_DEFINITIONSの先頭元号をフォールバックとして返すこと"""
        era, year = _get_default_era_values(date(1900, 1, 1))
        assert era == "令和"
        assert year == 1


class TestGetMaxEraYear:
    """元号の最大年を返す関数のテスト"""

    def test_reiwa_returns_99(self):
        """令和（進行中）は99を返すこと"""
        assert _get_max_era_year("令和") == 99

    def test_heisei_returns_30(self):
        """平成は30を返すこと（2019-1989=30）"""
        assert _get_max_era_year("平成") == 30

    def test_showa_returns_63(self):
        """昭和は63を返すこと（1989-1926=63）"""
        assert _get_max_era_year("昭和") == 63

    def test_taisho_returns_14(self):
        """大正は14を返すこと（1926-1912=14）"""
        assert _get_max_era_year("大正") == 14

    def test_unsupported_era_returns_99(self):
        """未対応の元号は99を返すこと"""
        assert _get_max_era_year("不明") == 99


class TestGetMaxDay:
    """月の最大日数を返す関数のテスト"""

    def test_january_has_31_days(self):
        assert _get_max_day(2025, 1) == 31

    def test_february_non_leap_year(self):
        """平年の2月は28日"""
        assert _get_max_day(2025, 2) == 28

    def test_february_leap_year(self):
        """閏年の2月は29日"""
        assert _get_max_day(2024, 2) == 29

    def test_april_has_30_days(self):
        assert _get_max_day(2025, 4) == 30

    def test_december_has_31_days(self):
        assert _get_max_day(2025, 12) == 31


@patch("src.interfaces.web.streamlit.components.japanese_era_date_input.st")
class TestJapaneseEraDateInput:
    """コンポーネント全体のテスト"""

    def test_western_mode_returns_date_input_result(self, mock_st):
        """西暦モードではst.date_inputの結果を返すこと"""
        mock_st.radio.return_value = "西暦"
        expected_date = date(2025, 3, 15)
        mock_st.date_input.return_value = expected_date

        result = japanese_era_date_input(
            "テスト日付", value=date(2025, 1, 1), key="test"
        )

        assert result == expected_date
        mock_st.date_input.assert_called_once()

    def test_japanese_era_mode_returns_converted_date(self, mock_st):
        """和暦モードで正しい日付を返すこと"""
        mock_st.radio.return_value = "和暦"
        mock_st.columns.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]
        mock_st.selectbox.return_value = "令和"
        mock_st.number_input.side_effect = [7, 2, 10]

        result = japanese_era_date_input(
            "テスト日付", value=date(2025, 2, 10), key="test"
        )

        assert result == date(2025, 2, 10)

    def test_default_value_is_today_when_none(self, mock_st):
        """valueがNoneの場合はdate.today()をデフォルトとすること"""
        mock_st.radio.return_value = "西暦"
        today = date.today()
        mock_st.date_input.return_value = today

        result = japanese_era_date_input("テスト日付", key="test")

        assert result == today

    def test_mode_toggle_uses_correct_key(self, mock_st):
        """モード切替ラジオに正しいキーが設定されること"""
        mock_st.radio.return_value = "西暦"
        mock_st.date_input.return_value = date(2025, 1, 1)

        japanese_era_date_input("テスト", value=date(2025, 1, 1), key="my_date")

        mock_st.radio.assert_called_once()
        call_kwargs = mock_st.radio.call_args
        assert call_kwargs.kwargs["key"] == "my_date_mode"


@patch("src.interfaces.web.streamlit.components.japanese_era_date_input.st")
class TestRenderJapaneseEraMode:
    """和暦入力モードのレンダリングテスト"""

    def test_renders_four_columns(self, mock_st):
        """4列のカラムが生成されること"""
        mock_st.columns.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]
        mock_st.selectbox.return_value = "令和"
        mock_st.number_input.side_effect = [7, 2, 10]

        _render_japanese_era_mode(date(2025, 2, 10), "test")

        mock_st.columns.assert_called_once_with([2, 1.5, 1, 1])

    def test_invalid_date_shows_error_and_returns_fallback(self, mock_st):
        """無効な日付の場合にエラーを表示しフォールバック値を返すこと"""
        mock_st.columns.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]
        mock_st.selectbox.return_value = "令和"
        # モックがday=30を返すことで date(2025, 2, 30) の生成を試みる
        mock_st.number_input.side_effect = [7, 2, 30]

        fallback = date(2025, 2, 10)
        result = _render_japanese_era_mode(fallback, "test")

        assert result == fallback
        mock_st.error.assert_called_once()


@patch("src.interfaces.web.streamlit.components.japanese_era_date_input.st")
class TestRenderWesternMode:
    """西暦入力モードのレンダリングテスト"""

    def test_returns_date_from_date_input(self, mock_st):
        """st.date_inputのdate結果をそのまま返すこと"""
        expected = date(2025, 6, 1)
        mock_st.date_input.return_value = expected

        result = _render_western_mode(date(2025, 1, 1), "test")

        assert result == expected

    def test_returns_fallback_when_non_date_returned(self, mock_st):
        """st.date_inputがdate以外を返す場合にフォールバック値を返すこと"""
        mock_st.date_input.return_value = (
            date(2025, 1, 1),
            date(2025, 12, 31),
        )
        fallback = date(2025, 3, 1)

        result = _render_western_mode(fallback, "test")

        assert result == fallback

    def test_min_value_passed_to_date_input(self, mock_st):
        """min_valueがst.date_inputに渡されること"""
        mock_st.date_input.return_value = date(2025, 1, 1)
        min_val = date(1947, 4, 1)

        _render_western_mode(date(2025, 1, 1), "test", min_value=min_val)

        call_kwargs = mock_st.date_input.call_args
        assert call_kwargs.kwargs["min_value"] == min_val

    def test_max_value_passed_to_date_input(self, mock_st):
        """max_valueがst.date_inputに渡されること"""
        mock_st.date_input.return_value = date(2025, 1, 1)
        max_val = date(2030, 12, 31)

        _render_western_mode(date(2025, 1, 1), "test", max_value=max_val)

        call_kwargs = mock_st.date_input.call_args
        assert call_kwargs.kwargs["max_value"] == max_val

    def test_no_min_max_when_not_specified(self, mock_st):
        """min_value/max_value未指定時はst.date_inputに渡さないこと"""
        mock_st.date_input.return_value = date(2025, 1, 1)

        _render_western_mode(date(2025, 1, 1), "test")

        call_kwargs = mock_st.date_input.call_args
        assert "min_value" not in call_kwargs.kwargs
        assert "max_value" not in call_kwargs.kwargs


@patch("src.interfaces.web.streamlit.components.japanese_era_date_input.st")
class TestMinMaxValueValidation:
    """min_value/max_valueバリデーションのテスト"""

    def _setup_era_mode_mocks(self, mock_st, era_year, month, day):
        """和暦モードのモックをセットアップする"""
        mock_st.columns.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]
        mock_st.selectbox.return_value = "令和"
        mock_st.number_input.side_effect = [era_year, month, day]

    def test_japanese_era_mode_min_value_violation_returns_min(self, mock_st):
        """和暦モードでmin_valueより前の日付を入力した場合、min_valueを返すこと"""
        self._setup_era_mode_mocks(mock_st, era_year=1, month=1, day=1)
        min_val = date(2020, 1, 1)

        result = _render_japanese_era_mode(date(2019, 1, 1), "test", min_value=min_val)

        assert result == min_val
        mock_st.warning.assert_called_once()

    def test_japanese_era_mode_max_value_violation_returns_max(self, mock_st):
        """和暦モードでmax_valueより後の日付を入力した場合、max_valueを返すこと"""
        self._setup_era_mode_mocks(mock_st, era_year=99, month=12, day=31)
        max_val = date(2030, 12, 31)

        result = _render_japanese_era_mode(
            date(2117, 12, 31), "test", max_value=max_val
        )

        assert result == max_val
        mock_st.warning.assert_called_once()

    def test_japanese_era_mode_within_range_returns_date(self, mock_st):
        """和暦モードで範囲内の日付はそのまま返すこと"""
        self._setup_era_mode_mocks(mock_st, era_year=7, month=6, day=15)
        min_val = date(2020, 1, 1)
        max_val = date(2030, 12, 31)

        result = _render_japanese_era_mode(
            date(2025, 6, 15), "test", min_value=min_val, max_value=max_val
        )

        assert result == date(2025, 6, 15)
        mock_st.warning.assert_not_called()

    def test_help_text_displayed(self, mock_st):
        """helpパラメータ指定時にst.captionが呼ばれること"""
        mock_st.radio.return_value = "西暦"
        mock_st.date_input.return_value = date(2025, 1, 1)

        japanese_era_date_input(
            "テスト日付",
            value=date(2025, 1, 1),
            key="test",
            help="テスト用ヘルプ",
        )

        mock_st.caption.assert_called_once_with("テスト用ヘルプ")

    def test_help_text_not_displayed_when_none(self, mock_st):
        """helpパラメータ未指定時はst.captionが呼ばれないこと"""
        mock_st.radio.return_value = "西暦"
        mock_st.date_input.return_value = date(2025, 1, 1)

        japanese_era_date_input(
            "テスト日付",
            value=date(2025, 1, 1),
            key="test",
        )

        mock_st.caption.assert_not_called()
