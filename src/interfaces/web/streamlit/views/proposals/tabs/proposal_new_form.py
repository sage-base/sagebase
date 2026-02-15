"""Tab 1: 新規議案登録・スクレイピングフォーム.

議案の新規登録フォームとURLからの自動抽出機能を提供します。
"""

from typing import Any

import streamlit as st

from ..dialogs import show_create_politician_dialog

from src.common.logging import get_logger
from src.domain.value_objects.submitter_type import SubmitterType
from src.interfaces.web.streamlit.presenters.proposal_presenter import ProposalPresenter
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


logger = get_logger(__name__)


def render_new_proposal_form(presenter: ProposalPresenter) -> None:
    """Render new proposal creation form."""
    with st.expander("新規議案登録"):
        # 提出者種別の選択（フォーム外に配置して動的更新を可能に）
        st.markdown("**提出者情報**")

        submitter_type_options_new: dict[str, str | None] = {
            "未設定": None,
            "👤 市長": "mayor",
            "👥 議員": "politician",
            "🏛️ 会派": "parliamentary_group",
            "📋 委員会": "committee",
            "❓ その他": "other",
        }

        selected_type_label_new = st.selectbox(
            "提出者種別",
            options=list(submitter_type_options_new.keys()),
            key="new_submitter_type",
        )
        selected_type_new = submitter_type_options_new[selected_type_label_new]

        # 種別に応じた追加入力（フォーム外）
        submitter_name_new = ""
        submitter_politician_ids_new: list[int] = []
        submitter_parliamentary_group_id_new: int | None = None

        if selected_type_new == "politician":
            try:
                politicians = presenter.load_politicians()
                politician_opts: dict[str, int] = {
                    f"{p.name} (ID: {p.id})": p.id for p in politicians if p.id
                }

                # 作成直後の政治家をデフォルト選択に追加
                created_pol_id = st.session_state.get("created_politician_id")
                created_pol_name = st.session_state.get("created_politician_name")
                default_selections: list[str] = []
                if created_pol_id and created_pol_name:
                    key = f"{created_pol_name} (ID: {created_pol_id})"
                    if key in politician_opts:
                        default_selections = [key]
                    st.session_state.pop("created_politician_id", None)
                    st.session_state.pop("created_politician_name", None)

                col_pol, col_btn = st.columns([4, 1])
                with col_pol:
                    selected_pols_new = st.multiselect(
                        "議員を選択（複数選択可）",
                        options=list(politician_opts.keys()),
                        default=default_selections,
                        key="new_submitter_politicians",
                    )
                with col_btn:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("➕ 新規", key="new_politician_btn"):
                        show_create_politician_dialog()

                submitter_politician_ids_new = [
                    politician_opts[name] for name in selected_pols_new
                ]
            except Exception:
                logger.exception("議員情報の読み込みに失敗")
                st.warning("議員情報の読み込みに失敗しました")

        elif selected_type_new == "parliamentary_group":
            st.info("会派を選択するには、下の会議体選択で会議体を選択してください。")

        elif selected_type_new in ("mayor", "committee", "other"):
            default_name_new = "市長" if selected_type_new == "mayor" else ""
            submitter_name_new = st.text_input(
                "提出者名",
                value=default_name_new,
                key="new_submitter_name",
            )

        st.markdown("---")

        with st.form("new_proposal_form"):
            title = st.text_area("議案タイトル *", placeholder="議案のタイトルを入力")

            col1, col2 = st.columns(2)
            with col1:
                detail_url = st.text_input("詳細URL", placeholder="https://...")
                status_url = st.text_input(
                    "状態URL (optional)", placeholder="https://..."
                )
                votes_url = st.text_input(
                    "賛否URL (optional)", placeholder="https://..."
                )

            with col2:
                # Load meetings and conferences for selection
                try:
                    meetings = presenter.load_meetings()
                    meeting_options: dict[str, int | None] = {"なし": None}
                    meeting_options.update(
                        {f"{m['name']} (ID: {m['id']})": m["id"] for m in meetings}
                    )
                    selected_meeting = st.selectbox(
                        "紐づく会議 (optional)",
                        options=list(meeting_options.keys()),
                        index=0,
                    )
                    meeting_id = meeting_options[selected_meeting]
                except Exception:
                    logger.exception("会議一覧の読み込みに失敗")
                    meeting_id = None
                    st.warning("会議一覧の読み込みに失敗しました")

                conferences: list[dict[str, Any]] = []
                try:
                    conferences = presenter.load_conferences()
                    conference_options: dict[str, int | None] = {"なし": None}
                    for c in conferences:
                        conference_options[f"{c['name']} (ID: {c['id']})"] = c["id"]
                    selected_conference = st.selectbox(
                        "紐づく会議体 (optional)",
                        options=list(conference_options.keys()),
                        index=0,
                    )
                    conference_id = conference_options[selected_conference]
                except Exception:
                    logger.exception("会議体一覧の読み込みに失敗")
                    conference_id = None
                    st.warning("会議体一覧の読み込みに失敗しました")

            # 会派選択（会議体が選択されている場合のみフォーム内で表示）
            if selected_type_new == "parliamentary_group" and conference_id:
                try:
                    candidates = presenter.get_submitter_candidates(conference_id)
                    pg_opts: dict[str, int | None] = {"選択してください": None}
                    pg_opts.update(
                        {
                            f"{pg.name} (ID: {pg.id})": pg.id
                            for pg in candidates.parliamentary_groups
                        }
                    )
                    selected_pg_new = st.selectbox(
                        "会派を選択",
                        options=list(pg_opts.keys()),
                        key="new_submitter_pg",
                    )
                    submitter_parliamentary_group_id_new = pg_opts[selected_pg_new]
                    if submitter_parliamentary_group_id_new:
                        for pg in candidates.parliamentary_groups:
                            if pg.id == submitter_parliamentary_group_id_new:
                                submitter_name_new = pg.name
                                break
                except Exception:
                    logger.exception("会派情報の読み込みに失敗")
                    st.warning("会派情報の読み込みに失敗しました")

            submitted = st.form_submit_button("登録")

            if submitted:
                if not title:
                    st.error("議案タイトルは必須です")
                else:
                    try:
                        user_id = presenter.get_current_user_id()
                        result = presenter.create(
                            title=title,
                            detail_url=detail_url or None,
                            status_url=status_url or None,
                            votes_url=votes_url or None,
                            meeting_id=meeting_id,
                            conference_id=conference_id,
                            user_id=user_id,
                        )

                        if result.success and result.proposal:
                            # Register submitters
                            if selected_type_new == "politician":
                                if submitter_politician_ids_new:
                                    presenter.update_submitters(
                                        proposal_id=result.proposal.id,  # type: ignore[arg-type]
                                        politician_ids=submitter_politician_ids_new,
                                    )
                            elif selected_type_new == "parliamentary_group":
                                if submitter_parliamentary_group_id_new:
                                    presenter.update_submitters(
                                        proposal_id=result.proposal.id,  # type: ignore[arg-type]
                                        parliamentary_group_id=submitter_parliamentary_group_id_new,
                                    )
                            elif selected_type_new in ("mayor", "committee", "other"):
                                if submitter_name_new:
                                    presenter.update_submitters(
                                        proposal_id=result.proposal.id,  # type: ignore[arg-type]
                                        other_submitter=(
                                            SubmitterType(selected_type_new),
                                            submitter_name_new,
                                        ),
                                    )
                            st.success(result.message)
                            st.rerun()
                        elif result.success:
                            st.success(result.message)
                            st.rerun()
                        else:
                            st.error(result.message)
                    except Exception as e:
                        handle_ui_error(e, "議案の登録")


def render_scrape_proposal_section(presenter: ProposalPresenter) -> None:
    """Render proposal scraping section."""
    with st.expander("議案情報の自動抽出"):
        st.markdown("URLから議案情報を自動的に抽出してデータベースに保存します。")

        with st.form("scrape_proposal_form"):
            url = st.text_input("議案詳細URL *", placeholder="https://...")
            meeting_id = st.number_input(
                "会議ID (オプション)", min_value=0, value=0, step=1
            )

            submitted = st.form_submit_button("抽出実行")

            if submitted:
                if not url:
                    st.error("URLは必須です")
                else:
                    with st.spinner("議案情報を抽出中..."):
                        try:
                            result = presenter.scrape_proposal(
                                url=url,
                                meeting_id=meeting_id if meeting_id > 0 else None,
                            )

                            if result:
                                st.success("議案情報を抽出しました")
                                st.json(
                                    {
                                        "タイトル": result.title[:100] + "..."
                                        if len(result.title) > 100
                                        else result.title,
                                    }
                                )
                                st.rerun()
                            else:
                                st.warning("議案情報を抽出できませんでした")
                        except Exception as e:
                            handle_ui_error(e, "議案の抽出")
