"""Search tool test module for politician matching.

政治家候補の検索・スコアリングツールのテスト機能を提供します。
"""

import asyncio

from typing import Any

import streamlit as st

from src.infrastructure.di.container import Container
from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
    create_politician_matching_tools,
)


def render_politician_search_test() -> None:
    """Test search_politician_candidates tool.

    政治家候補の検索・スコアリングツールのテスト画面をレンダリングします。
    発言者名から政治家候補をスコア順に表示します。
    """
    st.subheader("政治家候補の検索・スコアリング")

    st.markdown("発言者名を入力すると、政治家候補をスコア順に表示します。")

    speaker_name = st.text_input(
        "発言者名",
        value="田中太郎",
        help="マッチング対象の発言者名",
        key="pol_search_speaker_name",
    )

    speaker_party = st.text_input(
        "所属政党（オプション）",
        value="",
        help="政党が一致するとスコアがブーストされます",
        key="pol_search_party",
    )

    max_candidates = st.slider(
        "最大候補数",
        min_value=5,
        max_value=30,
        value=10,
        key="pol_search_max",
    )

    if st.button("候補を検索", type="primary", key="pol_search_button"):
        if not speaker_name:
            st.warning("発言者名を入力してください")
            return

        _execute_search(speaker_name, speaker_party, max_candidates)


def _execute_search(
    speaker_name: str,
    speaker_party: str,
    max_candidates: int,
) -> None:
    """Execute politician candidate search.

    Args:
        speaker_name: 発言者名
        speaker_party: 所属政党
        max_candidates: 最大候補数
    """
    with st.spinner("候補を検索中..."):
        try:
            container = Container.create_for_environment()
            tools = create_politician_matching_tools(
                politician_repo=container.repositories.politician_repository(),
                affiliation_repo=(
                    container.repositories.politician_affiliation_repository()
                ),
            )
            search_tool = tools[0]

            tool_input = {
                "speaker_name": speaker_name,
                "max_candidates": max_candidates,
            }
            if speaker_party:
                tool_input["speaker_party"] = speaker_party

            result = asyncio.run(search_tool.ainvoke(tool_input))

            if "error" in result:
                st.error(f"エラー: {result['error']}")
            else:
                _display_search_results(result)

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            import traceback

            with st.expander("エラー詳細"):
                st.code(traceback.format_exc())


def _display_search_results(result: dict[str, Any]) -> None:
    """Display search results.

    Args:
        result: 検索結果
    """
    st.success(
        f"✅ {result['total_candidates']}人の候補から"
        f"上位{len(result['candidates'])}人を表示"
    )

    for i, candidate in enumerate(result.get("candidates", []), 1):
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            st.markdown(f"**{i}. {candidate.get('politician_name')}**")
        with col2:
            score = candidate.get("score", 0.0)
            st.metric("スコア", f"{score:.2f}")
        with col3:
            match_type = candidate.get("match_type", "")
            type_label = {
                "exact": "完全一致",
                "partial": "部分一致",
                "fuzzy": "類似",
                "none": "なし",
            }.get(match_type, match_type)
            st.write(type_label)

        party = candidate.get("party_name")
        if party:
            st.caption(f"政党: {party}")
        st.divider()
