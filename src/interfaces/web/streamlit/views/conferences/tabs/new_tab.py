"""New conference registration tab.

会議体新規登録タブのUI実装を提供します。
"""

import asyncio

import streamlit as st

from ..constants import CONFERENCE_PREFECTURES

from src.domain.entities import Election
from src.domain.repositories import GoverningBodyRepository
from src.infrastructure.persistence.election_repository_impl import (
    ElectionRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
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
    会議体名、開催主体、都道府県、種別、議員紹介URL、選挙の入力フォームを提供します。

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

        # Election selection (based on selected governing body)
        election_id = _render_election_selector(
            governing_body_id, form_data.election_id
        )

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
                election_id,
                prefecture,
                term,
                members_url,
            )


def _render_election_selector(
    governing_body_id: int | None, current_election_id: int | None
) -> int | None:
    """Render election selector dropdown.

    選択された開催主体に紐づく選挙を取得し、ドロップダウンで表示します。

    Args:
        governing_body_id: 開催主体ID
        current_election_id: 現在選択されている選挙ID

    Returns:
        選択された選挙ID（なしの場合はNone）
    """
    if not governing_body_id:
        st.info("選挙を選択するには、先に開催主体を選択してください。")
        return None

    # Load elections for the selected governing body
    election_repo = RepositoryAdapter(ElectionRepositoryImpl)
    elections: list[Election] = asyncio.run(
        election_repo.get_by_governing_body(governing_body_id)
    )

    if not elections:
        st.info("この開催主体には選挙が登録されていません。")
        return None

    # Build options
    election_options: dict[str, int | None] = {"（選挙を選択しない）": None}
    for election in elections:
        label = f"第{election.term_number}期 ({election.election_date})"
        if election.election_type:
            label += f" - {election.election_type}"
        election_options[label] = election.id

    # Find current selection index
    current_index = 0
    if current_election_id:
        for i, (_, eid) in enumerate(election_options.items()):
            if eid == current_election_id:
                current_index = i
                break

    selected_election = st.selectbox(
        "選挙（期）",
        options=list(election_options.keys()),
        index=current_index,
        help="会議体を紐付ける選挙（期）を選択してください",
    )

    return election_options.get(selected_election) if selected_election else None


def _handle_form_submission(
    presenter: ConferencePresenter,
    form_data: ConferenceFormData,
    name: str,
    governing_body_id: int | None,
    election_id: int | None,
    prefecture: str,
    term: str,
    members_url: str,
) -> None:
    """Handle form submission for conference creation.

    Args:
        presenter: 会議体プレゼンター
        form_data: フォームデータ
        name: 会議体名
        governing_body_id: 開催主体ID
        election_id: 選挙ID
        prefecture: 都道府県
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
        form_data.election_id = election_id
        form_data.prefecture = prefecture if prefecture else None
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
