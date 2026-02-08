"""List tab for conferences.

会議体一覧タブのUI実装を提供します。
"""

import asyncio

import streamlit as st

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
    都道府県、開催主体でのフィルタリングなどの機能を提供します。

    Args:
        presenter: 会議体プレゼンター
        governing_body_repo: 開催主体リポジトリ
    """
    st.header("会議体一覧")

    # Filters
    col1, col2 = st.columns(2)

    with col1:
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

    with col2:
        pass

    # Load and display conferences
    df = asyncio.run(presenter.load_conferences(governing_body_id))

    # Display statistics
    st.metric("総会議体数", len(df))

    # Display table
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("会議体が登録されていません。")
