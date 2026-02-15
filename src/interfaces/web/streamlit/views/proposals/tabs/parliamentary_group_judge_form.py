"""Tab 4: 会派賛否 新規登録フォーム.

会派単位・政治家単位の賛否情報を新規登録するフォームを提供します。
"""

import streamlit as st

from ..constants import JUDGMENT_OPTIONS

from src.interfaces.web.streamlit.presenters.proposal_presenter import ProposalPresenter
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


def render_parliamentary_group_judge_form(
    presenter: ProposalPresenter, proposal_id: int
) -> None:
    """Render form for creating new parliamentary group / politician judge."""
    st.markdown("### 新規登録")

    try:
        parliamentary_groups = presenter.load_parliamentary_groups_for_proposal(
            proposal_id
        )
        politicians = presenter.load_politicians_for_proposal(proposal_id)

        if not parliamentary_groups and not politicians:
            st.warning(
                "この議案に関連する会派・政治家が見つかりません。"
                "議案に会議が紐づいていない可能性があります。"
            )

        judge_type = st.radio(
            "賛否種別",
            options=["会派単位", "政治家単位"],
            horizontal=True,
            key="new_judge_type_radio",
        )
        is_parliamentary_group = judge_type == "会派単位"

        with st.form("new_parliamentary_group_judge_form"):
            col1, col2 = st.columns(2)

            with col1:
                if is_parliamentary_group:
                    if parliamentary_groups:
                        pg_options = {
                            f"{pg.name} (ID: {pg.id})": pg.id
                            for pg in parliamentary_groups
                            if pg.id
                        }
                        selected_pg_names = st.multiselect(
                            "会派 *（複数選択可能）",
                            options=list(pg_options.keys()),
                        )
                        selected_pg_ids = [
                            pg_options[name] for name in selected_pg_names
                        ]
                    else:
                        st.info("会派が見つかりません")
                        selected_pg_ids = []
                    selected_politician_ids = []
                else:
                    if politicians:
                        politician_options = {
                            f"{p.name} (ID: {p.id})": p.id for p in politicians if p.id
                        }
                        selected_politician_names = st.multiselect(
                            "政治家 *（複数選択可能）",
                            options=list(politician_options.keys()),
                        )
                        selected_politician_ids = [
                            politician_options[name]
                            for name in selected_politician_names
                        ]
                    else:
                        st.info("政治家が見つかりません")
                        selected_politician_ids = []
                    selected_pg_ids = []

                judgment = st.selectbox("賛否 *", options=JUDGMENT_OPTIONS)

            with col2:
                if is_parliamentary_group:
                    member_count = st.number_input(
                        "人数（任意）",
                        min_value=0,
                        value=0,
                        help="賛否に参加した人数を入力",
                    )
                else:
                    member_count = 0

                note = st.text_input(
                    "備考（任意）",
                    placeholder="自由投票など特記事項",
                )

            submitted = st.form_submit_button("登録")

            if submitted:
                if is_parliamentary_group and not selected_pg_ids:
                    st.error("会派を選択してください")
                elif not is_parliamentary_group and not selected_politician_ids:
                    st.error("政治家を選択してください")
                elif not judgment:
                    st.error("賛否を選択してください")
                else:
                    try:
                        if is_parliamentary_group:
                            # 会派単位: Many-to-Many構造で一括登録
                            result = presenter.create_parliamentary_group_judge(
                                proposal_id=proposal_id,
                                judgment=judgment,
                                judge_type="parliamentary_group",
                                parliamentary_group_ids=selected_pg_ids,
                                politician_ids=None,
                                member_count=(
                                    member_count if member_count > 0 else None
                                ),
                                note=note if note else None,
                            )
                            if result.success:
                                st.success("賛否情報を登録しました")
                                st.rerun()
                            else:
                                st.error(result.message)
                        else:
                            # 政治家単位: Many-to-Many構造で一括登録
                            result = presenter.create_parliamentary_group_judge(
                                proposal_id=proposal_id,
                                judgment=judgment,
                                judge_type="politician",
                                parliamentary_group_ids=None,
                                politician_ids=selected_politician_ids,
                                member_count=None,
                                note=note if note else None,
                            )
                            if result.success:
                                st.success("賛否情報を登録しました")
                                st.rerun()
                            else:
                                st.error(result.message)
                    except Exception as e:
                        handle_ui_error(e, "賛否情報の登録")

    except Exception as e:
        handle_ui_error(e, "会派・政治家情報の読み込み")
