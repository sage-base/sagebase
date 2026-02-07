"""共通ウィジェット.

会議体管理画面の複数タブで共有されるUIコンポーネントを提供します。
"""

import streamlit as st

from src.application.dtos.election_dto import ElectionOutputItem
from src.interfaces.web.streamlit.presenters.conference_presenter import (
    ConferencePresenter,
)


def render_governing_body_and_election_selector(
    presenter: ConferencePresenter,
    gb_options: dict[str, int | None],
    governing_body_index: int,
    current_election_id: int | None,
    key_prefix: str,
) -> tuple[int | None, int | None]:
    """開催主体と選挙セレクターをフラグメントとしてレンダリングする.

    st.fragmentでラップすることで、開催主体変更時にページ全体のリランを防ぎ、
    タブ遷移が発生しないようにします。

    Args:
        presenter: 会議体プレゼンター
        gb_options: 開催主体の表示名→IDマッピング
        governing_body_index: 現在の開催主体のインデックス
        current_election_id: 現在選択されている選挙ID
        key_prefix: ウィジェットキーのプレフィックス

    Returns:
        (開催主体ID, 選挙ID) のタプル
    """
    # session_stateのキー
    gb_key = f"{key_prefix}_governing_body_id"
    election_key = f"{key_prefix}_election_id"

    @st.fragment
    def _selector_fragment() -> None:
        selected_gb = st.selectbox(
            "開催主体 *",
            options=list(gb_options.keys()),
            index=governing_body_index,
            key=f"{key_prefix}_governing_body_select",
        )
        governing_body_id = gb_options[selected_gb] if selected_gb else None
        st.session_state[gb_key] = governing_body_id

        election_id = _render_election_selector(
            presenter, governing_body_id, current_election_id, key_prefix
        )
        st.session_state[election_key] = election_id

    _selector_fragment()

    return (
        st.session_state.get(gb_key),
        st.session_state.get(election_key),
    )


def _render_election_selector(
    presenter: ConferencePresenter,
    governing_body_id: int | None,
    current_election_id: int | None,
    key_prefix: str,
) -> int | None:
    """選挙選択ドロップダウンをレンダリングする.

    Args:
        presenter: 会議体プレゼンター
        governing_body_id: 開催主体ID
        current_election_id: 現在選択されている選挙ID
        key_prefix: ウィジェットキーのプレフィックス

    Returns:
        選択された選挙ID（なしの場合はNone）
    """
    if not governing_body_id:
        st.info("選挙を選択するには、先に開催主体を選択してください。")
        return None

    # Presenter経由でUseCase→Repositoryの順にアクセス（同期呼び出し）
    elections: list[ElectionOutputItem] = presenter.get_elections_for_governing_body(
        governing_body_id
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
        key=f"{key_prefix}_election_select",
        help="会議体を紐付ける選挙（期）を選択してください",
    )

    return election_options.get(selected_election) if selected_election else None
