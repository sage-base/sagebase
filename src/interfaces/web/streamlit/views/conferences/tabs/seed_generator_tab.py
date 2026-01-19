"""Seed generator tab for conferences.

SEEDファイル生成タブのUI実装を提供します。
"""

import streamlit as st

from src.interfaces.web.streamlit.presenters.conference_presenter import (
    ConferencePresenter,
)


def render_seed_generator(presenter: ConferencePresenter) -> None:
    """Render seed file generator.

    SEEDファイル生成タブをレンダリングします。
    現在データベースに登録されている会議体情報からSEEDファイルを生成します。

    Args:
        presenter: 会議体プレゼンター
    """
    st.header("SEEDファイル生成")

    st.info("現在データベースに登録されている会議体情報からSEEDファイルを生成します。")

    if st.button("SEEDファイル生成", type="primary"):
        success, file_path, error_message = presenter.generate_seed_file()

        if success:
            st.success(f"SEEDファイルを生成しました: {file_path}")

            # Show download button
            with open(file_path) as f:
                seed_content = f.read()

            st.download_button(
                label="SEEDファイルをダウンロード",
                data=seed_content,
                file_name="seed_conferences_generated.sql",
                mime="text/plain",
            )
        else:
            st.error(f"生成に失敗しました: {error_message}")
