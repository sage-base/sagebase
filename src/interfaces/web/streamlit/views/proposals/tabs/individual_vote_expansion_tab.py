"""Tab 5: 個人投票展開タブ.

会派賛否データから個人投票データを展開する機能を提供します。
"""

import streamlit as st

from src.application.dtos.expand_group_judges_dto import ExpandGroupJudgesResultDTO
from src.application.dtos.expand_group_judges_preview_dto import (
    ExpandGroupJudgesPreviewDTO,
)
from src.interfaces.web.streamlit.presenters.proposal_presenter import ProposalPresenter
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


def render_individual_vote_expansion_tab(presenter: ProposalPresenter) -> None:
    """会派賛否から個人投票データへの展開タブ."""
    st.subheader("個人投票展開")
    st.markdown("会派賛否データから個人投票データを展開します。")

    try:
        proposal_id = st.number_input(
            "議案ID",
            min_value=1,
            step=1,
            key="expand_proposal_id_input",
        )

        if not proposal_id:
            st.info("展開する議案IDを入力してください。")
            return

        selected_proposal = presenter.load_proposal_by_id(int(proposal_id))
        if selected_proposal is None:
            st.warning(f"議案ID {proposal_id} が見つかりません。")
            return

        with st.expander("議案詳細", expanded=False):
            st.markdown(f"**タイトル**: {selected_proposal.title}")
            if selected_proposal.meeting_id:
                st.markdown(f"**会議ID**: {selected_proposal.meeting_id}")
            if selected_proposal.conference_id:
                st.markdown(f"**会議体ID**: {selected_proposal.conference_id}")

        judges = presenter.load_parliamentary_group_judges(int(proposal_id))
        pg_judges = [j for j in judges if j.is_parliamentary_group_judge()]

        if not pg_judges:
            st.info("この議案に登録された会派賛否はありません。")
            return

        st.markdown("### 会派賛否一覧")

        col_all, col_none = st.columns(2)
        with col_all:
            select_all = st.button("全選択", key="expand_select_all")
        with col_none:
            deselect_all = st.button("全解除", key="expand_deselect_all")

        if select_all:
            for j in pg_judges:
                st.session_state[f"expand_check_{j.id}"] = True
        if deselect_all:
            for j in pg_judges:
                st.session_state[f"expand_check_{j.id}"] = False

        selected_ids: list[int] = []
        for j in pg_judges:
            default_checked = st.session_state.get(f"expand_check_{j.id}", False)
            pg_name_display = (
                ", ".join(j.parliamentary_group_names)
                if j.parliamentary_group_names
                else "（不明）"
            )
            judgment_emoji = {
                "賛成": "✅",
                "反対": "❌",
                "棄権": "⏸️",
                "欠席": "🚫",
            }.get(j.judgment, "❓")
            count = j.member_count or "-"
            label = f"{pg_name_display} - {judgment_emoji} {j.judgment} ({count}人)"
            checked = st.checkbox(
                label,
                value=default_checked,
                key=f"expand_check_{j.id}",
            )
            if checked:
                selected_ids.append(j.id)

        if not selected_ids:
            st.info("展開する会派賛否を選択してください。")
            return

        st.markdown(f"**選択中**: {len(selected_ids)}件")

        if st.button("プレビュー", type="primary", key="expand_preview_btn"):
            with st.spinner("プレビューを生成中..."):
                preview = presenter.preview_group_judges_expansion(selected_ids)
                st.session_state["expand_preview_result"] = preview

        preview_result: ExpandGroupJudgesPreviewDTO | None = st.session_state.get(
            "expand_preview_result"
        )
        if preview_result is not None:
            _render_expansion_preview(preview_result)

            st.markdown("---")
            force_overwrite = st.checkbox(
                "既存の個人投票データを上書きする",
                value=False,
                key="expand_force_overwrite",
            )

            if st.button("展開実行", type="primary", key="expand_execute_btn"):
                with st.spinner("展開処理中..."):
                    result = presenter.expand_group_judges_to_individual(
                        group_judge_ids=selected_ids,
                        force_overwrite=force_overwrite,
                    )

                if result.success:
                    st.success("展開が完了しました")
                else:
                    st.error("展開中にエラーが発生しました")

                _render_expansion_result_summary(result)

                st.session_state.pop("expand_preview_result", None)

    except Exception as e:
        handle_ui_error(e, "個人投票展開タブの読み込み")


def _render_expansion_preview(preview: ExpandGroupJudgesPreviewDTO) -> None:
    """展開プレビュー結果を表示する."""
    if preview.errors:
        for err in preview.errors:
            st.error(err)

    st.markdown(
        f"**展開対象**: {preview.total_members}人 "
        f"（うち既存投票あり: {preview.total_existing_votes}人）"
    )

    for item in preview.items:
        pg_label = ", ".join(item.parliamentary_group_names)
        with st.expander(
            f"{pg_label} - {item.judgment} ({len(item.members)}人)",
            expanded=False,
        ):
            if item.errors:
                for err in item.errors:
                    st.warning(err)

            if not item.members:
                st.info("該当するメンバーがいません。")
                continue

            lines: list[str] = []
            for m in item.members:
                conflict = " ⚠️ 既存投票あり" if m.has_existing_vote else ""
                lines.append(f"- {m.politician_name} (ID: {m.politician_id}){conflict}")
            st.markdown("\n".join(lines))


def _render_expansion_result_summary(
    result: ExpandGroupJudgesResultDTO,
) -> None:
    """展開結果サマリーを表示する."""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("作成", result.total_judges_created)
    with col2:
        st.metric("スキップ", result.total_judges_skipped)
    with col3:
        st.metric("上書き", result.total_judges_overwritten)
    with col4:
        st.metric("日付不明", result.skipped_no_meeting_date)

    if result.errors:
        st.markdown("### エラー")
        for err in result.errors:
            st.error(err)
