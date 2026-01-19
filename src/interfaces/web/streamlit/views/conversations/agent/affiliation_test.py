"""Affiliation verification test module for politician matching.

政治家所属情報の検証ツールのテスト機能を提供します。
"""

import asyncio

from typing import Any

import streamlit as st

from src.infrastructure.di.container import Container
from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
    create_politician_matching_tools,
)


def render_politician_affiliation_test() -> None:
    """Test verify_politician_affiliation tool.

    政治家所属情報の検証ツールのテスト画面をレンダリングします。
    政治家IDから所属情報を取得し、期待される政党との一致を確認します。
    """
    st.subheader("政治家所属情報の検証")

    st.markdown("政治家IDを指定して、所属情報を検証します。")

    politician_id = st.number_input(
        "政治家ID",
        value=1,
        min_value=1,
        key="pol_aff_id",
    )

    expected_party = st.text_input(
        "期待される政党（オプション）",
        value="",
        help="指定すると、政党の一致を確認します",
        key="pol_aff_party",
    )

    if st.button("所属を検証", type="primary", key="pol_aff_button"):
        _execute_verification(int(politician_id), expected_party)


def _execute_verification(politician_id: int, expected_party: str) -> None:
    """Execute affiliation verification.

    Args:
        politician_id: 政治家ID
        expected_party: 期待される政党
    """
    with st.spinner("所属情報を検証中..."):
        try:
            container = Container.create_for_environment()
            tools = create_politician_matching_tools(
                politician_repo=container.repositories.politician_repository(),
                affiliation_repo=(
                    container.repositories.politician_affiliation_repository()
                ),
            )
            verify_tool = tools[1]

            tool_input: dict[str, int | str] = {"politician_id": politician_id}
            if expected_party:
                tool_input["expected_party"] = expected_party

            result = asyncio.run(verify_tool.ainvoke(tool_input))

            if "error" in result:
                st.error(f"エラー: {result['error']}")
            else:
                _display_verification_results(result, expected_party)

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            import traceback

            with st.expander("エラー詳細"):
                st.code(traceback.format_exc())


def _display_verification_results(result: dict[str, Any], expected_party: str) -> None:
    """Display verification results.

    Args:
        result: 検証結果
        expected_party: 期待される政党
    """
    st.success(f"✅ {result['politician_name']} の情報を取得しました")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("政治家名", result.get("politician_name", "N/A"))
    with col2:
        st.metric("所属政党", result.get("current_party", "N/A"))

    if expected_party:
        party_matches = result.get("party_matches")
        if party_matches:
            st.success("✅ 政党が一致しています")
        else:
            st.warning("政党が一致しません")

    affiliations = result.get("affiliations", [])
    if affiliations:
        st.markdown("### 所属会議体")
        for aff in affiliations:
            st.write(
                f"- 会議体ID: {aff.get('conference_id')}, "
                f"開始: {aff.get('start_date')}, "
                f"終了: {aff.get('end_date', '現在')}"
            )
