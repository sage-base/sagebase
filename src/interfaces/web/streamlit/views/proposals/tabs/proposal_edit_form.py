"""Tab 1: 議案表示・編集フォーム.

議案一覧の行表示と編集フォームを提供します。
"""

import streamlit as st

from ..dialogs import show_create_politician_dialog
from ..helpers import build_submitters_text

from src.common.logging import get_logger
from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_submitter import ProposalSubmitter
from src.domain.value_objects.submitter_type import SubmitterType
from src.interfaces.web.streamlit.presenters.proposal_presenter import ProposalPresenter
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


logger = get_logger(__name__)


def render_proposal_row(
    presenter: ProposalPresenter,
    proposal: Proposal,
    submitters_map: dict[int, list[ProposalSubmitter]] | None = None,
    politician_names: dict[int, str] | None = None,
    conference_names: dict[int, str] | None = None,
    pg_names: dict[int, str] | None = None,
) -> None:
    """Render a single proposal row."""
    # Check if this proposal is being edited
    if proposal.id is not None and presenter.is_editing(proposal.id):
        render_edit_proposal_form(presenter, proposal)
    else:
        render_proposal_display(
            presenter,
            proposal,
            submitters_map,
            politician_names,
            conference_names,
            pg_names,
        )


def render_proposal_display(
    presenter: ProposalPresenter,
    proposal: Proposal,
    submitters_map: dict[int, list[ProposalSubmitter]] | None = None,
    politician_names: dict[int, str] | None = None,
    conference_names: dict[int, str] | None = None,
    pg_names: dict[int, str] | None = None,
) -> None:
    """Render proposal in display mode.

    WebSocket負荷を削減するため、1行あたりのStreamlit要素数を最小化する。
    複数のst.markdownを1つに統合し、columns数も最小限にする。
    """
    related_data_map: dict[int, dict[str, str | None]] = st.session_state.get(
        "proposal_related_data_map", {}
    )
    related_data = related_data_map.get(proposal.id, {}) if proposal.id else {}
    conference_name = related_data.get("conference_name")
    governing_body_name = related_data.get("governing_body_name")

    info_lines: list[str] = [f"**議案 #{proposal.id}** {proposal.title[:100]}"]

    meta_parts: list[str] = []
    if conference_name:
        meta_parts.append(f"会議体: {conference_name}")
    if governing_body_name:
        meta_parts.append(f"開催主体: {governing_body_name}")
    if proposal.session_number is not None:
        meta_parts.append(f"第{proposal.session_number}回")
    if proposal.deliberation_status:
        meta_parts.append(f"審議状況: {proposal.deliberation_status}")
    if meta_parts:
        info_lines.append(" | ".join(meta_parts))

    submitter_text = build_submitters_text(
        proposal, submitters_map, politician_names, conference_names, pg_names
    )
    info_lines.append(f"提出者: {submitter_text}")

    url_parts: list[str] = []
    if proposal.detail_url:
        url_parts.append(f"[詳細]({proposal.detail_url})")
    if proposal.status_url:
        url_parts.append(f"[状態]({proposal.status_url})")
    if proposal.votes_url:
        url_parts.append(f"[賛否]({proposal.votes_url})")
    if url_parts:
        info_lines.append(" | ".join(url_parts))

    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown("  \n".join(info_lines))
    with col2:
        if st.button("編集", key=f"edit_proposal_{proposal.id}"):
            if proposal.id is not None:
                presenter.set_editing_mode(proposal.id)
                st.rerun()
        if st.button(
            "削除",
            key=f"delete_proposal_{proposal.id}",
            type="secondary",
        ):
            st.session_state[f"confirm_delete_{proposal.id}"] = True

    if st.session_state.get(f"confirm_delete_{proposal.id}", False):
        st.warning("本当に削除しますか？")
        col_confirm1, col_confirm2 = st.columns(2)
        with col_confirm1:
            if st.button("はい", key=f"confirm_yes_{proposal.id}"):
                try:
                    user_id = presenter.get_current_user_id()
                    result = presenter.delete(
                        proposal_id=proposal.id,
                        user_id=user_id,
                    )
                    if result.success:
                        st.success(result.message)
                        del st.session_state[f"confirm_delete_{proposal.id}"]
                        st.rerun()
                    else:
                        st.error(result.message)
                except Exception as e:
                    handle_ui_error(e, "議案の削除")
        with col_confirm2:
            if st.button("いいえ", key=f"confirm_no_{proposal.id}"):
                del st.session_state[f"confirm_delete_{proposal.id}"]
                st.rerun()

    st.divider()


def render_edit_proposal_form(presenter: ProposalPresenter, proposal: Proposal) -> None:
    """Render proposal edit form."""
    with st.container():
        st.markdown(f"### 議案 #{proposal.id} を編集中")

        # 現在の提出者を取得
        current_submitters = presenter.load_submitters(proposal.id)  # type: ignore[arg-type]
        current_submitter = current_submitters[0] if current_submitters else None

        # 提出者種別の選択肢（フォーム外に配置して動的更新を可能に）
        st.markdown("**提出者情報の編集**")

        submitter_type_options: dict[str, str | None] = {
            "未設定": None,
            "👤 市長": "mayor",
            "👥 議員": "politician",
            "🏛️ 会派": "parliamentary_group",
            "📋 委員会": "committee",
            "❓ その他": "other",
        }

        # 現在の種別を取得
        current_type_key = "未設定"
        if current_submitter:
            current_type = current_submitter.submitter_type.value
            for key, val in submitter_type_options.items():
                if val == current_type:
                    current_type_key = key
                    break

        selected_type_label = st.selectbox(
            "提出者種別",
            options=list(submitter_type_options.keys()),
            index=list(submitter_type_options.keys()).index(current_type_key),
            key=f"edit_submitter_type_{proposal.id}",
        )
        selected_type = submitter_type_options[selected_type_label]

        # 種別に応じた追加入力（フォーム外）
        submitter_name = ""
        submitter_politician_ids: list[int] = []
        submitter_parliamentary_group_id: int | None = None

        if selected_type == "politician":
            try:
                politicians = presenter.load_politicians()
                politician_options: dict[str, int] = {
                    f"{p.name} (ID: {p.id})": p.id for p in politicians if p.id
                }

                # 現在選択中の議員を取得（複数対応）
                current_politician_ids = [
                    s.politician_id
                    for s in current_submitters
                    if s.politician_id is not None
                ]
                default_selections: list[str] = [
                    name
                    for name, pid in politician_options.items()
                    if pid in current_politician_ids
                ]

                # 作成直後の政治家をデフォルト選択に追加
                created_pol_id = st.session_state.get("created_politician_id")
                created_pol_name = st.session_state.get("created_politician_name")
                if created_pol_id and created_pol_name:
                    key = f"{created_pol_name} (ID: {created_pol_id})"
                    if key in politician_options and key not in default_selections:
                        default_selections.append(key)
                    st.session_state.pop("created_politician_id", None)
                    st.session_state.pop("created_politician_name", None)

                col_pol, col_btn = st.columns([4, 1])
                with col_pol:
                    selected_pols = st.multiselect(
                        "議員を選択（複数選択可）",
                        options=list(politician_options.keys()),
                        default=default_selections,
                        key=f"edit_submitter_politicians_{proposal.id}",
                    )
                with col_btn:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("➕ 新規", key=f"edit_politician_btn_{proposal.id}"):
                        show_create_politician_dialog()

                submitter_politician_ids = [
                    politician_options[name] for name in selected_pols
                ]
            except Exception:
                logger.exception("議員情報の読み込みに失敗")
                st.warning("議員情報の読み込みに失敗しました")

        elif selected_type == "parliamentary_group":
            try:
                parliamentary_groups = presenter.load_parliamentary_groups_for_proposal(
                    proposal.id  # type: ignore[arg-type]
                )
                pg_options: dict[str, int | None] = {"選択してください": None}
                pg_options.update(
                    {
                        f"{pg.name} (ID: {pg.id})": pg.id
                        for pg in parliamentary_groups
                        if pg.id
                    }
                )

                current_pg_idx = 0
                if current_submitter and current_submitter.parliamentary_group_id:
                    for idx, (_, pgid) in enumerate(pg_options.items()):
                        if pgid == current_submitter.parliamentary_group_id:
                            current_pg_idx = idx
                            break

                selected_pg = st.selectbox(
                    "会派を選択",
                    options=list(pg_options.keys()),
                    index=current_pg_idx,
                    key=f"edit_submitter_pg_{proposal.id}",
                )
                submitter_parliamentary_group_id = pg_options[selected_pg]
                if submitter_parliamentary_group_id:
                    for pg in parliamentary_groups:
                        if pg.id == submitter_parliamentary_group_id:
                            submitter_name = pg.name
                            break
            except Exception:
                logger.exception("会派情報の読み込みに失敗")
                st.warning("会派情報の読み込みに失敗しました")

        elif selected_type in ("mayor", "committee", "other"):
            default_name = ""
            if current_submitter and current_submitter.raw_name:
                default_name = current_submitter.raw_name
            elif selected_type == "mayor":
                default_name = "市長"
            submitter_name = st.text_input(
                "提出者名",
                value=default_name,
                key=f"edit_submitter_name_{proposal.id}",
            )

        st.markdown("---")

        with st.form(f"edit_proposal_form_{proposal.id}"):
            title = st.text_area(
                "議案タイトル *",
                value=proposal.title,
                key=f"edit_title_{proposal.id}",
            )

            col1, col2 = st.columns(2)
            with col1:
                detail_url = st.text_input(
                    "詳細URL",
                    value=proposal.detail_url or "",
                    key=f"edit_detail_url_{proposal.id}",
                )
                status_url = st.text_input(
                    "状態URL",
                    value=proposal.status_url or "",
                    key=f"edit_status_url_{proposal.id}",
                )
                votes_url = st.text_input(
                    "賛否URL",
                    value=proposal.votes_url or "",
                    key=f"edit_votes_url_{proposal.id}",
                )

            with col2:
                # Load meetings
                try:
                    meetings = presenter.load_meetings()
                    meeting_options: dict[str, int | None] = {"なし": None}
                    meeting_options.update(
                        {f"{m['name']} (ID: {m['id']})": m["id"] for m in meetings}
                    )
                    current_meeting_idx = 0
                    if proposal.meeting_id:
                        for idx, (_, mid) in enumerate(meeting_options.items()):
                            if mid == proposal.meeting_id:
                                current_meeting_idx = idx
                                break
                    selected_meeting = st.selectbox(
                        "紐づく会議",
                        options=list(meeting_options.keys()),
                        index=current_meeting_idx,
                        key=f"edit_meeting_{proposal.id}",
                    )
                    meeting_id = meeting_options[selected_meeting]
                except Exception:
                    logger.exception("会議一覧の読み込みに失敗")
                    meeting_id = proposal.meeting_id
                    st.warning("会議一覧の読み込みに失敗しました")

                # Load conferences
                try:
                    conferences = presenter.load_conferences()
                    conference_options: dict[str, int | None] = {"なし": None}
                    for c in conferences:
                        conference_options[f"{c['name']} (ID: {c['id']})"] = c["id"]
                    current_conference_idx = 0
                    if proposal.conference_id:
                        for idx, (_, cid) in enumerate(conference_options.items()):
                            if cid == proposal.conference_id:
                                current_conference_idx = idx
                                break
                    selected_conference = st.selectbox(
                        "紐づく会議体",
                        options=list(conference_options.keys()),
                        index=current_conference_idx,
                        key=f"edit_conference_{proposal.id}",
                    )
                    conference_id = conference_options[selected_conference]
                except Exception:
                    logger.exception("会議体一覧の読み込みに失敗")
                    conference_id = proposal.conference_id
                    st.warning("会議体一覧の読み込みに失敗しました")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submitted = st.form_submit_button("保存", type="primary")
            with col_btn2:
                cancelled = st.form_submit_button("キャンセル")

            if submitted:
                if not title:
                    st.error("議案タイトルは必須です")
                else:
                    try:
                        user_id = presenter.get_current_user_id()
                        result = presenter.update(
                            proposal_id=proposal.id,
                            title=title,
                            detail_url=detail_url or None,
                            status_url=status_url or None,
                            votes_url=votes_url or None,
                            meeting_id=meeting_id,
                            conference_id=conference_id,
                            user_id=user_id,
                        )

                        if result.success:
                            # Update submitters
                            if selected_type == "politician":
                                presenter.update_submitters(
                                    proposal_id=proposal.id,  # type: ignore[arg-type]
                                    politician_ids=submitter_politician_ids
                                    if submitter_politician_ids
                                    else None,
                                )
                            elif selected_type == "parliamentary_group":
                                presenter.update_submitters(
                                    proposal_id=proposal.id,  # type: ignore[arg-type]
                                    parliamentary_group_id=submitter_parliamentary_group_id,
                                )
                            elif selected_type in ("mayor", "committee", "other"):
                                if submitter_name:
                                    presenter.update_submitters(
                                        proposal_id=proposal.id,  # type: ignore[arg-type]
                                        other_submitter=(
                                            SubmitterType(selected_type),
                                            submitter_name,
                                        ),
                                    )
                                else:
                                    presenter.clear_submitter(proposal.id)  # type: ignore[arg-type]
                            else:
                                # 提出者をクリア
                                presenter.clear_submitter(proposal.id)  # type: ignore[arg-type]

                            st.success(result.message)
                            presenter.cancel_editing()
                            st.rerun()
                        else:
                            st.error(result.message)
                    except Exception as e:
                        handle_ui_error(e, "議案の更新")

            if cancelled:
                presenter.cancel_editing()
                st.rerun()

        st.divider()
