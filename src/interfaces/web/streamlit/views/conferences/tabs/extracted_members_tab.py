"""Extracted members tab for conferences.

抽出結果確認タブのUI実装を提供します。
"""

import asyncio

from typing import Any

import pandas as pd
import streamlit as st

from src.application.usecases.mark_entity_as_verified_usecase import (
    EntityType,
    MarkEntityAsVerifiedInputDto,
    MarkEntityAsVerifiedUseCase,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.components import (
    get_verification_badge_text,
    render_verification_filter,
)


def render_extracted_members(
    extracted_member_repo: RepositoryAdapter, conference_repo: RepositoryAdapter
) -> None:
    """抽出された議員情報を表示する

    抽出結果確認タブをレンダリングします。
    会議体、ステータス、検証状態でのフィルタリング、詳細表示などの機能を提供します。

    Args:
        extracted_member_repo: 抽出メンバーリポジトリ
        conference_repo: 会議体リポジトリ
    """
    st.header("抽出結果確認")

    # フィルタ列
    col1, col2, col3 = st.columns(3)

    with col1:
        # 会議体でフィルタリング
        conferences = conference_repo.get_all()
        conference_options: dict[str, int | None] = {"すべて": None}
        conference_options.update({conf.name: conf.id for conf in conferences})

        selected_conf = st.selectbox(
            "会議体で絞り込み",
            options=list(conference_options.keys()),
            key="filter_extracted_conference",
        )
        conference_id = conference_options[selected_conf]

    with col2:
        # ステータスでフィルタリング
        status_options = {
            "すべて": None,
            "未マッチング": "pending",
            "マッチング済み": "matched",
            "マッチなし": "no_match",
            "要確認": "needs_review",
        }
        selected_status = st.selectbox(
            "ステータスで絞り込み",
            options=list(status_options.keys()),
            key="filter_extracted_status",
        )
        status = status_options[selected_status]

    with col3:
        # 検証状態でフィルタリング
        verification_filter = render_verification_filter(
            key="filter_extracted_verification"
        )

    # サマリー統計を取得（RepositoryAdapterが自動的にasyncio.run()を実行）
    summary = extracted_member_repo.get_extraction_summary(conference_id)

    # 統計を表示
    _display_summary_statistics(summary)

    # メンバーを取得してフィルタリング
    members = _get_and_filter_members(
        extracted_member_repo, conference_id, status, verification_filter
    )

    if not members:
        st.info("該当する抽出結果がありません。")
        return

    # 検証UseCase初期化
    verify_use_case = MarkEntityAsVerifiedUseCase(
        conference_member_repository=extracted_member_repo  # type: ignore[arg-type]
    )

    # DataFrameに変換して表示
    _display_members_dataframe(members)

    # 詳細表示と検証状態更新
    _render_member_details(members, verify_use_case)


def _display_summary_statistics(summary: dict[str, Any]) -> None:
    """Display summary statistics.

    Args:
        summary: サマリー統計
    """
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("総件数", summary.get("total", 0))
    with col2:
        st.metric("未マッチング", summary.get("pending", 0))
    with col3:
        st.metric("マッチング済み", summary.get("matched", 0))
    with col4:
        st.metric("マッチなし", summary.get("no_match", 0))
    with col5:
        st.metric("要確認", summary.get("needs_review", 0))


def _get_and_filter_members(
    extracted_member_repo: RepositoryAdapter,
    conference_id: int | None,
    status: str | None,
    verification_filter: bool | None,
) -> list[Any]:
    """Get and filter members.

    Args:
        extracted_member_repo: 抽出メンバーリポジトリ
        conference_id: 会議体ID
        status: ステータス
        verification_filter: 検証フィルター

    Returns:
        フィルタリングされたメンバーリスト
    """
    # 抽出結果を取得（RepositoryAdapterが自動的にasyncio.run()を実行）
    if conference_id:
        members = extracted_member_repo.get_by_conference(conference_id)
    else:
        members = extracted_member_repo.get_all(limit=1000)

    # ステータスでフィルタリング
    if status:
        members = [m for m in members if m.matching_status == status]

    # 検証状態でフィルタリング
    if verification_filter is not None:
        members = [m for m in members if m.is_manually_verified == verification_filter]

    return members


def _display_members_dataframe(members: list[Any]) -> None:
    """Display members as DataFrame.

    Args:
        members: メンバーリスト
    """
    data = []
    for member in members:
        data.append(
            {
                "ID": member.id,
                "会議体ID": member.conference_id,
                "名前": member.extracted_name,
                "役職": member.extracted_role or "",
                "政党": member.extracted_party_name or "",
                "ステータス": member.matching_status,
                "検証状態": get_verification_badge_text(member.is_manually_verified),
                "マッチング信頼度": (
                    f"{member.matching_confidence:.2f}"
                    if member.matching_confidence
                    else ""
                ),
                "抽出日時": member.extracted_at.strftime("%Y-%m-%d %H:%M:%S"),
                "ソースURL": member.source_url,
            }
        )

    df = pd.DataFrame(data)

    # 表示
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ソースURL": st.column_config.LinkColumn("ソースURL"),
            "マッチング信頼度": st.column_config.NumberColumn(
                "マッチング信頼度",
                format="%.2f",
            ),
        },
    )


def _render_member_details(members: list[Any], verify_use_case: Any) -> None:
    """Render member details and verification controls.

    Args:
        members: メンバーリスト
        verify_use_case: 検証UseCase
    """
    st.markdown("### メンバー詳細と検証状態更新")
    for member in members[:20]:  # 最大20件表示
        badge = get_verification_badge_text(member.is_manually_verified)
        with st.expander(f"{member.extracted_name} - {badge}"):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**ID:** {member.id}")
                st.write(f"**名前:** {member.extracted_name}")
                st.write(f"**役職:** {member.extracted_role or '-'}")
                st.write(f"**政党:** {member.extracted_party_name or '-'}")
                st.write(f"**ステータス:** {member.matching_status}")

            with col2:
                _render_verification_control(member, verify_use_case)


def _render_verification_control(member: Any, verify_use_case: Any) -> None:
    """Render verification control for a member.

    Args:
        member: メンバーエンティティ
        verify_use_case: 検証UseCase
    """
    # 検証状態チェックボックス
    current_verified = member.is_manually_verified
    new_verified = st.checkbox(
        "手動検証済み",
        value=current_verified,
        key=f"verify_conf_member_{member.id}",
        help="チェックすると、AI再実行でこのデータが上書きされなくなります",
    )

    if new_verified != current_verified:
        if st.button(
            "検証状態を更新",
            key=f"update_verify_{member.id}",
            type="primary",
        ):
            result = asyncio.run(
                verify_use_case.execute(
                    MarkEntityAsVerifiedInputDto(
                        entity_type=EntityType.CONFERENCE_MEMBER,
                        entity_id=member.id,  # type: ignore[arg-type]
                        is_verified=new_verified,
                    )
                )
            )
            if result.success:
                status_text = "手動検証済み" if new_verified else "未検証"
                st.success(f"検証状態を「{status_text}」に更新しました")
                st.rerun()
            else:
                st.error(f"更新に失敗しました: {result.error_message}")
