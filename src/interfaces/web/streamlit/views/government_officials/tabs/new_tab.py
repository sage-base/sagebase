"""Government official new registration tab.

政府関係者の新規登録フォームを提供します。
"""

import streamlit as st

from src.interfaces.web.streamlit.presenters.government_official_presenter import (
    GovernmentOfficialPresenter,
)


def render_new_tab(presenter: GovernmentOfficialPresenter) -> None:
    """新規登録タブをレンダリングする."""
    st.subheader("政府関係者の新規登録")

    with st.form(key="new_government_official"):
        name = st.text_input("名前（必須）")

        submitted = st.form_submit_button("登録", type="primary")

    if submitted:
        if not name:
            st.error("名前は必須です")
            return

        success, created, error = presenter.create(
            name=name.strip(),
        )

        if success and created:
            st.success(
                f"政府関係者「{created.name}」を登録しました（ID: {created.id}）"
            )
        else:
            st.error(f"登録に失敗: {error}")
