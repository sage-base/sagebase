"""Main page for conversations management.

発言・発言者管理のメインページとタブ構成を定義します。
"""

import streamlit as st

from .agent.agent_tab import render_politician_matching_agent_tab
from .tabs.list_tab import render_conversations_list_tab
from .tabs.matching_tab import render_matching_tab
from .tabs.search_filter_tab import render_search_filter_tab
from .tabs.speakers_list_tab import render_speakers_list_tab
from .tabs.statistics_tab import render_statistics_tab


def render_conversations_page() -> None:
    """Render the conversations and speakers management page.

    発言・発言者管理のメインページをレンダリングします。
    6つのタブ（発言一覧、検索・フィルタ、発言者一覧、発言マッチング、
    統計情報、政治家マッチングAgent）を提供します。
    """
    st.header("発言・発言者管理")
    st.markdown("発言記録と発言者の情報を管理します")

    # Create tabs
    tabs = st.tabs(
        [
            "発言一覧",
            "検索・フィルタ",
            "発言者一覧",
            "発言マッチング",
            "統計情報",
            "政治家マッチングAgent",
        ]
    )

    with tabs[0]:
        render_conversations_list_tab()

    with tabs[1]:
        render_search_filter_tab()

    with tabs[2]:
        render_speakers_list_tab()

    with tabs[3]:
        render_matching_tab()

    with tabs[4]:
        render_statistics_tab()

    with tabs[5]:
        render_politician_matching_agent_tab()
