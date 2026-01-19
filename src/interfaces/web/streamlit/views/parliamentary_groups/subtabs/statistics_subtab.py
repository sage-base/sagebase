"""Statistics subtab for parliamentary group members.

議員団メンバーの統計サブタブのUI実装を提供します。
"""

import streamlit as st

from src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter import (  # noqa: E501
    ParliamentaryGroupMemberPresenter,
)


def render_member_statistics_subtab(
    presenter: ParliamentaryGroupMemberPresenter,
) -> None:
    """Render the member statistics sub-tab.

    議員団メンバーの統計サブタブをレンダリングします。
    全体統計と議員団別統計を表示します。

    Args:
        presenter: 議員団メンバープレゼンター
    """
    st.markdown("### 統計情報")

    # Overall statistics
    stats = presenter.get_statistics()

    st.markdown("#### 全体統計")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("総レコード数", f"{stats['total']}件")
    with col2:
        st.metric("紐付け未実行", f"{stats['pending']}件")
    with col3:
        st.metric("マッチ済み", f"{stats['matched']}件")
    with col4:
        st.metric("マッチなし", f"{stats['no_match']}件")

    # Parliamentary group statistics
    parliamentary_groups = presenter.get_all_parliamentary_groups()

    if parliamentary_groups:
        st.markdown("#### 議員団別統計")
        for group in parliamentary_groups:
            if group.id:
                group_stats = presenter.get_statistics(group.id)
                if group_stats["total"] > 0:
                    with st.expander(f"{group.name} (総数: {group_stats['total']}件)"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(
                                "紐付け未実行", f"{group_stats.get('pending', 0)}件"
                            )
                            st.metric(
                                "マッチ済み", f"{group_stats.get('matched', 0)}件"
                            )
                        with col2:
                            st.metric(
                                "マッチなし", f"{group_stats.get('no_match', 0)}件"
                            )
