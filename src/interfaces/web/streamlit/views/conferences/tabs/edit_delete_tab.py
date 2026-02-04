"""Edit and delete tab for conferences.

会議体の編集・削除タブのUI実装を提供します。
"""

import asyncio

from typing import cast

import streamlit as st

from ..constants import CONFERENCE_PREFECTURES

from src.domain.entities import Conference
from src.domain.repositories import ConferenceRepository, GoverningBodyRepository
from src.interfaces.web.streamlit.presenters.conference_presenter import (
    ConferenceFormData,
    ConferencePresenter,
)


def render_edit_delete_form(
    presenter: ConferencePresenter,
    conference_repo: ConferenceRepository,
    governing_body_repo: GoverningBodyRepository,
) -> None:
    """Render edit and delete form.

    会議体の編集・削除フォームをレンダリングします。
    都道府県でのフィルタリング、会議体情報の編集、削除機能を提供します。

    Args:
        presenter: 会議体プレゼンター
        conference_repo: 会議体リポジトリ
        governing_body_repo: 開催主体リポジトリ
    """
    st.header("会議体の編集・削除")

    # Load all conferences for selection
    # Note: conference_repoはDependencyContainerでラップされており、同期的にリストを返す
    conferences = cast(list[Conference], conference_repo.get_all())

    if not conferences:
        st.info("編集可能な会議体がありません。")
        return

    # 都道府県フィルター
    filtered_conferences = _render_filters(conferences)

    if not filtered_conferences:
        st.warning("条件に一致する会議体がありません。")
        return

    # Conference selection
    conf_options = {
        f"{conf.name} (ID: {conf.id})": conf.id for conf in filtered_conferences
    }

    selected_conf = st.selectbox(
        "編集する会議体を選択",
        options=list(conf_options.keys()),
        key="edit_conference_select",
    )

    if selected_conf:
        conference_id = conf_options[selected_conf]
        assert conference_id is not None  # DBから取得した会議体は必ずIDを持つ
        conference = next(c for c in conferences if c.id == conference_id)

        _render_edit_form(presenter, conference, conference_id, governing_body_repo)


def _render_filters(conferences: list[Conference]) -> list[Conference]:
    """Render filter controls and return filtered conferences.

    Args:
        conferences: 全会議体リスト

    Returns:
        フィルタリングされた会議体リスト
    """
    st.markdown("#### フィルター")
    col1, col2 = st.columns([2, 1])

    with col1:
        prefecture_filter_options = ["すべて"] + [
            p for p in CONFERENCE_PREFECTURES if p
        ]
        selected_prefecture_filter = st.selectbox(
            "都道府県でフィルター",
            prefecture_filter_options,
            key="edit_prefecture_filter",
        )

    with col2:
        filter_no_prefecture = st.checkbox(
            "都道府県が未設定のみ",
            key="filter_no_prefecture",
            help="都道府県が設定されていない会議体のみ表示",
        )

    # フィルターを適用
    filtered_conferences = conferences

    # 都道府県未設定フィルター（優先）
    if filter_no_prefecture:
        filtered_conferences = [c for c in filtered_conferences if not c.prefecture]
    elif selected_prefecture_filter != "すべて":
        filtered_conferences = [
            c for c in conferences if c.prefecture == selected_prefecture_filter
        ]

    # フィルター結果の表示
    is_filtered = filter_no_prefecture or selected_prefecture_filter != "すべて"
    if is_filtered:
        st.info(
            f"フィルター適用中: {len(filtered_conferences)}件 / 全{len(conferences)}件"
        )

    return filtered_conferences


def _render_edit_form(
    presenter: ConferencePresenter,
    conference: Conference,
    conference_id: int,
    governing_body_repo: GoverningBodyRepository,
) -> None:
    """Render the edit form for a conference.

    Args:
        presenter: 会議体プレゼンター
        conference: 会議体エンティティ
        conference_id: 会議体ID
        governing_body_repo: 開催主体リポジトリ
    """
    # Load form data
    form_data = presenter.load_conference_for_edit(conference)

    # Load governing bodies for dropdown
    governing_bodies = governing_body_repo.get_all()
    gb_options = {f"{gb.name} ({gb.type})": gb.id for gb in governing_bodies}

    with st.form(f"conference_edit_form_{conference_id}"):
        # Conference name
        name = st.text_input(
            "会議体名 *",
            value=form_data.name,
        )

        # Governing body selection
        current_gb = next(
            (
                f"{gb.name} ({gb.type})"
                for gb in governing_bodies
                if gb.id == form_data.governing_body_id
            ),
            None,
        )
        selected_gb = st.selectbox(
            "開催主体 *",
            options=list(gb_options.keys()),
            index=list(gb_options.keys()).index(current_gb) if current_gb else 0,
        )
        governing_body_id = gb_options[selected_gb] if selected_gb else None

        # Prefecture selection
        prefecture_options = [p for p in CONFERENCE_PREFECTURES if p]
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
            help="国会の場合は「第XXX回」、地方議会の場合は「令和X年度」など",
        )

        # Members introduction URL
        members_url = st.text_input(
            "議員紹介URL",
            value=form_data.members_introduction_url or "",
        )

        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            update_button = st.form_submit_button("更新", type="primary")
        with col2:
            delete_button = st.form_submit_button("削除", type="secondary")

        if update_button:
            _handle_update(
                presenter,
                form_data,
                conference_id,
                name,
                governing_body_id,
                prefecture,
                term,
                members_url,
            )

        if delete_button:
            _handle_delete(presenter, conference_id)


def _handle_update(
    presenter: ConferencePresenter,
    form_data: ConferenceFormData,
    conference_id: int,
    name: str,
    governing_body_id: int | None,
    prefecture: str,
    term: str,
    members_url: str,
) -> None:
    """Handle conference update.

    Args:
        presenter: 会議体プレゼンター
        form_data: フォームデータ
        conference_id: 会議体ID
        name: 会議体名
        governing_body_id: 開催主体ID
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
        form_data.prefecture = prefecture if prefecture else None
        form_data.term = term if term else None
        form_data.members_introduction_url = members_url if members_url else None

        # Update conference
        success, error_message = asyncio.run(
            presenter.update_conference(conference_id, form_data)
        )

        if success:
            st.success("会議体を更新しました。")
            st.rerun()
        else:
            st.error(f"更新に失敗しました: {error_message}")


def _handle_delete(presenter: ConferencePresenter, conference_id: int) -> None:
    """Handle conference deletion.

    Args:
        presenter: 会議体プレゼンター
        conference_id: 会議体ID
    """
    # Delete conference
    success, error_message = asyncio.run(presenter.delete_conference(conference_id))

    if success:
        st.success("会議体を削除しました。")
        st.rerun()
    else:
        st.error(f"削除に失敗しました: {error_message}")
