"""Government officials batch link tab.

未紐付きSpeakerとGovernmentOfficialの一括自動紐付け機能を提供します。
"""

import pandas as pd
import streamlit as st

from src.interfaces.web.streamlit.presenters.government_official_presenter import (
    GovernmentOfficialPresenter,
)


def render_batch_link_tab(presenter: GovernmentOfficialPresenter) -> None:
    """一括紐付けタブをレンダリングする."""
    st.subheader("一括自動紐付け")
    st.markdown(
        "未紐付きSpeaker（非政治家・官僚未紐付け）と政府関係者を"
        "名前の正規化（旧字体変換・スペース除去等）による完全一致で自動紐付けします。"
    )

    # プレビューボタン
    if st.button("プレビュー（dry run）", type="primary"):
        with st.spinner("マッチング候補を検索中..."):
            result = presenter.batch_link_speakers(dry_run=True)

        st.session_state["batch_link_preview"] = result

    # プレビュー結果表示
    if "batch_link_preview" in st.session_state:
        result = st.session_state["batch_link_preview"]

        col1, col2 = st.columns(2)
        with col1:
            st.metric("紐付け候補", f"{result.linked_count}件")
        with col2:
            st.metric("スキップ（マッチなし）", f"{result.skipped_count}件")

        if result.details:
            data = []
            for d in result.details:
                data.append(
                    {
                        "Speaker ID": d.speaker_id,
                        "Speaker名": d.speaker_name,
                        "官僚ID": d.government_official_id,
                        "官僚名": d.government_official_name,
                        "正規化名": d.normalized_name,
                    }
                )
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # 実行ボタン
            if st.button("紐付けを実行", type="primary"):
                with st.spinner("紐付けを実行中..."):
                    exec_result = presenter.batch_link_speakers(dry_run=False)

                st.success(f"{exec_result.linked_count}件の紐付けを実行しました")
                # プレビュー結果をクリア
                del st.session_state["batch_link_preview"]
                st.rerun()
        else:
            st.info("紐付け可能な候補が見つかりませんでした")
