"""Edit and delete tab for parliamentary groups.

議員団の編集・削除タブのUI実装を提供します。
"""

from typing import Any

import pandas as pd
import streamlit as st

from src.interfaces.web.streamlit.presenters.parliamentary_group_presenter import (
    ParliamentaryGroupPresenter,
)


def render_edit_delete_tab(presenter: ParliamentaryGroupPresenter) -> None:
    """Render the edit/delete tab.

    議員団の編集・削除タブをレンダリングします。
    議員団の選択、情報の編集、削除処理を行います。

    Args:
        presenter: 議員団プレゼンター
    """
    st.subheader("議員団の編集・削除")

    # Load all parliamentary groups
    groups = presenter.load_data()
    if not groups:
        st.info("編集する議員団がありません")
        return

    # Get governing bodies for display
    governing_bodies = presenter.get_all_governing_bodies()

    # Select parliamentary group to edit
    group_options: list[str] = []
    group_map: dict[str, Any] = {}
    for group in groups:
        gb = next(
            (g for g in governing_bodies if g.id == group.governing_body_id), None
        )
        gb_name = gb.name if gb else "不明"
        display_name = f"{group.name} ({gb_name})"
        group_options.append(display_name)
        group_map[display_name] = group

    selected_group_display = st.selectbox("編集する議員団を選択", group_options)
    selected_group = group_map[selected_group_display]

    # Get political parties
    political_parties = presenter.get_all_political_parties()
    party_options = ["なし"] + [p.name for p in political_parties]
    party_map: dict[str, int | None] = {"なし": None}
    for p in political_parties:
        party_map[p.name] = p.id

    # 中間テーブルから主要政党IDを取得
    current_primary_party_id = presenter.get_primary_party_id(selected_group.id)
    current_party_index = 0
    if current_primary_party_id:
        for i, p in enumerate(political_parties):
            if p.id == current_primary_party_id:
                current_party_index = i + 1
                break

    # Edit and delete forms
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 編集")
        with st.form("edit_parliamentary_group_form"):
            new_name = st.text_input("議員団名", value=selected_group.name)
            new_party = st.selectbox(
                "政党（任意）", party_options, index=current_party_index
            )
            new_url = st.text_input("議員団URL", value=selected_group.url or "")
            new_description = st.text_area(
                "説明", value=selected_group.description or ""
            )
            new_is_active = st.checkbox("活動中", value=selected_group.is_active)

            submitted = st.form_submit_button("更新")

            if submitted:
                if not new_name:
                    st.error("議員団名を入力してください")
                else:
                    new_political_party_id = party_map.get(new_party)
                    success, error = presenter.update(
                        selected_group.id,
                        new_name,
                        new_url if new_url else None,
                        new_description if new_description else None,
                        new_is_active,
                        political_party_id=new_political_party_id,
                        chamber=selected_group.chamber,
                    )
                    if success:
                        st.success("議員団を更新しました")
                        st.rerun()
                    else:
                        st.error(f"更新に失敗しました: {error}")

    with col2:
        st.markdown("#### メンバー情報")
        # Presenterのメソッドを通じてメンバーシップを取得
        memberships = presenter.get_memberships_by_group(selected_group.id)

        if memberships:
            # アクティブメンバー数をカウント
            active_count = sum(1 for m in memberships if m["is_active"])
            st.write(f"現在のメンバー数: {active_count}名")

            # 表示用にデータを整形
            display_data = []
            for m in memberships:
                start_date_str = (
                    m["start_date"].strftime("%Y-%m-%d") if m["start_date"] else "-"
                )
                end_date_str = (
                    m["end_date"].strftime("%Y-%m-%d") if m["end_date"] else "現在"
                )
                display_data.append(
                    {
                        "政治家": m["politician_name"],
                        "役職": m["role"] or "-",
                        "開始日": start_date_str,
                        "終了日": end_date_str,
                    }
                )

            # DataFrameで表示
            if display_data:
                df = pd.DataFrame(display_data)
                st.dataframe(df, use_container_width=True, hide_index=True, height=200)
        else:
            st.info("メンバーが登録されていません")

        st.markdown("#### 削除")
        st.warning("⚠️ 議員団を削除すると、所属履歴も削除されます")

        # Can only delete inactive groups
        if selected_group.is_active:
            st.info("活動中の議員団は削除できません。先に非活動にしてください。")
        else:
            if st.button("🗑️ この議員団を削除", type="secondary"):
                success, error = presenter.delete(selected_group.id)
                if success:
                    st.success(f"議員団「{selected_group.name}」を削除しました")
                    st.rerun()
                else:
                    st.error(f"削除に失敗しました: {error}")
