"""BAML matching test module for politician matching.

BAMLによる政治家マッチングツールのテスト機能を提供します。
"""

import asyncio

from typing import Any

import streamlit as st

from src.infrastructure.di.container import Container
from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
    create_politician_matching_tools,
)


def render_politician_baml_match_test() -> None:
    """Test match_politician_with_baml tool.

    BAMLによる政治家マッチングツールのテスト画面をレンダリングします。
    候補リストから最適な政治家を選択します。
    """
    st.subheader("BAMLによる政治家マッチング")

    st.markdown("BAMLを使用して、候補から最適な政治家を選択します。")

    speaker_name = st.text_input(
        "発言者名",
        value="田中太郎",
        key="pol_baml_speaker",
    )

    col1, col2 = st.columns(2)
    with col1:
        speaker_type = st.text_input(
            "発言者種別",
            value="議員",
            key="pol_baml_type",
        )
    with col2:
        speaker_party = st.text_input(
            "発言者政党",
            value="〇〇党",
            key="pol_baml_party",
        )

    st.markdown("### 候補政治家（JSON）")
    default_json = (
        '[{"politician_id": 1, "politician_name": "田中太郎", "party_name": "〇〇党"}]'
    )
    candidates_json = st.text_area(
        "候補JSON",
        value=default_json,
        height=100,
        key="pol_baml_candidates",
    )

    if st.button("BAMLマッチング実行", type="primary", key="pol_baml_button"):
        if not speaker_name:
            st.warning("発言者名を入力してください")
            return

        _execute_baml_matching(
            speaker_name, speaker_type, speaker_party, candidates_json
        )


def _execute_baml_matching(
    speaker_name: str,
    speaker_type: str,
    speaker_party: str,
    candidates_json: str,
) -> None:
    """Execute BAML matching.

    Args:
        speaker_name: 発言者名
        speaker_type: 発言者種別
        speaker_party: 発言者政党
        candidates_json: 候補JSON
    """
    with st.spinner("BAMLマッチング中..."):
        try:
            container = Container.create_for_environment()
            tools = create_politician_matching_tools(
                politician_repo=container.repositories.politician_repository(),
                affiliation_repo=(
                    container.repositories.politician_affiliation_repository()
                ),
            )
            match_tool = tools[2]

            result = asyncio.run(
                match_tool.ainvoke(
                    {
                        "speaker_name": speaker_name,
                        "speaker_type": speaker_type,
                        "speaker_party": speaker_party,
                        "candidates_json": candidates_json,
                    }
                )
            )

            if "error" in result:
                st.error(f"エラー: {result['error']}")
            else:
                _display_baml_results(result)

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            import traceback

            with st.expander("エラー詳細"):
                st.code(traceback.format_exc())


def _display_baml_results(result: dict[str, Any]) -> None:
    """Display BAML matching results.

    Args:
        result: マッチング結果
    """
    if result.get("matched"):
        st.success("✅ マッチング成功！")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "マッチした政治家",
                result.get("politician_name"),
            )
        with col2:
            st.metric(
                "信頼度",
                f"{result.get('confidence', 0):.2f}",
            )
        st.info(f"理由: {result.get('reason')}")
    else:
        st.warning("マッチなし")
        st.info(f"理由: {result.get('reason')}")
