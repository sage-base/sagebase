"""New parliamentary group registration tab.

議員団新規登録タブのUI実装を提供します。
"""

from typing import Any

import streamlit as st

from src.interfaces.web.streamlit.presenters.parliamentary_group_presenter import (
    ParliamentaryGroupPresenter,
)


def render_new_parliamentary_group_tab(presenter: ParliamentaryGroupPresenter) -> None:
    """Render the new parliamentary group registration tab.

    議員団の新規登録タブをレンダリングします。
    開催主体の選択、議員団情報の入力、登録処理を行います。

    Args:
        presenter: 議員団プレゼンター
    """
    st.subheader("議員団の新規登録")

    # Get governing bodies
    governing_bodies = presenter.get_all_governing_bodies()
    if not governing_bodies:
        st.error("開催主体が登録されていません。先に開催主体を登録してください。")
        return

    def get_gb_display_name(gb: Any) -> str:
        return gb.name

    gb_options = [get_gb_display_name(gb) for gb in governing_bodies]
    gb_map = {get_gb_display_name(gb): gb.id for gb in governing_bodies}

    with st.form("new_parliamentary_group_form", clear_on_submit=False):
        selected_gb = st.selectbox("所属開催主体", gb_options)

        # Input fields
        group_name = st.text_input("議員団名", placeholder="例: 自民党市議団")
        group_url = st.text_input(
            "議員団URL（任意）",
            placeholder="https://example.com/parliamentary-group",
            help="議員団の公式ページやプロフィールページのURL",
        )
        group_description = st.text_area(
            "説明（任意）", placeholder="議員団の説明や特徴を入力"
        )
        is_active = st.checkbox("活動中", value=True)

        submitted = st.form_submit_button("登録")

    if submitted:
        gb_id = gb_map[selected_gb]
        if not group_name:
            st.error("議員団名を入力してください")
        elif gb_id is None:
            st.error("開催主体を選択してください")
        else:
            success, group, error = presenter.create(
                group_name,
                gb_id,
                group_url if group_url else None,
                group_description if group_description else None,
                is_active,
            )
            if success and group:
                presenter.add_created_group(group, selected_gb)
                st.success(f"議員団「{group.name}」を登録しました（ID: {group.id}）")
            else:
                st.error(f"登録に失敗しました: {error}")

    # Display created groups
    created_groups = presenter.get_created_groups()
    if created_groups:
        st.divider()
        st.subheader("作成済み議員団")

        for i, group in enumerate(created_groups):
            with st.expander(f"✅ {group['name']} (ID: {group['id']})", expanded=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**議員団名**: {group['name']}")
                    st.write(f"**議員団ID**: {group['id']}")
                    st.write(f"**所属開催主体**: {group['governing_body_name']}")
                    if group["url"]:
                        st.write(f"**URL**: {group['url']}")
                    if group["description"]:
                        st.write(f"**説明**: {group['description']}")
                    active_status = "活動中" if group["is_active"] else "非活動"
                    st.write(f"**活動状態**: {active_status}")
                    if group["created_at"]:
                        st.write(f"**作成日時**: {group['created_at']}")
                with col2:
                    if st.button("削除", key=f"remove_created_{i}"):
                        presenter.remove_created_group(i)
                        st.rerun()
