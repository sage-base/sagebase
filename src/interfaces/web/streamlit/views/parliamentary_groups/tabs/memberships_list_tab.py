"""Memberships list tab for parliamentary groups.

議員団メンバーシップ一覧タブのUI実装を提供します。
"""

from typing import Any

import pandas as pd
import streamlit as st

from src.interfaces.web.streamlit.presenters.parliamentary_group_presenter import (
    ParliamentaryGroupPresenter,
)


def render_memberships_list_tab(presenter: ParliamentaryGroupPresenter) -> None:
    """Render the memberships list tab.

    議員団メンバーシップ一覧タブをレンダリングします。
    開催主体・議員団でのフィルタリング、メンバーシップの一覧表示などの機能を提供します。

    Args:
        presenter: 議員団プレゼンター
    """
    st.subheader("メンバーシップ一覧")

    # Get all parliamentary groups for filter
    all_groups = presenter.load_data()
    governing_bodies = presenter.get_all_governing_bodies()

    # Create governing body to groups mapping
    gb_to_groups: dict[int, list[Any]] = {}
    for group in all_groups:
        if group.governing_body_id not in gb_to_groups:
            gb_to_groups[group.governing_body_id] = []
        gb_to_groups[group.governing_body_id].append(group)

    # Governing body filter
    def get_gb_display_name(gb: Any) -> str:
        return gb.name

    gb_options = ["すべて"] + [get_gb_display_name(gb) for gb in governing_bodies]
    gb_map = {get_gb_display_name(gb): gb.id for gb in governing_bodies}

    selected_gb = st.selectbox(
        "開催主体でフィルタ", gb_options, key="membership_gb_filter"
    )

    # Parliamentary group filter
    if selected_gb == "すべて":
        group_options = ["すべて"] + [g.name for g in all_groups]
        group_map = {g.name: g.id for g in all_groups}
    else:
        gb_id = gb_map.get(selected_gb)
        if gb_id is not None:
            filtered_groups = gb_to_groups.get(gb_id, [])
            group_options = ["すべて"] + [g.name for g in filtered_groups]
            group_map = {g.name: g.id for g in filtered_groups}
        else:
            group_options = ["すべて"]
            group_map = {}

    selected_group = st.selectbox(
        "議員団でフィルタ", group_options, key="membership_group_filter"
    )

    # Get memberships
    try:
        all_memberships = _get_memberships(
            presenter,
            selected_gb,
            selected_group,
            gb_map,
            gb_to_groups,
            all_groups,
            group_map,
        )

        if all_memberships:
            _display_memberships(all_memberships, all_groups)
        else:
            st.info("メンバーシップが登録されていません")

    except Exception as e:
        st.error(f"メンバーシップの取得中にエラーが発生しました: {e}")


def _get_memberships(
    presenter: ParliamentaryGroupPresenter,
    selected_gb: str,
    selected_group: str,
    gb_map: dict[str, int | None],
    gb_to_groups: dict[int, list[Any]],
    all_groups: list[Any],
    group_map: dict[str, int | None],
) -> list[dict[str, Any]]:
    """Get memberships based on filters.

    Presenterのメソッドを通じてメンバーシップを取得します。

    Args:
        presenter: 議員団プレゼンター
        selected_gb: 選択された開催主体
        selected_group: 選択された議員団
        gb_map: 開催主体名からIDへのマップ
        gb_to_groups: 開催主体IDから議員団リストへのマップ
        all_groups: すべての議員団
        group_map: 議員団名からIDへのマップ

    Returns:
        メンバーシップ情報のリスト（dict形式）
    """
    if selected_group == "すべて":
        # Get all memberships for selected governing body or all
        if selected_gb == "すべて":
            groups_to_query = all_groups
        else:
            gb_id = gb_map.get(selected_gb)
            if gb_id is not None:
                groups_to_query = gb_to_groups.get(gb_id, [])
            else:
                groups_to_query = []

        # Presenterのメソッドを使用して複数グループのメンバーシップを取得
        group_ids = [g.id for g in groups_to_query if g.id]
        return presenter.get_memberships_for_groups(group_ids)
    else:
        # Get memberships for specific group
        group_id = group_map.get(selected_group)
        if group_id is not None:
            return presenter.get_memberships_by_group(group_id)
        else:
            return []


def _display_memberships(
    all_memberships: list[dict[str, Any]],
    all_groups: list[Any],
) -> None:
    """Display memberships in a table.

    Presenterから取得したメンバーシップ情報を表形式で表示します。

    Args:
        all_memberships: メンバーシップ情報のリスト（dict形式）
        all_groups: すべての議員団
    """
    # Prepare data for display
    membership_data = []
    for membership in all_memberships:
        # Get group name
        group = next(
            (g for g in all_groups if g.id == membership["parliamentary_group_id"]),
            None,
        )
        group_name = group.name if group else "不明"

        # Format dates
        start_date_str = (
            membership["start_date"].strftime("%Y-%m-%d")
            if membership["start_date"]
            else "-"
        )
        end_date_str = (
            membership["end_date"].strftime("%Y-%m-%d")
            if membership["end_date"]
            else "現在"
        )

        membership_data.append(
            {
                "ID": membership["id"],
                "議員団": group_name,
                "政治家": membership["politician_name"],
                "役職": membership["role"] or "-",
                "開始日": start_date_str,
                "終了日": end_date_str,
                "状態": "現在" if membership["is_active"] else "過去",
            }
        )

    # Display as DataFrame
    df = pd.DataFrame(membership_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Display summary
    st.markdown("### 統計")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総メンバーシップ数", len(all_memberships))
    with col2:
        active_count = sum(1 for m in all_memberships if m["is_active"])
        st.metric("現在のメンバー数", active_count)
    with col3:
        past_count = sum(1 for m in all_memberships if not m["is_active"])
        st.metric("過去のメンバー数", past_count)
