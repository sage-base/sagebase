"""Tab 1: 議案管理タブ（メイン）.

議案のフィルタリング、ページネーション、一覧表示を提供します。
"""

import streamlit as st

from ..constants import PROPOSALS_PAGE_SIZE
from .proposal_edit_form import render_proposal_row
from .proposal_new_form import render_new_proposal_form, render_scrape_proposal_section

from src.common.logging import get_logger
from src.interfaces.web.streamlit.presenters.proposal_presenter import ProposalPresenter
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


logger = get_logger(__name__)


def render_proposals_tab(presenter: ProposalPresenter) -> None:
    """Render the proposals management tab."""

    # Filter section
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        filter_options = {
            "すべて": "all",
            "会議別": "by_meeting",
            "会議体別": "by_conference",
            "開催主体別": "by_governing_body",
        }
        selected_filter = st.selectbox(
            "表示フィルター", options=list(filter_options.keys()), index=0
        )
        filter_type = filter_options[selected_filter]

    # Additional filters based on selection
    meeting_filter: int | None = None
    conference_filter: int | None = None
    governing_body_filter: int | None = None

    if filter_type == "by_meeting":
        with col2:
            try:
                meetings = presenter.load_meetings()
                meeting_options: dict[str, int | None] = {"選択してください": None}
                meeting_options.update(
                    {f"{m['name']} (ID: {m['id']})": m["id"] for m in meetings}
                )
                selected_meeting = st.selectbox(
                    "会議",
                    options=list(meeting_options.keys()),
                    key="filter_meeting_select",
                )
                meeting_filter = meeting_options[selected_meeting]
            except Exception:
                logger.exception("会議一覧の読み込みに失敗")
                meeting_filter = st.number_input("会議ID", min_value=1, step=1)

    elif filter_type == "by_conference":
        with col2:
            try:
                conferences = presenter.load_conferences()
                conference_options: dict[str, int | None] = {"選択してください": None}
                conference_options.update(
                    {f"{c['name']} (ID: {c['id']})": c["id"] for c in conferences}
                )
                selected_conference = st.selectbox(
                    "会議体",
                    options=list(conference_options.keys()),
                    key="filter_conference_select",
                )
                conference_filter = conference_options[selected_conference]
            except Exception:
                logger.exception("会議体一覧の読み込みに失敗")
                conference_filter = st.number_input("会議体ID", min_value=1, step=1)

    elif filter_type == "by_governing_body":
        with col2:
            try:
                governing_bodies = presenter.load_governing_bodies()
                governing_body_options: dict[str, int | None] = {
                    "選択してください": None
                }
                governing_body_options.update(
                    {f"{g['name']} (ID: {g['id']})": g["id"] for g in governing_bodies}
                )
                selected_governing_body = st.selectbox(
                    "開催主体",
                    options=list(governing_body_options.keys()),
                    key="filter_governing_body_select",
                )
                governing_body_filter = governing_body_options[selected_governing_body]
            except Exception:
                logger.exception("開催主体一覧の読み込みに失敗")
                st.warning("開催主体一覧の読み込みに失敗しました")

    # 追加フィルター: 提出回次・審議状況
    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        session_number_input = st.number_input(
            "提出回次（0で全て）",
            min_value=0,
            value=0,
            step=1,
            key="filter_session_number",
        )
        session_number_filter: int | None = (
            session_number_input if session_number_input > 0 else None
        )

    with filter_col2:
        try:
            statuses = presenter.load_distinct_deliberation_statuses()
            status_options = ["すべて"] + statuses
        except Exception:
            logger.exception("審議状況一覧の読み込みに失敗")
            status_options = ["すべて"]
        selected_status = st.selectbox(
            "審議状況",
            options=status_options,
            index=0,
            key="filter_deliberation_status",
        )
        deliberation_status_filter: str | None = (
            selected_status if selected_status != "すべて" else None
        )

    # Load data
    try:
        # 開催主体フィルターの場合は、その開催主体に属する会議体IDを取得してフィルター
        actual_conference_filter = conference_filter
        if filter_type == "by_governing_body" and governing_body_filter:
            # 開催主体に属する会議体をDB側で取得
            gb_conferences = presenter.load_conferences_by_governing_body(
                governing_body_filter
            )
            if gb_conferences:
                # 最初の会議体IDでフィルター（DB側ページネーションを使うため）
                # TODO: 複数会議体の場合はIN句対応が必要
                actual_conference_filter = gb_conferences[0]["id"]
                filter_type = "by_conference"
            else:
                actual_conference_filter = None

        # フィルター変更時にページをリセット
        current_filter_key = (
            f"{filter_type}:{meeting_filter}:{actual_conference_filter}"
            f":{session_number_filter}:{deliberation_status_filter}"
        )
        prev_filter_key = st.session_state.get("proposals_filter_key", "")
        if current_filter_key != prev_filter_key:
            st.session_state.proposals_page = 0
            st.session_state.proposals_filter_key = current_filter_key

        # ページネーション状態
        if "proposals_page" not in st.session_state:
            st.session_state.proposals_page = 0

        page = st.session_state.proposals_page
        offset = page * PROPOSALS_PAGE_SIZE

        # DB側ページネーションで必要なページ分だけ取得
        # _run_async呼び出しを1回に統合し、fragment内でのevent loopブロックを最小化
        # ロード中フラグで多重rerunを防止
        st.session_state["_proposals_loading"] = True
        try:
            page_data = presenter.load_proposals_page_data(
                filter_type=filter_type,
                meeting_id=meeting_filter,
                conference_id=actual_conference_filter,
                limit=PROPOSALS_PAGE_SIZE,
                offset=offset,
                session_number=session_number_filter,
                deliberation_status=deliberation_status_filter,
            )
        finally:
            st.session_state["_proposals_loading"] = False

        proposals = page_data.result.proposals
        total_count = page_data.result.total_count

        st.session_state["proposal_related_data_map"] = page_data.related_data_map

        # Display statistics
        with col3:
            st.metric("議案数", total_count)

        # New proposal section
        render_new_proposal_form(presenter)

        # Scrape proposal section
        render_scrape_proposal_section(presenter)

        # Display proposals list
        if proposals:
            st.subheader("議案一覧")

            total_pages = max(
                1,
                (total_count + PROPOSALS_PAGE_SIZE - 1) // PROPOSALS_PAGE_SIZE,
            )
            # ページ番号がはみ出さないよう補正
            if st.session_state.proposals_page >= total_pages:
                st.session_state.proposals_page = total_pages - 1

            for proposal in proposals:
                render_proposal_row(
                    presenter,
                    proposal,
                    page_data.submitters_map,
                    page_data.politician_names,
                    page_data.conference_names,
                    page_data.pg_names,
                )

            # ページネーションUI
            # on_clickコールバックを使用（st.rerunを避けevent loop衝突を防止）
            # ロード中は何もしないガードで多重rerunを防止
            def _go_prev() -> None:
                if st.session_state.get("_proposals_loading"):
                    return
                st.session_state.proposals_page -= 1

            def _go_next() -> None:
                if st.session_state.get("_proposals_loading"):
                    return
                st.session_state.proposals_page += 1

            if total_pages > 1:
                is_loading = st.session_state.get("_proposals_loading", False)
                col_prev, col_info, col_next = st.columns([1, 2, 1])
                with col_prev:
                    st.button(
                        "← 前へ",
                        disabled=st.session_state.proposals_page == 0 or is_loading,
                        key="proposals_prev_page",
                        on_click=_go_prev,
                    )
                with col_info:
                    st.markdown(
                        f"ページ {st.session_state.proposals_page + 1} / {total_pages}"
                        f"（全{total_count}件）",
                    )
                with col_next:
                    st.button(
                        "次へ →",
                        disabled=st.session_state.proposals_page >= total_pages - 1
                        or is_loading,
                        key="proposals_next_page",
                        on_click=_go_next,
                    )
        elif total_count > 0:
            st.info("このページには表示する議案がありません。")
        else:
            st.info("表示する議案がありません。")

    except Exception as e:
        st.session_state["_proposals_loading"] = False
        handle_ui_error(e, "議案一覧の読み込み")
