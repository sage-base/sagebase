"""Tab 4: 賛否タブ.

会派単位の賛否情報を手動で登録・管理する機能を提供します。
"""

import streamlit as st

from ..constants import JUDGMENT_OPTIONS
from .parliamentary_group_judge_form import render_parliamentary_group_judge_form

from src.application.dtos.proposal_parliamentary_group_judge_dto import (
    ProposalParliamentaryGroupJudgeDTO,
)
from src.interfaces.web.streamlit.presenters.proposal_presenter import ProposalPresenter
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


def render_parliamentary_group_judges_tab(presenter: ProposalPresenter) -> None:
    """Render the parliamentary group judges tab."""
    st.subheader("賛否")
    st.markdown("会派単位の賛否情報を手動で登録・管理します。")

    # 議案ID入力（全件ロードを避けるためnumber_inputを使用）
    try:
        proposal_id = st.number_input(
            "議案ID",
            min_value=1,
            step=1,
            key="pg_judge_proposal_id_input",
        )

        if not proposal_id:
            st.info("賛否を登録する議案IDを入力してください。")
            return

        selected_proposal = presenter.load_proposal_by_id(int(proposal_id))
        if selected_proposal is None:
            st.warning(f"議案ID {proposal_id} が見つかりません。")
            return

        # 議案情報の表示
        with st.expander("📋 議案詳細", expanded=False):
            st.markdown(f"**タイトル**: {selected_proposal.title}")
            if selected_proposal.meeting_id:
                st.markdown(f"**会議ID**: {selected_proposal.meeting_id}")
            if selected_proposal.conference_id:
                st.markdown(f"**会議体ID**: {selected_proposal.conference_id}")

        # 賛否一覧
        render_parliamentary_group_judges_list(presenter, int(proposal_id))

        # 新規登録フォーム
        render_parliamentary_group_judge_form(presenter, int(proposal_id))

    except Exception as e:
        handle_ui_error(e, "賛否タブの読み込み")


def render_parliamentary_group_judges_list(
    presenter: ProposalPresenter, proposal_id: int
) -> None:
    """Render parliamentary group judges list for a proposal."""
    st.markdown("### 賛否一覧")

    try:
        judges = presenter.load_parliamentary_group_judges(proposal_id)

        if not judges:
            st.info("この議案に登録された賛否はありません。")
            return

        # 統計情報
        render_parliamentary_group_judge_statistics(judges)

        # 一覧表示
        for judge in judges:
            render_parliamentary_group_judge_row(presenter, judge, proposal_id)

    except Exception as e:
        handle_ui_error(e, "賛否一覧の読み込み")


def render_parliamentary_group_judge_statistics(
    judges: list[ProposalParliamentaryGroupJudgeDTO],
) -> None:
    """Render statistics for parliamentary group judges."""
    # 賛否ごとの集計（会派数/政治家数を正しくカウント）
    judgment_pg_counts: dict[str, int] = {}  # 会派数
    judgment_pol_counts: dict[str, int] = {}  # 政治家数
    total_members = 0

    for judge in judges:
        judgment = judge.judgment
        if judge.is_parliamentary_group_judge():
            # 会派賛否: 紐づく会派の数をカウント
            pg_count = len(judge.parliamentary_group_ids)
            judgment_pg_counts[judgment] = (
                judgment_pg_counts.get(judgment, 0) + pg_count
            )
        else:
            # 政治家賛否: 紐づく政治家の数をカウント
            pol_count = len(judge.politician_ids)
            judgment_pol_counts[judgment] = (
                judgment_pol_counts.get(judgment, 0) + pol_count
            )
        if judge.member_count:
            total_members += judge.member_count

    # 全ての判定種別を取得
    all_judgments = set(judgment_pg_counts.keys()) | set(judgment_pol_counts.keys())

    if not all_judgments:
        return

    # 統計を横並びで表示
    stats_parts = []
    for judgment in sorted(all_judgments):
        pg_count = judgment_pg_counts.get(judgment, 0)
        pol_count = judgment_pol_counts.get(judgment, 0)
        count_parts = []
        if pg_count > 0:
            count_parts.append(f"{pg_count}会派")
        if pol_count > 0:
            count_parts.append(f"{pol_count}名")
        count_str = " / ".join(count_parts) if count_parts else "-"
        stats_parts.append(f"**{judgment}**: {count_str}")

    if total_members > 0:
        stats_parts.append(f"**総人数**: {total_members}人")

    st.markdown(" ｜ ".join(stats_parts))


def render_parliamentary_group_judge_row(
    presenter: ProposalPresenter,
    judge: ProposalParliamentaryGroupJudgeDTO,
    proposal_id: int,
) -> None:
    """Render a single parliamentary group / politician judge row.

    Many-to-Many構造対応: 複数の会派名・政治家名をカンマ区切りで表示。
    """
    is_parliamentary_group = judge.is_parliamentary_group_judge()

    with st.container():
        col1, col2, col3, col4, col5, col6 = st.columns([1, 3, 2, 1, 2, 1])

        with col1:
            if is_parliamentary_group:
                st.markdown("🏛️")
            else:
                st.markdown("👤")

        with col2:
            if is_parliamentary_group:
                # 複数の会派名をカンマ区切りで結合
                if judge.parliamentary_group_names:
                    name_display = ", ".join(judge.parliamentary_group_names)
                else:
                    name_display = "（不明）"
                st.markdown(f"**{name_display}**")
            else:
                # 複数の政治家名をカンマ区切りで結合
                if judge.politician_names:
                    name_display = ", ".join(judge.politician_names)
                else:
                    name_display = "（不明）"
                st.markdown(f"**{name_display}**")

        with col3:
            judgment_emoji = {
                "賛成": "✅",
                "反対": "❌",
                "棄権": "⏸️",
                "欠席": "🚫",
            }
            emoji = judgment_emoji.get(judge.judgment, "❓")
            st.markdown(f"{emoji} {judge.judgment}")

        with col4:
            if is_parliamentary_group:
                st.markdown(f"{judge.member_count or '-'}人")
            else:
                st.markdown("-")

        with col5:
            if judge.note:
                st.markdown(f"📝 {judge.note[:20]}...")
            else:
                st.markdown("-")

        with col6:
            with st.popover("⚙️ 操作"):
                st.markdown("**編集**")

                # 会派/政治家の選択
                new_pg_ids: list[int] = []
                new_politician_ids: list[int] = []
                if is_parliamentary_group:
                    parliamentary_groups = (
                        presenter.load_parliamentary_groups_for_proposal(proposal_id)
                    )
                    if parliamentary_groups:
                        pg_options = {
                            f"{pg.name} (ID: {pg.id})": pg.id
                            for pg in parliamentary_groups
                            if pg.id
                        }
                        # 現在選択されている会派を特定
                        current_selections = [
                            name
                            for name, pid in pg_options.items()
                            if pid in judge.parliamentary_group_ids
                        ]
                        selected_pg_names = st.multiselect(
                            "会派",
                            options=list(pg_options.keys()),
                            default=current_selections,
                            key=f"edit_pg_{judge.id}",
                        )
                        new_pg_ids = [pg_options[name] for name in selected_pg_names]
                    else:
                        st.info("会派が見つかりません")
                else:
                    politicians = presenter.load_politicians_for_proposal(proposal_id)
                    if politicians:
                        politician_options = {
                            f"{p.name} (ID: {p.id})": p.id for p in politicians if p.id
                        }
                        # 現在選択されている政治家を特定
                        current_selections = [
                            name
                            for name, pid in politician_options.items()
                            if pid in judge.politician_ids
                        ]
                        selected_politician_names = st.multiselect(
                            "政治家",
                            options=list(politician_options.keys()),
                            default=current_selections,
                            key=f"edit_politician_{judge.id}",
                        )
                        new_politician_ids = [
                            politician_options[name]
                            for name in selected_politician_names
                        ]
                    else:
                        st.info("政治家が見つかりません")

                new_judgment = st.selectbox(
                    "賛否",
                    options=JUDGMENT_OPTIONS,
                    index=(
                        JUDGMENT_OPTIONS.index(judge.judgment)
                        if judge.judgment in JUDGMENT_OPTIONS
                        else 0
                    ),
                    key=f"edit_judgment_{judge.id}",
                )
                if is_parliamentary_group:
                    new_member_count = st.number_input(
                        "人数",
                        min_value=0,
                        value=judge.member_count or 0,
                        key=f"edit_member_count_{judge.id}",
                    )
                else:
                    new_member_count = 0
                new_note = st.text_input(
                    "備考",
                    value=judge.note or "",
                    key=f"edit_note_{judge.id}",
                )

                if st.button("更新", key=f"update_pg_judge_{judge.id}"):
                    # 会派/政治家の選択チェック
                    if is_parliamentary_group and not new_pg_ids:
                        st.error("会派を選択してください")
                    elif not is_parliamentary_group and not new_politician_ids:
                        st.error("政治家を選択してください")
                    else:
                        try:
                            result = presenter.update_parliamentary_group_judge(
                                judge_id=judge.id,
                                judgment=new_judgment,
                                member_count=new_member_count
                                if new_member_count > 0
                                else None,
                                note=new_note if new_note else None,
                                parliamentary_group_ids=new_pg_ids
                                if is_parliamentary_group
                                else None,
                                politician_ids=new_politician_ids
                                if not is_parliamentary_group
                                else None,
                            )
                            if result.success:
                                st.success(result.message)
                                st.rerun()
                            else:
                                st.error(result.message)
                        except Exception as e:
                            handle_ui_error(e, "賛否の更新")

                st.divider()

                # 削除ボタン
                st.markdown("**削除**")
                delete_key = f"confirm_delete_pg_judge_{judge.id}"
                if st.button(
                    "🗑️ 削除",
                    key=f"delete_pg_judge_{judge.id}",
                    type="primary",
                ):
                    st.session_state[delete_key] = True

                # 削除確認
                if st.session_state.get(delete_key, False):
                    # 会派/政治家の名前を適切に表示（複数対応）
                    if judge.is_parliamentary_group_judge():
                        if judge.parliamentary_group_names:
                            display_name = ", ".join(judge.parliamentary_group_names)
                        else:
                            display_name = "（不明）"
                    else:
                        if judge.politician_names:
                            display_name = ", ".join(judge.politician_names)
                        else:
                            display_name = "（不明）"
                    st.warning(f"「{display_name}」の賛否を削除しますか？")
                    col_del1, col_del2 = st.columns(2)
                    with col_del1:
                        if st.button(
                            "削除する",
                            key=f"confirm_yes_pg_judge_{judge.id}",
                            type="primary",
                        ):
                            try:
                                result = presenter.delete_parliamentary_group_judge(
                                    judge_id=judge.id
                                )
                                if result.success:
                                    st.success(result.message)
                                    del st.session_state[delete_key]
                                    st.rerun()
                                else:
                                    st.error(result.message)
                            except Exception as e:
                                handle_ui_error(e, "賛否の削除")
                    with col_del2:
                        if st.button(
                            "キャンセル",
                            key=f"confirm_no_pg_judge_{judge.id}",
                        ):
                            del st.session_state[delete_key]
                            st.rerun()

        st.divider()
