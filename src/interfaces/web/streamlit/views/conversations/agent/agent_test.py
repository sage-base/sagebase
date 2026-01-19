"""Agent test module for politician matching.

PoliticianMatchingAgentのテスト機能を提供します。
"""

import asyncio

from typing import Any

import streamlit as st

from src.infrastructure.di.container import Container


def render_politician_matching_agent_test() -> None:
    """Test PoliticianMatchingAgent.

    PoliticianMatchingAgentのテスト画面をレンダリングします。
    ReActパターンで動作し、3つのツールを使って反復的にマッチングを行います。
    """
    st.markdown("### PoliticianMatchingAgent の実行")

    st.info(
        "このエージェントはReActパターンで動作し、"
        "3つのツールを使って反復的にマッチングを行います。"
    )

    speaker_name = st.text_input(
        "発言者名",
        value="田中太郎",
        help="マッチング対象の発言者名",
        key="pol_agent_speaker",
    )

    col1, col2 = st.columns(2)
    with col1:
        speaker_type = st.text_input(
            "発言者種別（オプション）",
            value="",
            help="例: 議員、委員",
            key="pol_agent_type",
        )
    with col2:
        speaker_party = st.text_input(
            "発言者政党（オプション）",
            value="",
            help="所属政党",
            key="pol_agent_party",
        )

    with st.expander("詳細設定"):
        st.info(
            "エージェントの設定（現在は固定値）\n\n"
            "- MAX_REACT_STEPS: 10\n"
            "- 信頼度閾値: 0.7"
        )

    if st.button("政治家マッチングAgentを実行", type="primary", key="pol_agent_btn"):
        if not speaker_name:
            st.warning("発言者名を入力してください")
            return

        _execute_agent(speaker_name, speaker_type, speaker_party)

    _display_usage_guide()


def _execute_agent(
    speaker_name: str,
    speaker_type: str,
    speaker_party: str,
) -> None:
    """Execute the politician matching agent.

    Args:
        speaker_name: 発言者名
        speaker_type: 発言者種別
        speaker_party: 発言者政党
    """
    with st.spinner("エージェントを実行中..."):
        try:
            # DIコンテナからエージェントを取得（Clean Architecture準拠）
            container = Container.create_for_environment()
            agent = container.use_cases.politician_matching_agent()

            result = asyncio.run(
                agent.match_politician(
                    speaker_name=speaker_name,
                    speaker_type=speaker_type or None,
                    speaker_party=speaker_party or None,
                )
            )

            _display_agent_results(result)

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            import traceback

            with st.expander("エラー詳細"):
                st.code(traceback.format_exc())


def _display_agent_results(result: dict[str, Any]) -> None:
    """Display agent execution results.

    Args:
        result: エージェント実行結果
    """
    st.markdown("### マッチング結果")

    if result.get("error_message"):
        st.error(f"エラー: {result['error_message']}")
    elif result["matched"]:
        st.success("✅ マッチング成功！")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "政治家名",
                result.get("politician_name", "Unknown"),
            )
        with col2:
            st.metric(
                "政党",
                result.get("political_party_name", "N/A"),
            )
        with col3:
            st.metric(
                "信頼度",
                f"{result.get('confidence', 0):.2f}",
            )

        st.markdown("### 判定理由")
        st.info(result.get("reason", ""))

        with st.expander("詳細結果（JSON）"):
            st.json(dict(result))
    else:
        st.warning("マッチする政治家が見つかりませんでした")
        st.info(result.get("reason", ""))

        with st.expander("詳細結果（JSON）"):
            st.json(dict(result))


def _display_usage_guide() -> None:
    """Display usage guide."""
    st.markdown("---")
    st.markdown("""
    ### 使い方

    1. **発言者名** を入力（例: 田中太郎）
    2. 必要に応じて **発言者種別** と **発言者政党** を入力
    3. **「政治家マッチングAgentを実行」** ボタンをクリック

    **動作の流れ:**
    1. エージェントが候補検索ツールで政治家候補を取得
    2. 上位候補の所属情報を検証
    3. BAMLを使用して最終的なマッチング判定
    4. 信頼度0.7以上ならマッチング成功

    **注意:**
    - エージェントの実行には数秒〜十数秒かかることがあります
    - LLM API（Gemini）を使用するため、API キーが必要です
    """)
