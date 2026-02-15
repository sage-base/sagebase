"""Tab 3: 確定賛否情報タブ.

承認済みの最終的な賛否情報を管理する機能を提供します。
"""

import streamlit as st

from src.domain.entities.proposal_judge import ProposalJudge
from src.interfaces.web.streamlit.presenters.proposal_presenter import ProposalPresenter
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


def render_final_judges_tab(presenter: ProposalPresenter) -> None:
    """Render the final judges tab."""
    st.subheader("確定賛否情報")
    st.markdown("承認済みの最終的な賛否情報を管理します。")

    # Filter section
    col1, col2 = st.columns([2, 1])

    with col1:
        proposal_id_filter = st.number_input(
            "議案IDでフィルター",
            min_value=1,
            value=1,
            step=1,
            key="final_filter",
        )

    if not proposal_id_filter:
        st.info("表示する議案IDを入力してください。")
        return

    # Load final judges
    try:
        judges = presenter.load_proposal_judges(proposal_id=int(proposal_id_filter))

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
    vote_counts: dict[str, int] = {}
    for judge in judges:
        vote = judge.approve or "未設定"
        vote_counts[vote] = vote_counts.get(vote, 0) + 1

    st.markdown("### 統計情報")

    if vote_counts:
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
            if st.button("削除", key=f"delete_judge_{judge.id}"):
                # Note: Delete functionality would need to be added to presenter
                st.warning("削除機能は未実装です")

        st.divider()
