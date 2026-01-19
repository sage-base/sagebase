"""List tab for conferences.

会議体一覧タブのUI実装を提供します。
"""

import asyncio

from typing import cast

import pandas as pd
import streamlit as st

from ..constants import CONFERENCE_PREFECTURES
from ..extraction.extractor import extract_members_from_conferences

from src.domain.repositories import GoverningBodyRepository
from src.interfaces.web.streamlit.presenters.conference_presenter import (
    ConferencePresenter,
)


def render_conferences_list(
    presenter: ConferencePresenter,
    governing_body_repo: GoverningBodyRepository,
) -> None:
    """Render conferences list tab.

    会議体一覧タブをレンダリングします。
    都道府県、開催主体、URL有無でのフィルタリング、議員情報の抽出などの機能を提供します。

    Args:
        presenter: 会議体プレゼンター
        governing_body_repo: 開催主体リポジトリ
    """
    st.header("会議体一覧")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        # 都道府県フィルター
        prefecture_filter_options = ["すべて"] + [
            p for p in CONFERENCE_PREFECTURES if p
        ]
        selected_prefecture = st.selectbox(
            "都道府県で絞り込み",
            options=prefecture_filter_options,
            key="filter_prefecture",
        )

    with col2:
        # Load governing bodies for filter
        governing_bodies = governing_body_repo.get_all()
        gb_options = {"すべて": None}
        gb_options.update({f"{gb.name} ({gb.type})": gb.id for gb in governing_bodies})

        selected_gb = st.selectbox(
            "開催主体で絞り込み",
            options=list(gb_options.keys()),
            key="filter_governing_body",
        )
        governing_body_id = gb_options[selected_gb]

    with col3:
        url_filter_options = {
            "すべて": None,
            "URLあり": True,
            "URLなし": False,
        }
        selected_url_filter = st.selectbox(
            "議員紹介URLで絞り込み",
            options=list(url_filter_options.keys()),
            key="filter_url",
        )
        with_members_url = url_filter_options[selected_url_filter]

    # Load and display conferences
    df, with_url_count, without_url_count = asyncio.run(
        presenter.load_conferences(governing_body_id, with_members_url)
    )

    # 都道府県フィルターを適用
    if selected_prefecture != "すべて" and not df.empty:
        df = cast(pd.DataFrame, df[df["都道府県"] == selected_prefecture])

    # Display statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総会議体数", len(df))
    with col2:
        st.metric("URL登録済み", with_url_count)
    with col3:
        st.metric("URL未登録", without_url_count)

    # Display table with selection checkbox
    if not df.empty:
        _render_conference_table(df)
    else:
        st.info("会議体が登録されていません。")


def _render_conference_table(df: pd.DataFrame) -> None:
    """Render conference table with selection and extraction.

    Args:
        df: 会議体DataFrame
    """
    # Add a selection column for extraction
    df_with_selection = df.copy()
    df_with_selection.insert(0, "抽出", False)

    # Use data_editor to allow selection
    edited_df = st.data_editor(
        df_with_selection,
        use_container_width=True,
        hide_index=True,
        disabled=[col for col in df_with_selection.columns if col != "抽出"],
        column_config={
            "抽出": st.column_config.CheckboxColumn(
                "抽出",
                help="議員情報を抽出する会議体を選択してください",
                default=False,
            )
        },
    )

    # Extract button
    selected_rows = cast(pd.DataFrame, edited_df[edited_df["抽出"]])
    if len(selected_rows) > 0:
        st.info(f"{len(selected_rows)}件の会議体が選択されています")

        if st.button("選択した会議体から議員情報を抽出", type="primary"):
            extract_members_from_conferences(selected_rows)
