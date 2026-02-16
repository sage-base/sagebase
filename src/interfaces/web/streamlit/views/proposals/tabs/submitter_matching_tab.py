"""Tab 7: 提出者マッチングタブ.

議案提出者の自動マッチング実行・確認・手動修正を提供します。
"""

import streamlit as st

from ..constants import PROPOSALS_PAGE_SIZE, SUBMITTER_TYPE_ICONS, SUBMITTER_TYPE_LABELS

from src.common.logging import get_logger
from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_submitter import ProposalSubmitter
from src.domain.value_objects.submitter_type import SubmitterType
from src.interfaces.web.streamlit.presenters.proposal_presenter import (
    ProposalPresenter,
)
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


logger = get_logger(__name__)


def render_submitter_matching_tab(presenter: ProposalPresenter) -> None:
    """提出者マッチングタブを描画する."""
    st.subheader("提出者マッチング")
    st.markdown("議案提出者の自動マッチングと手動修正を行います。")

    # --- 会議体フィルタ（必須） ---
    try:
        conferences = presenter.load_conferences()
    except Exception as e:
        handle_ui_error(e, "会議体一覧の読み込み")
        return

    conference_options: dict[str, int | None] = {"選択してください": None}
    conference_options.update(
        {f"{c['name']} (ID: {c['id']})": c["id"] for c in conferences}
    )
    selected_conference_label = st.selectbox(
        "会議体（必須）",
        options=list(conference_options.keys()),
        key="submitter_matching_conference_select",
    )
    selected_conference_id = conference_options[selected_conference_label]

    if selected_conference_id is None:
        st.info("会議体を選択してください。")
        return

    # 会議体変更時にページネーションをリセット
    prev_conference_key = "_submitter_matching_prev_conference"
    if st.session_state.get(prev_conference_key) != selected_conference_id:
        st.session_state[prev_conference_key] = selected_conference_id
        st.session_state["submitter_matching_page"] = 0

    # --- マッチ状態フィルタ ---
    match_filter = st.radio(
        "マッチ状態",
        options=["全て", "未マッチ", "マッチ済"],
        horizontal=True,
        key="submitter_matching_filter",
    )

    # --- データ取得 ---
    try:
        page_key = "submitter_matching_page"
        current_page = st.session_state.get(page_key, 0)

        page_data = presenter.load_proposals_page_data(
            filter_type="by_conference",
            conference_id=selected_conference_id,
            limit=PROPOSALS_PAGE_SIZE,
            offset=current_page * PROPOSALS_PAGE_SIZE,
        )
    except Exception as e:
        handle_ui_error(e, "議案データの読み込み")
        return

    proposals = page_data.result.proposals
    total_count = page_data.result.total_count
    submitters_map = page_data.submitters_map

    if not proposals:
        st.info("該当する議案がありません。")
        return

    # --- マッチ状態に基づくフィルタリングとサマリー計算 ---
    all_submitters: list[ProposalSubmitter] = []
    for subs in submitters_map.values():
        all_submitters.extend(subs)

    matched_count = sum(1 for s in all_submitters if s.is_matched())
    unmatched_count = len(all_submitters) - matched_count

    # フィルタ適用: 該当する議案のみ表示
    filtered_proposals = _filter_proposals_by_match_state(
        proposals, submitters_map, match_filter
    )

    # --- サマリーメトリクス ---
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("全提出者", f"{len(all_submitters)}件")
    col_m2.metric("マッチ済", f"{matched_count}件")
    col_m3.metric("未マッチ", f"{unmatched_count}件")

    # --- 候補リストを会議体単位で1回取得 ---
    try:
        candidates = presenter.get_submitter_candidates(selected_conference_id)
    except Exception as e:
        handle_ui_error(e, "提出者候補の読み込み")
        return

    politician_options: dict[str, int] = {p.name: p.id for p in candidates.politicians}
    pg_options: dict[str, int] = {
        pg.name: pg.id for pg in candidates.parliamentary_groups
    }

    # --- 一括操作 ---
    _render_bulk_actions(presenter, filtered_proposals, submitters_map)

    # --- 議案リスト表示 ---
    if not filtered_proposals:
        st.info("フィルタ条件に該当する議案がありません。")
    else:
        for proposal in filtered_proposals:
            _render_proposal_submitters(
                presenter,
                proposal,
                submitters_map.get(proposal.id or 0, []),
                page_data.politician_names,
                page_data.pg_names,
                politician_options,
                pg_options,
            )

    # --- ページネーション ---
    _render_pagination(page_key, current_page, total_count)


def _filter_proposals_by_match_state(
    proposals: list[Proposal],
    submitters_map: dict[int, list[ProposalSubmitter]],
    match_filter: str,
) -> list[Proposal]:
    """マッチ状態フィルタに基づいて議案をフィルタリングする."""
    if match_filter == "全て":
        return proposals

    filtered: list[Proposal] = []
    for p in proposals:
        pid = p.id or 0
        subs = submitters_map.get(pid, [])
        if not subs:
            if match_filter == "未マッチ":
                filtered.append(p)
            continue

        has_unmatched = any(not s.is_matched() for s in subs)
        if match_filter == "未マッチ" and has_unmatched:
            filtered.append(p)
        elif match_filter == "マッチ済" and not has_unmatched:
            filtered.append(p)

    return filtered


def _render_bulk_actions(
    presenter: ProposalPresenter,
    proposals: list[Proposal],
    submitters_map: dict[int, list[ProposalSubmitter]],
) -> None:
    """一括操作セクションを描画する."""
    # チェックボックスで選択された議案を収集
    selected_ids: list[int] = []
    for p in proposals:
        if p.id and st.session_state.get(f"select_proposal_{p.id}", False):
            selected_ids.append(p.id)

    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        run_matching = st.button(
            "選択した議案を自動マッチング",
            disabled=len(selected_ids) == 0,
            key="run_submitter_matching_btn",
        )
    with col_info:
        if selected_ids:
            st.caption(f"{len(selected_ids)}件の議案が選択されています")
        else:
            st.caption("マッチングする議案を選択してください")

    if run_matching and selected_ids:
        with st.spinner("自動マッチング実行中..."):
            try:
                result = presenter.analyze_submitters(selected_ids)
                if result.success:
                    st.success(result.message)
                    st.rerun()
                else:
                    st.error(result.message)
            except Exception as e:
                handle_ui_error(e, "自動マッチング")


def _render_proposal_submitters(
    presenter: ProposalPresenter,
    proposal: Proposal,
    submitters: list[ProposalSubmitter],
    politician_names: dict[int, str],
    pg_names: dict[int, str],
    politician_options: dict[str, int],
    pg_options: dict[str, int],
) -> None:
    """議案1件の提出者情報を描画する."""
    pid = proposal.id or 0
    title = proposal.title[:60] + "..." if len(proposal.title) > 60 else proposal.title

    # チェックボックス + 議案タイトル
    col_check, col_title = st.columns([0.5, 9.5])
    with col_check:
        st.checkbox(
            "選択",
            key=f"select_proposal_{pid}",
            label_visibility="collapsed",
        )
    with col_title:
        st.markdown(f"**議案ID: {pid}** | {title}")

    # 提出者一覧
    if not submitters:
        st.caption("　提出者情報なし")
    else:
        for sub in submitters:
            _render_single_submitter(
                presenter,
                sub,
                politician_names,
                pg_names,
                politician_options,
                pg_options,
            )

    st.divider()


def _render_single_submitter(
    presenter: ProposalPresenter,
    sub: ProposalSubmitter,
    politician_names: dict[int, str],
    pg_names: dict[int, str],
    politician_options: dict[str, int],
    pg_options: dict[str, int],
) -> None:
    """提出者1件を描画する."""
    sub_id = sub.id or 0
    type_val = sub.submitter_type.value if sub.submitter_type else "other"
    icon = SUBMITTER_TYPE_ICONS.get(type_val, "❓")
    type_label = SUBMITTER_TYPE_LABELS.get(type_val, "その他")
    raw = sub.raw_name or "（名前なし）"
    matched = sub.is_matched()

    if matched:
        # マッチ済みの表示
        matched_name = _get_matched_name(sub, politician_names, pg_names)
        st.markdown(f"　{icon} `{raw}` → **{matched_name}** ({type_label})")
    else:
        # 未マッチ: 手動修正UI
        st.markdown(f"　{icon} `{raw}` — 未マッチ ({type_label})")
        _render_manual_match_form(
            presenter, sub, sub_id, politician_options, pg_options
        )


def _get_matched_name(
    sub: ProposalSubmitter,
    politician_names: dict[int, str],
    pg_names: dict[int, str],
) -> str:
    """マッチ済み提出者の表示名を取得する."""
    if sub.submitter_type == SubmitterType.POLITICIAN and sub.politician_id:
        return politician_names.get(sub.politician_id, f"政治家ID:{sub.politician_id}")
    if (
        sub.submitter_type == SubmitterType.PARLIAMENTARY_GROUP
        and sub.parliamentary_group_id
    ):
        return pg_names.get(
            sub.parliamentary_group_id,
            f"会派ID:{sub.parliamentary_group_id}",
        )
    if sub.submitter_type in (SubmitterType.MAYOR, SubmitterType.COMMITTEE):
        return sub.raw_name or sub.submitter_type.name
    return sub.raw_name or "（不明）"


def _render_manual_match_form(
    presenter: ProposalPresenter,
    sub: ProposalSubmitter,
    sub_id: int,
    politician_options: dict[str, int],
    pg_options: dict[str, int],
) -> None:
    """未マッチ提出者の手動修正フォームを描画する."""
    col1, col2, col3 = st.columns([2, 3, 1])

    with col1:
        match_type = st.selectbox(
            "種別",
            options=["議員", "会派"],
            key=f"match_type_{sub_id}",
            label_visibility="collapsed",
        )

    with col2:
        base_options = politician_options if match_type == "議員" else pg_options
        options_list = ["選択してください"] + list(base_options.keys())
        selected = st.selectbox(
            "候補",
            options=options_list,
            key=f"match_candidate_{sub_id}",
            label_visibility="collapsed",
        )

    with col3:
        if st.button("設定", key=f"set_match_{sub_id}"):
            if selected == "選択してください":
                st.warning("候補を選択してください")
                return

            try:
                if match_type == "議員":
                    politician_id = politician_options[selected]
                    presenter.set_submitter(
                        proposal_id=sub.proposal_id,
                        submitter=sub.raw_name or "",
                        submitter_type=SubmitterType.POLITICIAN,
                        submitter_politician_id=politician_id,
                    )
                else:
                    pg_id = pg_options[selected]
                    presenter.set_submitter(
                        proposal_id=sub.proposal_id,
                        submitter=sub.raw_name or "",
                        submitter_type=SubmitterType.PARLIAMENTARY_GROUP,
                        submitter_parliamentary_group_id=pg_id,
                    )
                st.success("設定しました")
                st.rerun()
            except Exception as e:
                handle_ui_error(e, "提出者設定")


def _render_pagination(page_key: str, current_page: int, total_count: int) -> None:
    """ページネーションを描画する."""
    total_pages = max(1, (total_count + PROPOSALS_PAGE_SIZE - 1) // PROPOSALS_PAGE_SIZE)

    if total_pages <= 1:
        return

    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("← 前へ", disabled=current_page <= 0, key="submitter_prev"):
            st.session_state[page_key] = current_page - 1
            st.rerun()
    with col_info:
        st.caption(f"ページ {current_page + 1} / {total_pages}（全{total_count}件）")
    with col_next:
        if st.button(
            "次へ →",
            disabled=current_page >= total_pages - 1,
            key="submitter_next",
        ):
            st.session_state[page_key] = current_page + 1
            st.rerun()
