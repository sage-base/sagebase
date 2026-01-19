"""Main page for parliamentary group management.

議員団管理のメインページとタブ構成を定義します。
"""

import streamlit as st

from .tabs.edit_delete_tab import render_edit_delete_tab
from .tabs.list_tab import render_parliamentary_groups_list_tab
from .tabs.member_extraction_tab import render_member_extraction_tab
from .tabs.member_review_tab import render_member_review_tab
from .tabs.memberships_list_tab import render_memberships_list_tab
from .tabs.new_tab import render_new_parliamentary_group_tab

from src.interfaces.web.streamlit.presenters.parliamentary_group_presenter import (
    ParliamentaryGroupPresenter,
)


def render_parliamentary_groups_page() -> None:
    """Render the parliamentary groups management page.

    議員団管理のメインページをレンダリングします。
    6つのタブ（議員団一覧、新規登録、編集・削除、メンバー抽出、
    メンバーレビュー、メンバーシップ一覧）を提供します。
    """
    st.header("議員団管理")
    st.markdown("議員団（会派）の情報を管理します")

    presenter = ParliamentaryGroupPresenter()

    # Create tabs
    tabs = st.tabs(
        [
            "議員団一覧",
            "新規登録",
            "編集・削除",
            "メンバー抽出",
            "メンバーレビュー",
            "メンバーシップ一覧",
        ]
    )

    with tabs[0]:
        render_parliamentary_groups_list_tab(presenter)

    with tabs[1]:
        render_new_parliamentary_group_tab(presenter)

    with tabs[2]:
        render_edit_delete_tab(presenter)

    with tabs[3]:
        render_member_extraction_tab(presenter)

    with tabs[4]:
        render_member_review_tab()

    with tabs[5]:
        render_memberships_list_tab(presenter)
