"""和暦日付入力コンポーネント

和暦/西暦切り替え可能な日付入力UIを提供する。
既存の st.date_input と同様のインターフェースで、和暦入力モードを追加する。
"""

import calendar

from datetime import date

import streamlit as st

from src.domain.utils.japanese_era import ERA_DEFINITIONS, JapaneseEraConverter


_converter = JapaneseEraConverter()


def japanese_era_date_input(
    label: str,
    value: date | None = None,
    key: str = "japanese_era_date",
    min_value: date | None = None,
    max_value: date | None = None,
    help: str | None = None,
) -> date:
    """和暦/西暦切り替え可能な日付入力コンポーネント

    Args:
        label: ラベル文字列
        value: デフォルトの日付値（Noneの場合はdate.today()）
        key: Streamlitウィジェットのキープレフィックス
        min_value: 最小日付（この日付より前は選択不可）
        max_value: 最大日付（この日付より後は選択不可）
        help: ヘルプテキスト（ラベル下に表示）

    Returns:
        選択された日付（dateオブジェクト、西暦）
    """
    if value is None:
        value = date.today()

    st.markdown(f"**{label}**")
    if help:
        st.caption(help)

    # 入力モード切替
    mode = st.radio(
        "入力モード",
        options=["和暦", "西暦"],
        horizontal=True,
        key=f"{key}_mode",
        label_visibility="collapsed",
    )

    if mode == "西暦":
        return _render_western_mode(
            value, key, min_value=min_value, max_value=max_value
        )
    else:
        return _render_japanese_era_mode(
            value, key, min_value=min_value, max_value=max_value
        )


def _render_western_mode(
    value: date,
    key: str,
    min_value: date | None = None,
    max_value: date | None = None,
) -> date:
    """西暦入力モードをレンダリングする"""
    result = st.date_input(
        "日付",
        value=value,
        key=f"{key}_western",
        label_visibility="collapsed",
        min_value=min_value,
        max_value=max_value,
    )
    # st.date_input は単一値の場合 date を返す
    if isinstance(result, date):
        return result
    return value


def _render_japanese_era_mode(
    value: date,
    key: str,
    min_value: date | None = None,
    max_value: date | None = None,
) -> date:
    """和暦入力モードをレンダリングする"""
    # デフォルト値から和暦情報を取得
    default_era, default_era_year = _get_default_era_values(value)

    era_names = [e.name for e in ERA_DEFINITIONS]
    default_era_index = era_names.index(default_era) if default_era in era_names else 0

    col_era, col_year, col_month, col_day = st.columns([2, 1.5, 1, 1])

    with col_era:
        selected_era = st.selectbox(
            "元号",
            options=era_names,
            index=default_era_index,
            key=f"{key}_era",
        )

    # 選択された元号の年の最大値を計算
    max_year = _get_max_era_year(selected_era)
    clamped_era_year = min(default_era_year, max_year)

    with col_year:
        era_year = int(
            st.number_input(
                "年",
                min_value=1,
                max_value=max_year,
                value=clamped_era_year,
                step=1,
                key=f"{key}_year",
            )
        )

    with col_month:
        month = int(
            st.number_input(
                "月",
                min_value=1,
                max_value=12,
                value=value.month,
                step=1,
                key=f"{key}_month",
            )
        )

    # 日の最大値を計算（閏年・月に応じて動的に変更）
    western_year = _converter.to_western_year(selected_era, era_year)
    max_day = _get_max_day(western_year, month)
    clamped_day = min(value.day, max_day)

    with col_day:
        day = int(
            st.number_input(
                "日",
                min_value=1,
                max_value=max_day,
                value=clamped_day,
                step=1,
                key=f"{key}_day",
            )
        )

    # date オブジェクトを生成
    try:
        result = date(western_year, month, day)
    except ValueError:
        st.error(f"無効な日付です: {western_year}年{month}月{day}日")
        return value

    # min_value/max_value バリデーション
    if min_value is not None and result < min_value:
        st.warning(f"最小日付（{min_value}）より前の日付は指定できません")
        return min_value
    if max_value is not None and result > max_value:
        st.warning(f"最大日付（{max_value}）より後の日付は指定できません")
        return max_value

    return result


def _get_default_era_values(value: date) -> tuple[str, int]:
    """dateオブジェクトからデフォルトの元号名・元号年を取得する"""
    try:
        return _converter.to_japanese_era(value.year)
    except ValueError:
        return (ERA_DEFINITIONS[0].name, 1)


def _get_max_era_year(era_name: str) -> int:
    """指定された元号の最大年を返す"""
    era_def = next((e for e in ERA_DEFINITIONS if e.name == era_name), None)
    if era_def is None:
        return 99
    if era_def.end_year is not None:
        return era_def.end_year - era_def.start_year
    # 進行中の元号は99を上限とする
    return 99


def _get_max_day(year: int, month: int) -> int:
    """指定された年・月の最大日数を返す"""
    try:
        return calendar.monthrange(year, month)[1]
    except ValueError:
        return 31
