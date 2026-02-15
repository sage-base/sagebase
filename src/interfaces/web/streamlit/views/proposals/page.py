"""Main page for proposal management.

議案管理のメインページとタブ構成を定義します。
"""

import streamlit as st

from .tabs import (
    render_extracted_judges_tab,
    render_final_judges_tab,
    render_individual_vote_expansion_tab,
    render_parliamentary_group_judges_tab,
    render_proposals_tab,
    render_roll_call_override_tab,
)

from src.interfaces.web.streamlit.presenters.proposal_presenter import ProposalPresenter


def render_proposals_page() -> None:
    """Render the proposals management page."""
    st.title("議案管理")
    st.markdown("議案の情報を自動収集・管理します。")

    # Initialize presenter
    presenter = ProposalPresenter()

    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "議案管理",
            "LLM抽出結果",
            "確定賛否情報",
            "賛否",
            "個人投票展開",
            "記名投票上書き",
        ]
    )

    @st.fragment
    def _tab1_fragment() -> None:
        render_proposals_tab(presenter)

    @st.fragment
    def _tab2_fragment() -> None:
        render_extracted_judges_tab(presenter)

    @st.fragment
    def _tab3_fragment() -> None:
        render_final_judges_tab(presenter)

    @st.fragment
    def _tab4_fragment() -> None:
        render_parliamentary_group_judges_tab(presenter)

    @st.fragment
    def _tab5_fragment() -> None:
        render_individual_vote_expansion_tab(presenter)

    @st.fragment
    def _tab6_fragment() -> None:
        render_roll_call_override_tab(presenter)

    with tab1:
        _tab1_fragment()

    with tab2:
        _tab2_fragment()

    with tab3:
        _tab3_fragment()

    with tab4:
        _tab4_fragment()

    with tab5:
        _tab5_fragment()

    with tab6:
        _tab6_fragment()


def main() -> None:
    """Main entry point for the proposals page."""
    render_proposals_page()


if __name__ == "__main__":
    main()
