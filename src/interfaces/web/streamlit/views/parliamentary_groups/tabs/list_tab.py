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
    会議体でのフィルタリング、SEEDファイル生成、メンバー数表示などの機能を提供します。

    Args:
        presenter: 議員団プレゼンター
    """
    st.subheader("議員団一覧")

    # Get conferences for filter
    conferences = presenter.get_all_conferences()

    # Conference filter
    def get_conf_display_name(c: Any) -> str:
        gb_name = (
            c.governing_body.name
            if hasattr(c, "governing_body") and c.governing_body
            else ""
        )
        return f"{gb_name} - {c.name}"

    conf_options = ["すべて"] + [get_conf_display_name(c) for c in conferences]
    conf_map = {get_conf_display_name(c): c.id for c in conferences}

    selected_conf_filter = st.selectbox(
        "会議体でフィルタ", conf_options, key="conf_filter"
    )

    # Load parliamentary groups
    if selected_conf_filter == "すべて":
        groups = presenter.load_data()
    else:
        conf_id = conf_map[selected_conf_filter]
        groups = presenter.load_parliamentary_groups_with_filters(conf_id, False)

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
        df = presenter.to_dataframe(groups, conferences)
        if df is not None:
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Display member counts
        st.markdown("### メンバー数")
        member_df = presenter.get_member_counts(groups)
        if member_df is not None:
            st.dataframe(member_df, use_container_width=True, hide_index=True)
    else:
        st.info("議員団が登録されていません")
