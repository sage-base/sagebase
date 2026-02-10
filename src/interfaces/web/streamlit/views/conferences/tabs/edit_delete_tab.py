"""Edit and delete tab for conferences.

会議体の編集・削除タブのUI実装を提供します。
"""

import asyncio

from typing import cast

import streamlit as st

from ..widgets import render_governing_body_and_election_selector

from src.domain.entities import Conference, GoverningBody
from src.domain.repositories import ConferenceRepository, GoverningBodyRepository
from src.interfaces.web.streamlit.presenters.conference_presenter import (
    ConferenceFormData,
    ConferencePresenter,
)
from src.interfaces.web.streamlit.views.constants import PREFECTURES


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

    # 開催主体一覧を取得してフィルターに渡す
    governing_bodies = cast(list[GoverningBody], governing_body_repo.get_all())

    # 都道府県フィルター（開催主体のprefecture経由）
    filtered_conferences = _render_filters(conferences, governing_bodies)

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


def _render_filters(
    conferences: list[Conference],
    governing_bodies: list[GoverningBody],
) -> list[Conference]:
    """Render filter controls and return filtered conferences.

    Args:
        conferences: 全会議体リスト
        governing_bodies: 全開催主体リスト

    Returns:
        フィルタリングされた会議体リスト
    """
    st.markdown("#### フィルター")

    # 開催主体IDから都道府県へのマッピングを構築
    gb_prefecture_map = {gb.id: gb.prefecture for gb in governing_bodies}

    col1, col2 = st.columns([2, 1])

    with col1:
        prefecture_filter_options = ["すべて"] + [p for p in PREFECTURES if p]
        selected_prefecture_filter = st.selectbox(
            "都道府県でフィルター",
            prefecture_filter_options,
            key="edit_prefecture_filter",
        )

    with col2:
        filter_no_prefecture = st.checkbox(
            "都道府県が未設定のみ",
            key="filter_no_prefecture",
            help="開催主体に都道府県が設定されていない会議体のみ表示",
        )

    # フィルターを適用
    filtered_conferences = conferences

    # 都道府県未設定フィルター（優先）
    if filter_no_prefecture:
        filtered_conferences = [
            c
            for c in filtered_conferences
            if not gb_prefecture_map.get(c.governing_body_id)
        ]
    elif selected_prefecture_filter != "すべて":
        filtered_conferences = [
            c
            for c in conferences
            if gb_prefecture_map.get(c.governing_body_id) == selected_prefecture_filter
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
    gb_options: dict[str, int | None] = {
        f"{gb.name} ({gb.type})": gb.id for gb in governing_bodies
    }

    # 現在の開催主体のインデックスを計算
    current_gb = next(
        (
            f"{gb.name} ({gb.type})"
            for gb in governing_bodies
            if gb.id == form_data.governing_body_id
        ),
        None,
    )
    gb_index = list(gb_options.keys()).index(current_gb) if current_gb else 0

    # 開催主体・選挙選択（st.fragmentでタブ遷移を防止）
    governing_body_id, election_id = render_governing_body_and_election_selector(
        presenter=presenter,
        gb_options=gb_options,
        governing_body_index=gb_index,
        current_election_id=form_data.election_id,
        key_prefix=f"edit_{conference_id}",
    )

    with st.form(f"conference_edit_form_{conference_id}"):
        # Conference name
        name = st.text_input(
            "会議体名 *",
            value=form_data.name,
        )

        # Term (期/会期/年度)
        term = st.text_input(
            "期/会期/年度",
            value=form_data.term or "",
            help="国会の場合は「第XXX回」、地方議会の場合は「令和X年度」など",
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
                election_id,
                term,
            )

        if delete_button:
            _handle_delete(presenter, conference_id)


def _handle_update(
    presenter: ConferencePresenter,
    form_data: ConferenceFormData,
    conference_id: int,
    name: str,
    governing_body_id: int | None,
    election_id: int | None,
    term: str,
) -> None:
    """Handle conference update.

    Args:
        presenter: 会議体プレゼンター
        form_data: フォームデータ
        conference_id: 会議体ID
        name: 会議体名
        governing_body_id: 開催主体ID
        election_id: 選挙ID
        term: 期/会期/年度
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
        form_data.term = term if term else None

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
