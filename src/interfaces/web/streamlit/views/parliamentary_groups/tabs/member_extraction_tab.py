"""Member extraction tab for parliamentary groups.

議員団メンバー抽出タブのUI実装を提供します。
"""

from datetime import date
from typing import Any, cast

import pandas as pd
import streamlit as st

from src.interfaces.web.streamlit.components import japanese_era_date_input
from src.interfaces.web.streamlit.presenters.parliamentary_group_presenter import (
    ParliamentaryGroupPresenter,
)


def render_member_extraction_tab(presenter: ParliamentaryGroupPresenter) -> None:
    """Render the member extraction tab.

    議員団メンバーの抽出タブをレンダリングします。
    URLからの自動抽出、LangGraphエージェントによる抽出などの機能を提供します。

    Args:
        presenter: 議員団プレゼンター
    """
    st.subheader("議員団メンバーの抽出")
    st.markdown("議員団のURLから所属議員を自動的に抽出し、メンバーシップを作成します")

    # Get parliamentary groups with URLs
    groups = presenter.load_data()
    groups_with_url = [g for g in groups if g.url]

    if not groups_with_url:
        st.info(
            "URLが設定されている議員団がありません。先に議員団のURLを設定してください。"
        )
        return

    # Get governing bodies for display
    governing_bodies = presenter.get_all_governing_bodies()

    # Select parliamentary group
    group_options = []
    group_map = {}
    for group in groups_with_url:
        gb = next(
            (g for g in governing_bodies if g.id == group.governing_body_id), None
        )
        gb_name = gb.name if gb else "不明"
        display_name = f"{group.name} ({gb_name})"
        group_options.append(display_name)
        group_map[display_name] = group

    selected_group_display = st.selectbox(
        "抽出対象の議員団を選択", group_options, key="extract_group_select"
    )
    selected_group = group_map[selected_group_display]

    # Get extraction summary for selected group
    extraction_summary = presenter.get_extraction_summary(selected_group.id)

    # Display current information
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**議員団URL:** {selected_group.url}")
    with col2:
        st.info(f"**抽出済みメンバー数:** {extraction_summary['total']}名")

    # Display previously extracted members if they exist
    if extraction_summary["total"] > 0:
        _render_extracted_members_summary(presenter, selected_group, extraction_summary)

    # Extraction settings
    _render_extraction_settings(presenter, selected_group)


def _render_extracted_members_summary(
    presenter: ParliamentaryGroupPresenter,
    selected_group: object,
    extraction_summary: dict[str, Any],
) -> None:
    """Render previously extracted members summary.

    Args:
        presenter: 議員団プレゼンター
        selected_group: 選択された議員団
        extraction_summary: 抽出サマリー
    """
    st.markdown("### 抽出済みメンバー一覧")

    # Show summary statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("合計", extraction_summary["total"])
    with col2:
        st.metric(
            "紐付け未実行",
            extraction_summary["pending"],
            help="マッチング処理を待っている数",
        )
    with col3:
        st.metric(
            "マッチ済み",
            extraction_summary["matched"],
            help="政治家と正常にマッチングできた数",
        )
    with col4:
        st.metric(
            "マッチなし",
            extraction_summary["no_match"],
            help="マッチングを実行したが見つからなかった数",
        )

    # Get and display extracted members
    extracted_members = presenter.get_extracted_members(selected_group.id)  # type: ignore[attr-defined]
    if extracted_members:
        # Create DataFrame for display
        members_data = []
        for member in extracted_members:
            members_data.append(
                {
                    "名前": member.extracted_name,
                    "役職": member.extracted_role or "-",
                    "政党": member.extracted_party_name or "-",
                    "選挙区": member.extracted_district or "-",
                    "ステータス": member.matching_status,
                    "信頼度": f"{member.matching_confidence:.2f}"
                    if member.matching_confidence
                    else "-",
                    "抽出日時": member.extracted_at.strftime("%Y-%m-%d %H:%M")
                    if member.extracted_at
                    else "-",
                }
            )

        df_extracted = pd.DataFrame(members_data)
        st.dataframe(df_extracted, use_container_width=True, height=300)

    # Add separator
    st.divider()


def _render_extraction_settings(
    presenter: ParliamentaryGroupPresenter,
    selected_group: object,
) -> None:
    """Render extraction settings and execution buttons.

    Args:
        presenter: 議員団プレゼンター
        selected_group: 選択された議員団
    """
    st.markdown("### 抽出設定")

    col1, col2 = st.columns(2)
    with col1:
        confidence_threshold = st.slider(
            "マッチング信頼度の閾値",
            min_value=0.5,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="この値以上の信頼度でマッチングされた政治家のみメンバーシップを作成します",
        )

    with col2:
        start_date = japanese_era_date_input(
            label="所属開始日",
            value=date.today(),
            key="extraction_start_date",
            help="作成されるメンバーシップの所属開始日",
        )

    dry_run = st.checkbox(
        "ドライラン（データベースに保存しない）",
        value=False,
        help="チェックすると、抽出結果の確認のみ行い、データベースには保存しません",
    )

    # 抽出方式の選択
    use_agent = st.checkbox(
        "🤖 LangGraphエージェントを使用（推奨）",
        value=True,
        help="LangGraphエージェントによる高精度な抽出を使用します。"
        "検証・重複除去を自動で行います。",
    )

    # Execute extraction
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 メンバー抽出を実行", type="primary"):
            _execute_extraction(
                presenter,
                selected_group,
                use_agent,
                confidence_threshold,
                start_date,
                dry_run,
            )


def _execute_extraction(
    presenter: ParliamentaryGroupPresenter,
    selected_group: object,
    use_agent: bool,
    confidence_threshold: float,
    start_date: date,
    dry_run: bool,
) -> None:
    """Execute member extraction.

    Args:
        presenter: 議員団プレゼンター
        selected_group: 選択された議員団
        use_agent: LangGraphエージェントを使用するか
        confidence_threshold: マッチング信頼度の閾値
        start_date: 所属開始日
        dry_run: ドライランモードか
    """
    if use_agent:
        # LangGraphエージェントを使用
        with st.spinner("🤖 LangGraphエージェントでメンバー情報を抽出中..."):
            success, result, error = presenter.extract_members_with_agent(
                selected_group.name,  # type: ignore[attr-defined]
                cast(str, selected_group.url),  # type: ignore[attr-defined]
            )

            if success and result:
                extracted_count = len(result.members)

                if extracted_count > 0:
                    st.success(f"✅ {extracted_count}名のメンバーを抽出しました")

                    # 抽出結果を表示
                    st.markdown("### 抽出されたメンバー")
                    members_data = [
                        {
                            "名前": m.name,
                            "役職": m.role or "-",
                            "政党": m.party_name or "-",
                            "選挙区": m.district or "-",
                            "備考": m.additional_info or "-",
                        }
                        for m in result.members
                    ]
                    df_members = pd.DataFrame(members_data)
                    st.dataframe(df_members, use_container_width=True)

                    st.info(
                        "💡 DB保存は行っていません。"
                        "必要に応じて手動で登録してください。"
                    )
                else:
                    st.warning("メンバーが抽出されませんでした")
            else:
                st.error(f"抽出エラー: {error}")
    else:
        # 既存のBAML抽出器を使用
        with st.spinner("メンバー情報を抽出中..."):
            success, result, error = presenter.extract_members(
                selected_group.id,  # type: ignore[attr-defined]
                cast(str, selected_group.url),  # type: ignore[attr-defined]
                confidence_threshold,
                start_date,
                dry_run,
            )

            if success and result:
                if result.extracted_members:
                    st.success(
                        f"✅ {len(result.extracted_members)}名のメンバーを抽出しました"
                    )

                    # Display extracted members
                    st.markdown("### 抽出されたメンバー")

                    members_data = []
                    for member in result.extracted_members:
                        members_data.append(
                            {
                                "名前": member.name,
                                "役職": member.role or "-",
                                "政党": member.party_name or "-",
                                "選挙区": member.district or "-",
                                "備考": member.additional_info or "-",
                            }
                        )

                    df_members = pd.DataFrame(members_data)
                    st.dataframe(df_members, use_container_width=True)

                    if not dry_run:
                        st.info(
                            "💡 抽出されたメンバーは「メンバーレビュー」タブで"
                            "レビュー・マッチングできます"
                        )
                else:
                    st.warning("メンバーが抽出されませんでした")
            else:
                st.error(f"抽出エラー: {error}")
