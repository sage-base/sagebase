"""Search and filter tab for conversations.

発言の検索・フィルタタブのUI実装を提供します。
"""

import streamlit as st


def render_search_filter_tab() -> None:
    """Render the search and filter tab.

    発言の検索・フィルタタブをレンダリングします。
    キーワード検索、詳細フィルタなどの機能を提供します。
    """
    st.subheader("検索・フィルタ")

    # Search box
    st.text_input(
        "キーワード検索",
        placeholder="発言内容を検索...",
    )

    # Advanced filters
    st.markdown("### 詳細フィルタ")

    col1, col2 = st.columns(2)

    with col1:
        st.multiselect("政党", ["自民党", "立憲民主党", "公明党"], key="party_filter")
        st.multiselect("会議体", ["本会議", "委員会"], key="conference_filter")

    with col2:
        st.slider("発言文字数", 0, 1000, (0, 500), key="length_filter")
        st.multiselect("タグ", ["重要", "質問", "答弁"], key="tag_filter")

    if st.button("検索実行", type="primary"):
        with st.spinner("検索中..."):
            st.info("検索機能は実装中です")
