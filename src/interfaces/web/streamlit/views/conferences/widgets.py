"""共通ウィジェット.

会議体管理画面の複数タブで共有されるUIコンポーネントを提供します。
"""

import streamlit as st

from src.application.dtos.election_dto import ElectionOutputItem
from src.interfaces.web.streamlit.presenters.conference_presenter import (
    ConferencePresenter,
)


def render_election_selector(
    presenter: ConferencePresenter,
    governing_body_id: int | None,
    current_election_id: int | None,
) -> int | None:
    """選挙選択ドロップダウンをレンダリングする.

    選択された開催主体に紐づく選挙をPresenter経由で取得し、ドロップダウンで表示します。

    Args:
        presenter: 会議体プレゼンター
        governing_body_id: 開催主体ID
        current_election_id: 現在選択されている選挙ID

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
        help="会議体を紐付ける選挙（期）を選択してください",
    )

    return election_options.get(selected_election) if selected_election else None
