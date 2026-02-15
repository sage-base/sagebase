"""Tab 2: LLM抽出結果タブ.

議案の賛否情報を自動抽出し、レビューする機能を提供します。
"""

import streamlit as st

from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.interfaces.web.streamlit.presenters.proposal_presenter import ProposalPresenter
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


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
            "議案IDでフィルター", min_value=1, value=1, step=1
        )

    with col2:
        status_options = ["すべて", "pending", "matched", "needs_review", "no_match"]
        status_filter = st.selectbox("ステータス", options=status_options, index=0)

    if not proposal_id_filter:
        st.info("表示する議案IDを入力してください。")
        return

    # Load extracted judges
    try:
        judges = presenter.load_extracted_judges(proposal_id=int(proposal_id_filter))

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
    with st.expander("賛否情報の自動抽出"):
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
        if st.button("一括マッチング", type="primary"):
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
        if st.button("一括承認（matched のみ）"):
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
                "pending": "?",
                "matched": "OK",
                "needs_review": "!",
                "no_match": "X",
            }
            emoji = status_emoji.get(judge.matching_status or "pending", "?")

            st.markdown(
                f"[{emoji}] **ID {judge.id}** - {judge.extracted_politician_name}"
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
                if st.button("承認", key=f"approve_{judge.id}"):
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
                if st.button("マッチング", key=f"match_{judge.id}"):
                    try:
                        result = presenter.match_judges(proposal_id=judge.proposal_id)
                        st.success(f"マッチング完了: {result.matched_count}件")
                        st.rerun()
                    except Exception as e:
                        handle_ui_error(e, "マッチング処理")

        st.divider()
