"""New conference registration tab.

会議体新規登録タブのUI実装を提供します。
"""

import asyncio

import streamlit as st

from ..constants import CONFERENCE_PREFECTURES

from src.domain.repositories import GoverningBodyRepository
from src.interfaces.web.streamlit.presenters.conference_presenter import (
    ConferenceFormData,
    ConferencePresenter,
)


def render_new_conference_form(
    presenter: ConferencePresenter,
    governing_body_repo: GoverningBodyRepository,
) -> None:
    """Render new conference registration form.

    会議体の新規登録フォームをレンダリングします。
    会議体名、開催主体、都道府県、種別、議員紹介URLの入力フォームを提供します。

    Args:
        presenter: 会議体プレゼンター
        governing_body_repo: 開催主体リポジトリ
    """
    st.header("新規会議体登録")

    # Get form data
    form_data = presenter.get_form_data("new")

    # Load governing bodies for dropdown
    governing_bodies = governing_body_repo.get_all()
    gb_options = {f"{gb.name} ({gb.type})": gb.id for gb in governing_bodies}

    with st.form("conference_create_form"):
        # Conference name
        name = st.text_input(
            "会議体名 *",
            value=form_data.name,
            placeholder="例: 議会",
        )

        # Governing body selection
        selected_gb = st.selectbox(
            "開催主体 *",
            options=list(gb_options.keys()),
            index=0 if not form_data.governing_body_id else None,
        )
        governing_body_id = gb_options[selected_gb] if selected_gb else None

        # Prefecture selection
        prefecture_options = [p for p in CONFERENCE_PREFECTURES if p]  # 空文字を除く
        current_prefecture = form_data.prefecture or prefecture_options[0]
        prefecture_index = (
            prefecture_options.index(current_prefecture)
            if current_prefecture in prefecture_options
            else 0
        )
        prefecture = st.selectbox(
            "都道府県",
            options=prefecture_options,
            index=prefecture_index,
            help="国会の場合は「全国」を選択してください",
        )

        # Type
        conf_type = st.text_input(
            "種別",
            value=form_data.type or "",
            placeholder="例: 本会議, 委員会",
        )

        # Term (期/会期/年度)
        term = st.text_input(
            "期/会期/年度",
            value=form_data.term or "",
            placeholder="例: 第220回, 令和5年度",
            help="国会の場合は「第XXX回」、地方議会の場合は「令和X年度」など",
        )

        # Members introduction URL
        members_url = st.text_input(
            "議員紹介URL",
            value=form_data.members_introduction_url or "",
            placeholder="例: https://example.com/members",
        )

        # Submit button
        submitted = st.form_submit_button("登録", type="primary")

        if submitted:
            _handle_form_submission(
                presenter,
                form_data,
                name,
                governing_body_id,
                prefecture,
                conf_type,
                term,
                members_url,
            )


def _handle_form_submission(
    presenter: ConferencePresenter,
    form_data: ConferenceFormData,
    name: str,
    governing_body_id: int | None,
    prefecture: str,
    conf_type: str,
    term: str,
    members_url: str,
) -> None:
    """Handle form submission for conference creation.

    Args:
        presenter: 会議体プレゼンター
        form_data: フォームデータ
        name: 会議体名
        governing_body_id: 開催主体ID
        prefecture: 都道府県
        conf_type: 種別
        term: 期/会期/年度
        members_url: 議員紹介URL
    """
    # Validation
    if not name:
        st.error("会議体名を入力してください。")
    elif not governing_body_id:
        st.error("開催主体を選択してください。")
    else:
        # Update form data
        form_data.name = name
        form_data.governing_body_id = governing_body_id
        form_data.prefecture = prefecture if prefecture else None
        form_data.type = conf_type if conf_type else None
        form_data.term = term if term else None
        form_data.members_introduction_url = members_url if members_url else None

        # Create conference
        success, error_message = asyncio.run(presenter.create_conference(form_data))

        if success:
            st.success("会議体を登録しました。")
            presenter.clear_form_data("new")
            st.rerun()
        else:
            st.error(f"登録に失敗しました: {error_message}")
