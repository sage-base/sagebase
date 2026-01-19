"""Statistics tab for conversations.

発言の統計タブのUI実装を提供します。
"""

import streamlit as st


def render_statistics_tab() -> None:
    """Render the statistics tab.

    発言の統計タブをレンダリングします。
    発言者数、マッチング状況などの統計情報を表示します。
    """
    st.subheader("統計情報")

    # Statistics placeholders
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("総発言者数", "0名")

    with col2:
        st.metric("マッチング済み", "0名")

    with col3:
        st.metric("マッチング率", "0%")

    st.markdown("""
    ### 詳細統計
    - 会議別発言者数
    - 政党別発言数
    - 時系列発言推移
    """)
