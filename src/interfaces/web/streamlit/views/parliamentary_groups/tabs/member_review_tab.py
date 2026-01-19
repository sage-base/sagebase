"""Member review tab for parliamentary groups.

議員団メンバーレビュータブのUI実装を提供します。
"""

import streamlit as st

from ..subtabs.create_memberships_subtab import render_create_memberships_subtab
from ..subtabs.duplicate_management_subtab import render_duplicate_management_subtab
from ..subtabs.review_subtab import render_member_review_subtab
from ..subtabs.statistics_subtab import render_member_statistics_subtab

from src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter import (  # noqa: E501
    ParliamentaryGroupMemberPresenter,
)


def render_member_review_tab() -> None:
    """Render the member review tab.

    議員団メンバーレビュータブをレンダリングします。
    4つのサブタブ（レビュー、統計、メンバーシップ作成、重複管理）を提供します。
    """
    st.subheader("議員団メンバーレビュー")
    st.markdown("抽出された議員団メンバーをレビューして、メンバーシップを作成します")

    presenter = ParliamentaryGroupMemberPresenter()

    # Sub-tabs
    sub_tabs = st.tabs(["レビュー", "統計", "メンバーシップ作成", "重複管理"])

    with sub_tabs[0]:
        render_member_review_subtab(presenter)

    with sub_tabs[1]:
        render_member_statistics_subtab(presenter)

    with sub_tabs[2]:
        render_create_memberships_subtab(presenter)

    with sub_tabs[3]:
        render_duplicate_management_subtab(presenter)
