"""View for proposal management in Streamlit.

This module provides the UI layer for proposal management,
using the presenter pattern for business logic.
"""

import streamlit as st

from src.application.dtos.proposal_parliamentary_group_judge_dto import (
    ProposalParliamentaryGroupJudgeDTO,
)
from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_judge import ProposalJudge
from src.interfaces.web.streamlit.presenters.proposal_presenter import ProposalPresenter
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


def render_proposals_page() -> None:
    """Render the proposals management page."""
    st.title("議案管理")
    st.markdown("議案の情報を自動収集・管理します。")

    # Initialize presenter
    presenter = ProposalPresenter()

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        ["議案管理", "LLM抽出結果", "確定賛否情報", "会派賛否"]
    )

    with tab1:
        render_proposals_tab(presenter)

    with tab2:
        render_extracted_judges_tab(presenter)

    with tab3:
        render_final_judges_tab(presenter)

    with tab4:
        render_parliamentary_group_judges_tab(presenter)


# ========== Tab 1: Proposal Management ==========


def render_proposals_tab(presenter: ProposalPresenter) -> None:
    """Render the proposals management tab."""
    # Filter section
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        filter_options = {
            "すべて": "all",
            "状態別": "by_status",
            "会議別": "by_meeting",
        }
        selected_filter = st.selectbox(
            "表示フィルター", options=list(filter_options.keys()), index=0
        )
        filter_type = filter_options[selected_filter]

    # Additional filters based on selection
    status_filter = None
    meeting_filter = None

    if filter_type == "by_status":
        with col2:
            status_filter = st.text_input("状態", placeholder="例: 可決")

    elif filter_type == "by_meeting":
        with col2:
            meeting_filter = st.number_input("会議ID", min_value=1, step=1)

    # Load data
    try:
        result = presenter.load_data_filtered(
            filter_type=filter_type,
            status=status_filter,
            meeting_id=meeting_filter,
        )

        # Display statistics
        with col3:
            st.metric("議案数", result.statistics.total)

        # New proposal section
        render_new_proposal_form(presenter)

        # Scrape proposal section
        render_scrape_proposal_section(presenter)

        # Display proposals list
        if result.proposals:
            st.subheader("議案一覧")
            for proposal in result.proposals:
                render_proposal_row(presenter, proposal)
        else:
            st.info("表示する議案がありません。")

    except Exception as e:
        handle_ui_error(e, "議案一覧の読み込み")


def render_new_proposal_form(presenter: ProposalPresenter) -> None:
    """Render new proposal creation form."""
    with st.expander("📝 新規議案登録"):
        with st.form("new_proposal_form"):
            content = st.text_area("議案内容 *", placeholder="議案の内容を入力")

            col1, col2 = st.columns(2)
            with col1:
                proposal_number = st.text_input("議案番号", placeholder="例: 第1号議案")
                status = st.text_input("状態", placeholder="例: 審議中")
                submitter = st.text_input("提出者", placeholder="例: 市長")

            with col2:
                meeting_id = st.number_input("会議ID", min_value=0, value=0, step=1)
                submission_date = st.date_input("提出日")
                detail_url = st.text_input("詳細URL", placeholder="https://...")

            status_url = st.text_input("状態URL", placeholder="https://...")
            summary = st.text_area("要約", placeholder="議案の要約")

            submitted = st.form_submit_button("登録")

            if submitted:
                if not content:
                    st.error("議案内容は必須です")
                else:
                    try:
                        result = presenter.create(
                            content=content,
                            proposal_number=proposal_number or None,
                            status=status or None,
                            submitter=submitter or None,
                            meeting_id=meeting_id if meeting_id > 0 else None,
                            submission_date=(
                                submission_date.isoformat() if submission_date else None
                            ),
                            detail_url=detail_url or None,
                            status_url=status_url or None,
                            summary=summary or None,
                        )

                        if result.success:
                            st.success(result.message)
                            st.rerun()
                        else:
                            st.error(result.message)
                    except Exception as e:
                        handle_ui_error(e, "議案の登録")


def render_scrape_proposal_section(presenter: ProposalPresenter) -> None:
    """Render proposal scraping section."""
    with st.expander("🔍 議案情報の自動抽出"):
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

                            if result.proposal:
                                st.success("議案情報を抽出しました！")
                                st.json(
                                    {
                                        "議案番号": result.proposal.proposal_number,
                                        "内容": result.proposal.content[:100] + "...",
                                        "提出者": result.proposal.submitter,
                                        "提出日": result.proposal.submission_date,
                                    }
                                )
                                st.rerun()
                            else:
                                st.warning("議案情報を抽出できませんでした")
                        except Exception as e:
                            handle_ui_error(e, "議案の抽出")


def render_proposal_row(presenter: ProposalPresenter, proposal: Proposal) -> None:
    """Render a single proposal row."""
    with st.container():
        col1, col2 = st.columns([4, 1])

        with col1:
            st.markdown(f"**議案 #{proposal.id}**")
            if proposal.proposal_number:
                st.markdown(f"📋 {proposal.proposal_number}")
            st.markdown(f"📝 {proposal.content[:100]}...")

            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.markdown(f"**状態**: {proposal.status or '未設定'}")
            with col_info2:
                st.markdown(f"**提出者**: {proposal.submitter or '未設定'}")
            with col_info3:
                st.markdown(f"**提出日**: {proposal.submission_date or '未設定'}")

            if proposal.detail_url:
                st.markdown(f"🔗 [詳細URL]({proposal.detail_url})")
            if proposal.status_url:
                st.markdown(f"🔗 [状態URL]({proposal.status_url})")

        with col2:
            # Action buttons
            with st.popover("⚙️ 操作"):
                if st.button("編集", key=f"edit_proposal_{proposal.id}"):
                    if proposal.id is not None:
                        presenter.set_editing_mode(proposal.id)
                        st.rerun()

                if st.button(
                    "削除",
                    key=f"delete_proposal_{proposal.id}",
                    type="primary",
                ):
                    if st.button(
                        "本当に削除しますか？",
                        key=f"confirm_delete_{proposal.id}",
                    ):
                        try:
                            result = presenter.delete(proposal_id=proposal.id)
                            if result.success:
                                st.success(result.message)
                                st.rerun()
                            else:
                                st.error(result.message)
                        except Exception as e:
                            handle_ui_error(e, "議案の削除")

        st.divider()


# ========== Tab 2: Extracted Judges ==========


def render_extracted_judges_tab(presenter: ProposalPresenter) -> None:
    """Render the extracted judges tab."""
    st.subheader("LLM抽出結果")
    st.markdown("議案の賛否情報を自動抽出し、レビューします。")

    # Extract judges section
    render_extract_judges_section(presenter)

    # Filter section
    col1, col2 = st.columns([2, 1])

    with col1:
        proposal_id_filter = st.number_input(
            "議案IDでフィルター (0=全て)", min_value=0, value=0, step=1
        )

    with col2:
        status_options = ["すべて", "pending", "matched", "needs_review", "no_match"]
        status_filter = st.selectbox("ステータス", options=status_options, index=0)

    # Load extracted judges
    try:
        filter_id = proposal_id_filter if proposal_id_filter > 0 else None
        judges = presenter.load_extracted_judges(proposal_id=filter_id)

        # Filter by status if needed
        if status_filter != "すべて":
            judges = [j for j in judges if j.matching_status == status_filter]

        if judges:
            st.markdown(f"**抽出件数**: {len(judges)}件")

            # Batch operations
            render_batch_operations(presenter, judges)

            # Display judges
            for judge in judges:
                render_extracted_judge_row(presenter, judge)
        else:
            st.info("抽出結果がありません。")

    except Exception as e:
        handle_ui_error(e, "抽出結果の読み込み")


def render_extract_judges_section(presenter: ProposalPresenter) -> None:
    """Render judge extraction section."""
    with st.expander("🔍 賛否情報の自動抽出"):
        st.markdown("議案の状態URLから賛否情報を自動的に抽出します。")

        with st.form("extract_judges_form"):
            url = st.text_input("状態URL *", placeholder="https://...")
            proposal_id = st.number_input(
                "議案ID (オプション)", min_value=0, value=0, step=1
            )
            force = st.checkbox("既存データを上書き", value=False)

            submitted = st.form_submit_button("抽出実行")

            if submitted:
                if not url:
                    st.error("URLは必須です")
                else:
                    with st.spinner("賛否情報を抽出中..."):
                        try:
                            result = presenter.extract_judges(
                                url=url,
                                proposal_id=(proposal_id if proposal_id > 0 else None),
                                force=force,
                            )

                            st.success(
                                f"抽出完了！ {result.extracted_count}件の"
                                f"賛否情報を抽出しました。"
                            )
                            st.rerun()
                        except Exception as e:
                            handle_ui_error(e, "賛否情報の抽出")


def render_batch_operations(
    presenter: ProposalPresenter, judges: list[ExtractedProposalJudge]
) -> None:
    """Render batch operations for extracted judges."""
    st.markdown("### 一括操作")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔗 一括マッチング", type="primary"):
            with st.spinner("マッチング処理中..."):
                try:
                    # Get unique proposal IDs from judges
                    proposal_ids = {j.proposal_id for j in judges if j.proposal_id}

                    for prop_id in proposal_ids:
                        result = presenter.match_judges(proposal_id=prop_id)
                        st.info(f"議案ID {prop_id}: {result.matched_count}件マッチ")

                    st.success("マッチング完了")
                    st.rerun()
                except Exception as e:
                    handle_ui_error(e, "一括マッチング")

    with col2:
        if st.button("✅ 一括承認（matched のみ）"):
            with st.spinner("承認処理中..."):
                try:
                    # Get unique proposal IDs from matched judges
                    matched_judges = [
                        j for j in judges if j.matching_status == "matched"
                    ]
                    proposal_ids = {
                        j.proposal_id for j in matched_judges if j.proposal_id
                    }

                    for prop_id in proposal_ids:
                        result = presenter.create_judges_from_matched(
                            proposal_id=prop_id
                        )
                        st.info(f"議案ID {prop_id}: {result.created_count}件作成")

                    st.success("一括承認完了")
                    st.rerun()
                except Exception as e:
                    handle_ui_error(e, "一括承認")


def render_extracted_judge_row(
    presenter: ProposalPresenter, judge: ExtractedProposalJudge
) -> None:
    """Render a single extracted judge row."""
    with st.container():
        col1, col2 = st.columns([4, 1])

        with col1:
            # Status badge
            status_emoji = {
                "pending": "⏳",
                "matched": "✅",
                "needs_review": "⚠️",
                "no_match": "❌",
            }
            emoji = status_emoji.get(judge.matching_status or "pending", "❓")

            st.markdown(
                f"{emoji} **ID {judge.id}** - {judge.extracted_politician_name}"
            )

            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.markdown(f"**賛否**: {judge.extracted_judgment or '未設定'}")
            with col_info2:
                group_name = judge.extracted_parliamentary_group_name or "未設定"
                st.markdown(f"**議員団**: {group_name}")
            with col_info3:
                confidence = judge.matching_confidence
                if confidence:
                    st.markdown(f"**信頼度**: {confidence:.2f}")
                else:
                    st.markdown("**信頼度**: 未計算")

        with col2:
            if judge.matching_status == "matched":
                if st.button("✅ 承認", key=f"approve_{judge.id}"):
                    try:
                        # Create single judge
                        result = presenter.create_judges_from_matched(
                            proposal_id=judge.proposal_id
                        )
                        st.success(f"承認完了: {result.created_count}件作成")
                        st.rerun()
                    except Exception as e:
                        handle_ui_error(e, "承認処理")
            elif judge.matching_status == "pending":
                if st.button("🔗 マッチング", key=f"match_{judge.id}"):
                    try:
                        result = presenter.match_judges(proposal_id=judge.proposal_id)
                        st.success(f"マッチング完了: {result.matched_count}件")
                        st.rerun()
                    except Exception as e:
                        handle_ui_error(e, "マッチング処理")

        st.divider()


# ========== Tab 3: Final Judges ==========


def render_final_judges_tab(presenter: ProposalPresenter) -> None:
    """Render the final judges tab."""
    st.subheader("確定賛否情報")
    st.markdown("承認済みの最終的な賛否情報を管理します。")

    # Filter section
    col1, col2 = st.columns([2, 1])

    with col1:
        proposal_id_filter = st.number_input(
            "議案IDでフィルター (0=全て)",
            min_value=0,
            value=0,
            step=1,
            key="final_filter",
        )

    # Load final judges
    try:
        filter_id = proposal_id_filter if proposal_id_filter > 0 else None
        judges = presenter.load_proposal_judges(proposal_id=filter_id)

        with col2:
            st.metric("確定件数", len(judges))

        if judges:
            # Display statistics
            render_judge_statistics(judges)

            # Display judges list
            st.subheader("賛否一覧")
            for judge in judges:
                render_final_judge_row(presenter, judge)
        else:
            st.info("確定された賛否情報がありません。")

    except Exception as e:
        handle_ui_error(e, "確定賛否情報の読み込み")


def render_judge_statistics(judges: list[ProposalJudge]) -> None:
    """Render statistics for proposal judges."""
    # Count by vote
    vote_counts = {}
    for judge in judges:
        vote = judge.approve or "未設定"
        vote_counts[vote] = vote_counts.get(vote, 0) + 1

    st.markdown("### 統計情報")

    cols = st.columns(len(vote_counts))
    for i, (vote, count) in enumerate(vote_counts.items()):
        with cols[i]:
            st.metric(vote, count)


def render_final_judge_row(presenter: ProposalPresenter, judge: ProposalJudge) -> None:
    """Render a single final judge row."""
    with st.container():
        col1, col2 = st.columns([4, 1])

        with col1:
            st.markdown(f"**ID {judge.id}** - 政治家ID: {judge.politician_id}")

            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.markdown(f"**賛否**: {judge.approve or '未設定'}")
            with col_info2:
                # ProposalJudge doesn't have remarks field, skip it
                pass

        with col2:
            with st.popover("⚙️"):
                if st.button("削除", key=f"delete_judge_{judge.id}"):
                    # Note: Delete functionality would need to be added to presenter
                    st.warning("削除機能は未実装です")

        st.divider()


# ========== Tab 4: Parliamentary Group Judges (Issue #1007) ==========

# 賛否の選択肢
JUDGMENT_OPTIONS = ["賛成", "反対", "棄権", "欠席"]


def render_parliamentary_group_judges_tab(presenter: ProposalPresenter) -> None:
    """Render the parliamentary group judges tab."""
    st.subheader("会派賛否")
    st.markdown("会派単位の賛否情報を手動で登録・管理します。")

    # 議案選択
    try:
        proposals = presenter.load_data()

        if not proposals:
            st.info("議案がありません。先に議案を登録してください。")
            return

        # 議案プルダウン
        proposal_options = {
            f"#{p.id}: {p.proposal_number or p.content[:30]}...": p
            for p in proposals
            if p.id is not None
        }
        selected_label = st.selectbox(
            "議案を選択",
            options=list(proposal_options.keys()),
            key="pg_judge_proposal_select",
        )

        if not selected_label:
            return

        selected_proposal = proposal_options[selected_label]
        if selected_proposal.id is None:
            st.error("議案IDが取得できません")
            return

        proposal_id = selected_proposal.id

        # 議案情報の表示
        with st.expander("📋 議案詳細", expanded=False):
            st.markdown(
                f"**議案番号**: {selected_proposal.proposal_number or '未設定'}"
            )
            st.markdown(f"**内容**: {selected_proposal.content[:200]}...")
            st.markdown(f"**状態**: {selected_proposal.status or '未設定'}")
            if selected_proposal.meeting_id:
                st.markdown(f"**会議ID**: {selected_proposal.meeting_id}")

        # 会派賛否一覧
        render_parliamentary_group_judges_list(presenter, proposal_id)

        # 新規登録フォーム
        render_parliamentary_group_judge_form(presenter, proposal_id)

    except Exception as e:
        handle_ui_error(e, "会派賛否タブの読み込み")


def render_parliamentary_group_judges_list(
    presenter: ProposalPresenter, proposal_id: int
) -> None:
    """Render parliamentary group judges list for a proposal."""
    st.markdown("### 会派賛否一覧")

    try:
        judges = presenter.load_parliamentary_group_judges(proposal_id)

        if not judges:
            st.info("この議案に登録された会派賛否はありません。")
            return

        # 統計情報
        render_parliamentary_group_judge_statistics(judges)

        # 一覧表示
        for judge in judges:
            render_parliamentary_group_judge_row(presenter, judge)

    except Exception as e:
        handle_ui_error(e, "会派賛否一覧の読み込み")


def render_parliamentary_group_judge_statistics(
    judges: list[ProposalParliamentaryGroupJudgeDTO],
) -> None:
    """Render statistics for parliamentary group judges."""
    # 賛否ごとの集計
    judgment_counts: dict[str, int] = {}
    total_members = 0

    for judge in judges:
        judgment = judge.judgment
        judgment_counts[judgment] = judgment_counts.get(judgment, 0) + 1
        if judge.member_count:
            total_members += judge.member_count

    # 表示
    cols = st.columns(len(judgment_counts) + 1)

    for i, (judgment, count) in enumerate(judgment_counts.items()):
        with cols[i]:
            st.metric(judgment, f"{count}会派")

    with cols[-1]:
        st.metric("総人数", total_members if total_members > 0 else "-")


def render_parliamentary_group_judge_row(
    presenter: ProposalPresenter, judge: ProposalParliamentaryGroupJudgeDTO
) -> None:
    """Render a single parliamentary group judge row."""
    with st.container():
        col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 2, 1])

        with col1:
            st.markdown(f"**{judge.parliamentary_group_name}**")

        with col2:
            # 賛否に応じたバッジ
            judgment_emoji = {
                "賛成": "✅",
                "反対": "❌",
                "棄権": "⏸️",
                "欠席": "🚫",
            }
            emoji = judgment_emoji.get(judge.judgment, "❓")
            st.markdown(f"{emoji} {judge.judgment}")

        with col3:
            st.markdown(f"{judge.member_count or '-'}人")

        with col4:
            if judge.note:
                st.markdown(f"📝 {judge.note[:20]}...")
            else:
                st.markdown("-")

        with col5:
            with st.popover("⚙️ 操作"):
                # 編集フォーム
                st.markdown("**編集**")
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
                new_member_count = st.number_input(
                    "人数",
                    min_value=0,
                    value=judge.member_count or 0,
                    key=f"edit_member_count_{judge.id}",
                )
                new_note = st.text_input(
                    "備考",
                    value=judge.note or "",
                    key=f"edit_note_{judge.id}",
                )

                if st.button("更新", key=f"update_pg_judge_{judge.id}"):
                    try:
                        result = presenter.update_parliamentary_group_judge(
                            judge_id=judge.id,
                            judgment=new_judgment,
                            member_count=new_member_count
                            if new_member_count > 0
                            else None,
                            note=new_note if new_note else None,
                        )
                        if result.success:
                            st.success(result.message)
                            st.rerun()
                        else:
                            st.error(result.message)
                    except Exception as e:
                        handle_ui_error(e, "会派賛否の更新")

                st.divider()

                # 削除ボタン
                st.markdown("**削除**")
                if st.button(
                    "🗑️ 削除",
                    key=f"delete_pg_judge_{judge.id}",
                    type="primary",
                ):
                    # 確認ダイアログ
                    st.warning(
                        f"「{judge.parliamentary_group_name}」の賛否を削除します"
                    )
                    if st.button(
                        "本当に削除",
                        key=f"confirm_delete_pg_judge_{judge.id}",
                    ):
                        try:
                            result = presenter.delete_parliamentary_group_judge(
                                judge_id=judge.id
                            )
                            if result.success:
                                st.success(result.message)
                                st.rerun()
                            else:
                                st.error(result.message)
                        except Exception as e:
                            handle_ui_error(e, "会派賛否の削除")

        st.divider()


def render_parliamentary_group_judge_form(
    presenter: ProposalPresenter, proposal_id: int
) -> None:
    """Render form for creating new parliamentary group judge."""
    st.markdown("### 新規登録")

    # 会派一覧を取得
    try:
        parliamentary_groups = presenter.load_parliamentary_groups_for_proposal(
            proposal_id
        )

        if not parliamentary_groups:
            st.warning(
                "この議案に関連する会派が見つかりません。"
                "議案に会議が紐づいていない可能性があります。"
            )
            # 会派がない場合もフォームを表示（手動入力用）
            parliamentary_groups = []

        with st.form("new_parliamentary_group_judge_form"):
            col1, col2 = st.columns(2)

            with col1:
                # 会派選択
                if parliamentary_groups:
                    pg_options = {
                        pg.name: pg.id for pg in parliamentary_groups if pg.id
                    }
                    selected_pg_name = st.selectbox(
                        "会派 *",
                        options=list(pg_options.keys()),
                    )
                    selected_pg_id = (
                        pg_options.get(selected_pg_name) if selected_pg_name else None
                    )
                else:
                    st.info("会派が見つかりません")
                    selected_pg_id = None

                # 賛否選択
                judgment = st.selectbox("賛否 *", options=JUDGMENT_OPTIONS)

            with col2:
                # 人数入力
                member_count = st.number_input(
                    "人数（任意）",
                    min_value=0,
                    value=0,
                    help="賛否に参加した人数を入力",
                )

                # 備考入力
                note = st.text_input(
                    "備考（任意）",
                    placeholder="自由投票など特記事項",
                )

            submitted = st.form_submit_button("登録")

            if submitted:
                if not selected_pg_id:
                    st.error("会派を選択してください")
                elif not judgment:
                    st.error("賛否を選択してください")
                else:
                    try:
                        result = presenter.create_parliamentary_group_judge(
                            proposal_id=proposal_id,
                            parliamentary_group_id=selected_pg_id,
                            judgment=judgment,
                            member_count=member_count if member_count > 0 else None,
                            note=note if note else None,
                        )

                        if result.success:
                            st.success(result.message)
                            st.rerun()
                        else:
                            st.error(result.message)
                    except Exception as e:
                        handle_ui_error(e, "会派賛否の登録")

    except Exception as e:
        handle_ui_error(e, "会派情報の読み込み")


def main() -> None:
    """Main entry point for the proposals page."""
    render_proposals_page()


if __name__ == "__main__":
    main()
