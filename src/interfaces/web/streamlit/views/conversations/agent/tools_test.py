"""Tools test module for politician matching.

政治家マッチング用ツールの個別テスト機能を提供します。
"""

import streamlit as st

from .affiliation_test import render_politician_affiliation_test
from .baml_match_test import render_politician_baml_match_test
from .search_test import render_politician_search_test


def render_politician_matching_tools_test() -> None:
    """Test politician matching tools individually.

    政治家マッチング用ツールの個別テスト画面をレンダリングします。
    候補検索、所属検証、BAMLマッチングの3つのタブを提供します。
    """
    st.markdown("### 政治家マッチング用ツールの個別テスト")

    tool_tabs = st.tabs(["候補検索", "所属検証", "BAMLマッチング"])

    with tool_tabs[0]:
        render_politician_search_test()

    with tool_tabs[1]:
        render_politician_affiliation_test()

    with tool_tabs[2]:
        render_politician_baml_match_test()
