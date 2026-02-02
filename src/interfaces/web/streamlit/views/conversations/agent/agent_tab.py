"""Agent tab for politician matching.

政治家マッチングAgentタブのUI実装を提供します。
"""

import streamlit as st

from .agent_test import render_politician_matching_agent_test
from .tools_test import render_politician_matching_tools_test


def render_politician_matching_agent_tab() -> None:
    """Test PoliticianMatchingAgent (Issue #904).

    政治家マッチングAgentのテストタブをレンダリングします。
    ツール個別テストとAgentテストの2つのサブタブを提供します。
    """
    st.subheader("政治家マッチングAgentテスト")

    st.markdown("""
    ### PoliticianMatchingAgent の動作確認 (Issue #904)

    LangGraphのReActエージェントを使用した政治家マッチングをテストします。
    BAMLをLLM通信層として使用し、反復的推論で高精度なマッチングを実現します。

    **使用するツール:**
    1. `search_politician_candidates`: 候補検索・スコアリング
    2. `verify_conference_membership`: 所属情報検証
    3. `match_politician_with_baml`: BAMLマッチング実行
    """)

    # Create sub-tabs for tools and agent test
    sub_tabs = st.tabs(["ツール個別テスト", "Agentテスト"])

    with sub_tabs[0]:
        render_politician_matching_tools_test()

    with sub_tabs[1]:
        render_politician_matching_agent_test()
