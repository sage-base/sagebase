"""Main page for government official management.

政府関係者（官僚）管理のメインページとタブ構成を定義します。
"""

import streamlit as st

from .tabs.batch_link_tab import render_batch_link_tab
from .tabs.list_tab import render_list_tab
from .tabs.new_tab import render_new_tab

from src.interfaces.web.streamlit.presenters.government_official_presenter import (
    GovernmentOfficialPresenter,
)


def render_government_officials_page() -> None:
    """政府関係者管理のメインページをレンダリングする."""
    st.header("官僚管理")
    st.markdown("政府関係者（官僚）の情報を管理します")

    presenter = GovernmentOfficialPresenter()

    tabs = st.tabs(["一覧", "新規登録", "一括紐付け"])

    with tabs[0]:
        render_list_tab(presenter)

    with tabs[1]:
        render_new_tab(presenter)

    with tabs[2]:
        render_batch_link_tab(presenter)
