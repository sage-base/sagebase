"""List tab for parliamentary groups.

議員団一覧タブのUI実装を提供します。
"""

from typing import Any

import streamlit as st

from src.interfaces.web.streamlit.presenters.parliamentary_group_presenter import (
    ParliamentaryGroupPresenter,
)


def render_parliamentary_groups_list_tab(
    presenter: ParliamentaryGroupPresenter,
) -> None:
    """Render the parliamentary groups list tab.

    議員団一覧タブをレンダリングします。
    開催主体でのフィルタリング、SEEDファイル生成、メンバー数表示などの機能を提供します。

    Args:
        presenter: 議員団プレゼンター
    """
    st.subheader("議員団一覧")

    # Get governing bodies for filter
    governing_bodies = presenter.get_all_governing_bodies()

    # Governing body filter
    def get_gb_display_name(gb: Any) -> str:
        return gb.name

    gb_options = ["すべて"] + [get_gb_display_name(gb) for gb in governing_bodies]
    gb_map = {get_gb_display_name(gb): gb.id for gb in governing_bodies}

    selected_gb_filter = st.selectbox("開催主体でフィルタ", gb_options, key="gb_filter")

    # Load parliamentary groups
    if selected_gb_filter == "すべて":
        groups = presenter.load_data()
    else:
        gb_id = gb_map[selected_gb_filter]
        groups = presenter.load_parliamentary_groups_with_filters(gb_id, False)

    if groups:
        # Seed file generation section
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("### SEEDファイル生成")
                st.markdown(
                    "現在登録されている議員団データからSEEDファイルを生成します"
                )
            with col2:
                if st.button(
                    "SEEDファイル生成", key="generate_pg_seed", type="primary"
                ):
                    with st.spinner("SEEDファイルを生成中..."):
                        success, seed_content, file_path_or_error = (
                            presenter.generate_seed_file()
                        )
                        if success:
                            st.success(
                                f"✅ SEEDファイルを生成しました: {file_path_or_error}"
                            )
                            with st.expander("生成されたSEEDファイル", expanded=False):
                                st.code(seed_content, language="sql")
                        else:
                            st.error(
                                f"❌ SEEDファイル生成中にエラーが発生しました: "
                                f"{file_path_or_error}"
                            )

        st.markdown("---")

        # Display data in DataFrame
        df = presenter.to_dataframe(groups, governing_bodies)
        if df is not None:
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Display member counts
        st.markdown("### メンバー数")
        member_df = presenter.get_member_counts(groups)
        if member_df is not None:
            st.dataframe(member_df, use_container_width=True, hide_index=True)
    else:
        st.info("議員団が登録されていません")
