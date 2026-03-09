"""Government official new registration tab.

政府関係者の新規登録フォームを提供します。
"""

from datetime import date

import streamlit as st

from src.interfaces.web.streamlit.presenters.government_official_presenter import (
    GovernmentOfficialPresenter,
)


def render_new_tab(presenter: GovernmentOfficialPresenter) -> None:
    """新規登録タブをレンダリングする."""
    st.subheader("政府関係者の新規登録")

    with st.form(key="new_government_official"):
        name = st.text_input("名前（必須）")
        name_yomi = st.text_input("読み仮名")

        st.markdown("#### 初期役職情報（任意）")
        org = st.text_input("組織名", key="new_org")
        pos = st.text_input("役職名", key="new_pos")
        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input("開始日", value=None, key="new_start")
        with col_end:
            end_date = st.date_input("終了日", value=None, key="new_end")
        source_note = st.text_input("備考", key="new_note")

        submitted = st.form_submit_button("登録", type="primary")

    if submitted:
        if not name:
            st.error("名前は必須です")
            return

        success, created, error = presenter.create(
            name=name.strip(),
            name_yomi=name_yomi.strip() or None,
        )

        if success and created:
            st.success(
                f"政府関係者「{created.name}」を登録しました（ID: {created.id}）"
            )

            # 役職情報がある場合は追加
            if org and pos and created.id is not None:
                start_val: date | None = start_date if start_date else None
                end_val: date | None = end_date if end_date else None
                pos_success, pos_error = presenter.add_position(
                    official_id=created.id,
                    organization=org.strip(),
                    position=pos.strip(),
                    start_date=start_val,
                    end_date=end_val,
                    source_note=source_note.strip() or None,
                )
                if pos_success:
                    st.success("役職情報も登録しました")
                else:
                    st.warning(f"役職の追加に失敗: {pos_error}")
        else:
            st.error(f"登録に失敗: {error}")
