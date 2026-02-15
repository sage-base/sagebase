"""Tab 6: 記名投票上書きタブ.

記名投票の実データで個人投票データを上書きし、造反を検出する機能を提供します。
"""

import pandas as pd
import streamlit as st

from src.application.dtos.override_individual_judge_dto import IndividualVoteInputItem
from src.interfaces.web.streamlit.presenters.proposal_presenter import ProposalPresenter
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


def render_roll_call_override_tab(presenter: ProposalPresenter) -> None:
    """記名投票による個人データ上書きタブ."""
    st.subheader("記名投票上書き")
    st.markdown("記名投票の実データで個人投票データを上書きし、造反を検出します。")

    try:
        proposal_id = st.number_input(
            "議案ID",
            min_value=1,
            step=1,
            key="roll_call_proposal_id_input",
        )

        if not proposal_id:
            st.info("対象の議案IDを入力してください。")
            return

        selected_proposal = presenter.load_proposal_by_id(int(proposal_id))
        if selected_proposal is None:
            st.warning(f"議案ID {proposal_id} が見つかりません。")
            return

        with st.expander("議案詳細", expanded=False):
            st.markdown(f"**タイトル**: {selected_proposal.title}")
            if selected_proposal.meeting_id:
                st.markdown(f"**会議ID**: {selected_proposal.meeting_id}")

        input_method = st.radio(
            "入力方法",
            ["CSVインポート", "手動入力"],
            key="roll_call_input_method",
            horizontal=True,
        )

        votes: list[IndividualVoteInputItem] = []

        if input_method == "CSVインポート":
            st.markdown("CSVフォーマット: `politician_id,賛否` (1行1投票)")
            uploaded = st.file_uploader(
                "CSVファイル",
                type=["csv"],
                key="roll_call_csv_upload",
            )
            if uploaded is not None:
                csv_content = uploaded.getvalue().decode("utf-8")
                try:
                    votes = presenter.parse_roll_call_csv(csv_content)
                    st.success(f"{len(votes)}件の投票データを読み込みました。")
                    preview_data = [
                        {"議員ID": v.politician_id, "賛否": v.approve} for v in votes
                    ]
                    st.dataframe(pd.DataFrame(preview_data), hide_index=True)
                except ValueError as e:
                    st.error(f"CSV解析エラー: {e}")
                    return

        else:
            st.markdown("議員IDと賛否を入力してください。")
            manual_input = st.text_area(
                "投票データ (1行に `議員ID,賛否`)",
                height=200,
                key="roll_call_manual_input",
                placeholder="501,賛成\n502,反対\n503,棄権",
            )
            if manual_input.strip():
                try:
                    votes = presenter.parse_roll_call_csv(manual_input)
                    st.info(f"{len(votes)}件の投票データを認識しました。")
                except ValueError as e:
                    st.error(f"入力エラー: {e}")
                    return

        if not votes:
            return

        if st.button("上書き実行", type="primary", key="roll_call_execute_btn"):
            with st.spinner("記名投票データで上書き中..."):
                result = presenter.override_individual_judges(
                    proposal_id=int(proposal_id),
                    votes=votes,
                )

            if result.success:
                st.success("上書きが完了しました。")
            else:
                st.error("上書き中にエラーが発生しました。")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("新規作成", result.judges_created)
            with col2:
                st.metric("更新", result.judges_updated)
            with col3:
                st.metric("スキップ", result.judges_skipped)

            if result.errors:
                st.markdown("### エラー")
                for err in result.errors:
                    st.error(err)

            if result.defections:
                st.markdown("### 造反一覧")
                defection_data = [
                    {
                        "議員ID": d.politician_id,
                        "議員名": d.politician_name,
                        "個人投票": d.individual_vote,
                        "会派方針": d.group_judgment,
                        "会派名": d.parliamentary_group_name,
                    }
                    for d in result.defections
                ]
                st.dataframe(pd.DataFrame(defection_data), hide_index=True)
            else:
                st.info("造反はありませんでした。")

        st.markdown("---")
        st.markdown("### 造反検出（既存データ）")
        if st.button("造反を検出", key="roll_call_detect_defections_btn"):
            with st.spinner("造反を検出中..."):
                defections = presenter.detect_defections(int(proposal_id))

            if defections:
                st.warning(f"{len(defections)}件の造反が検出されました。")
                defection_data = [
                    {
                        "議員ID": d.politician_id,
                        "議員名": d.politician_name,
                        "個人投票": d.individual_vote,
                        "会派方針": d.group_judgment,
                        "会派名": d.parliamentary_group_name,
                    }
                    for d in defections
                ]
                st.dataframe(pd.DataFrame(defection_data), hide_index=True)
            else:
                st.info("造反は検出されませんでした。")

    except Exception as e:
        handle_ui_error(e, "記名投票上書きタブの読み込み")
