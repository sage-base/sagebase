"""New parliamentary group registration tab.

議員団新規登録タブのUI実装を提供します。
"""

from datetime import date
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

    # Get political parties
    political_parties = presenter.get_all_political_parties()
    party_options = ["なし"] + [p.name for p in political_parties]
    party_map: dict[str, int | None] = {"なし": None}
    for p in political_parties:
        party_map[p.name] = p.id

    # 開催主体が「国会」かどうかを判定するためのマップ
    gb_type_map = {get_gb_display_name(gb): gb.type for gb in governing_bodies}

    # 開催主体と院の選択はフォーム外（値変更で即リランさせるため）
    selected_gb = st.selectbox("所属開催主体", gb_options)

    # 国会の場合は院の選択肢を表示
    chamber = ""
    if selected_gb and gb_type_map.get(selected_gb) == "国":
        chamber = st.selectbox("院", ["衆議院", "参議院"])

    with st.form("new_parliamentary_group_form", clear_on_submit=False):
        # Input fields
        group_name = st.text_input("議員団名", placeholder="例: 自民党市議団")
        selected_party = st.selectbox("政党（任意）", party_options)
        group_url = st.text_input(
            "議員団URL（任意）",
            placeholder="https://example.com/parliamentary-group",
            help="議員団の公式ページやプロフィールページのURL",
        )
        group_description = st.text_area(
            "説明（任意）", placeholder="議員団の説明や特徴を入力"
        )
        is_active = st.checkbox("活動中", value=True)

        start_date: date | None = st.date_input(
            "開始日（任意）",
            value=None,
            help="会派の活動開始日",
        )
        end_date: date | None = st.date_input(
            "終了日（任意）",
            value=None,
            help="会派の活動終了日",
        )

        submitted = st.form_submit_button("登録")

    if submitted:
        gb_id = gb_map[selected_gb]
        political_party_id = party_map.get(selected_party)
        if not group_name:
            st.error("議員団名を入力してください")
        elif gb_id is None:
            st.error("開催主体を選択してください")
        elif start_date and end_date and end_date < start_date:
            st.error("終了日は開始日より後に設定してください")
        else:
            success, group, error = presenter.create(
                group_name,
                gb_id,
                group_url if group_url else None,
                group_description if group_description else None,
                is_active,
                political_party_id=political_party_id,
                chamber=chamber,
                start_date=start_date,
                end_date=end_date,
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
                    if group.get("start_date"):
                        st.write(f"**開始日**: {group['start_date']}")
                    if group.get("end_date"):
                        st.write(f"**終了日**: {group['end_date']}")
                    if group["created_at"]:
                        st.write(f"**作成日時**: {group['created_at']}")
                with col2:
                    if st.button("削除", key=f"remove_created_{i}"):
                        presenter.remove_created_group(i)
                        st.rerun()
