"""Speakers list tab for conversations.

発言者一覧タブのUI実装を提供します。
"""

import streamlit as st


def render_speakers_list_tab() -> None:
    """Render the speakers list tab.

    発言者一覧タブをレンダリングします。
    発言者リストの表示、政治家とのマッチング状況などの機能を提供予定です。
    """
    st.subheader("発言者一覧")

    # Placeholder for speaker list
    st.info("発言者リストの表示機能は実装中です")

    # Sample data display
    st.markdown("""
    ### 機能概要
    - 発言者の一覧表示
    - 政治家とのマッチング状況
    - 発言回数の統計
    """)
