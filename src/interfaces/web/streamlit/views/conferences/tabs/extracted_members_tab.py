"""Extracted members tab for conferences.

抽出結果確認タブのUI実装を提供します。
マッチング実行、所属情報作成、手動レビュー機能を含みます。
"""

import asyncio
import logging

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from src.application.usecases.manage_conference_members_usecase import (
    CreateAffiliationsInputDTO,
    ManageConferenceMembersUseCase,
    MatchMembersInputDTO,
)
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


logger = logging.getLogger(__name__)


def render_extracted_members(
    extracted_member_repo: RepositoryAdapter,
    conference_repo: RepositoryAdapter,
    politician_repo: RepositoryAdapter,
    manage_members_usecase: ManageConferenceMembersUseCase,
) -> None:
    """抽出された議員情報を表示する

    抽出結果確認タブをレンダリングします。
    会議体、ステータス、検証状態でのフィルタリング、マッチング実行、
    所属情報作成、手動レビューなどの機能を提供します。

    Args:
        extracted_member_repo: 抽出メンバーリポジトリ
        conference_repo: 会議体リポジトリ
        politician_repo: 政治家リポジトリ
        manage_members_usecase: 会議体メンバー管理UseCase
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

    # マッチング・所属作成アクションセクション
    _render_matching_actions(
        manage_members_usecase, conference_id, extracted_member_repo
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

    # 詳細表示と検証状態更新・手動レビュー
    _render_member_details(
        members, verify_use_case, extracted_member_repo, politician_repo
    )


def _render_matching_actions(
    usecase: ManageConferenceMembersUseCase,
    conference_id: int | None,
    extracted_member_repo: RepositoryAdapter,
) -> None:
    """マッチング実行と所属情報作成のアクションセクションを表示する

    Args:
        usecase: 会議体メンバー管理UseCase
        conference_id: 選択中の会議体ID（Noneの場合は全件対象）
        extracted_member_repo: 抽出メンバーリポジトリ
    """
    st.markdown("---")
    st.markdown("### マッチング・所属作成")

    col1, col2 = st.columns(2)

    with col1:
        _render_matching_execution(usecase, conference_id, extracted_member_repo)

    with col2:
        _render_affiliation_creation(usecase, conference_id, extracted_member_repo)

    st.markdown("---")


def _render_matching_execution(
    usecase: ManageConferenceMembersUseCase,
    conference_id: int | None,
    extracted_member_repo: RepositoryAdapter,
) -> None:
    """マッチング実行UIを表示する

    Args:
        usecase: 会議体メンバー管理UseCase
        conference_id: 選択中の会議体ID
        extracted_member_repo: 抽出メンバーリポジトリ
    """
    # 未マッチングの件数を取得
    summary = extracted_member_repo.get_extraction_summary(conference_id)
    pending_count = summary.get("pending", 0)

    st.markdown("#### 政治家マッチング")
    target_text = f"会議体ID: {conference_id}" if conference_id else "すべての会議体"
    st.caption(f"対象: {target_text}（未マッチング: {pending_count}件）")

    if pending_count == 0:
        st.info("未マッチングのメンバーがありません。")
        return

    if st.button(
        f"マッチング実行（{pending_count}件）",
        key="btn_match_members",
        type="primary",
    ):
        _execute_matching(usecase, conference_id)


def _execute_matching(
    usecase: ManageConferenceMembersUseCase,
    conference_id: int | None,
) -> None:
    """マッチング処理を実行する

    Args:
        usecase: 会議体メンバー管理UseCase
        conference_id: 会議体ID
    """
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        status_text.text("LLMを使用して政治家データとマッチング中...")
        progress_bar.progress(0.1)

        input_dto = MatchMembersInputDTO(conference_id=conference_id)
        output = asyncio.run(usecase.match_members(input_dto))

        progress_bar.progress(1.0)
        status_text.text("マッチング完了")

        # 結果サマリー表示
        st.success("マッチング処理が完了しました")
        result_col1, result_col2, result_col3 = st.columns(3)
        with result_col1:
            st.metric("マッチ成功", output.matched_count)
        with result_col2:
            st.metric("要確認", output.needs_review_count)
        with result_col3:
            st.metric("該当なし", output.no_match_count)

        st.rerun()

    except Exception:
        logger.exception("マッチング処理中にエラーが発生しました")
        progress_bar.progress(1.0)
        status_text.text("マッチング処理でエラーが発生しました")
        st.error("マッチング処理中にエラーが発生しました。ログを確認してください。")


def _render_affiliation_creation(
    usecase: ManageConferenceMembersUseCase,
    conference_id: int | None,
    extracted_member_repo: RepositoryAdapter,
) -> None:
    """所属情報作成UIを表示する

    Args:
        usecase: 会議体メンバー管理UseCase
        conference_id: 選択中の会議体ID
        extracted_member_repo: 抽出メンバーリポジトリ
    """
    # マッチ済みの件数を取得
    summary = extracted_member_repo.get_extraction_summary(conference_id)
    matched_count = summary.get("matched", 0)

    st.markdown("#### 所属情報作成")
    target_text = f"会議体ID: {conference_id}" if conference_id else "すべての会議体"
    st.caption(f"対象: {target_text}（マッチング済み: {matched_count}件）")

    if matched_count == 0:
        st.info("マッチング済みのメンバーがありません。")
        return

    start_date = st.date_input(
        "所属開始日",
        value=date.today(),
        key="affiliation_start_date",
    )

    if st.button(
        f"所属情報を作成（{matched_count}件）",
        key="btn_create_affiliations",
        type="primary",
    ):
        _execute_affiliation_creation(usecase, conference_id, start_date)


def _execute_affiliation_creation(
    usecase: ManageConferenceMembersUseCase,
    conference_id: int | None,
    start_date: date,
) -> None:
    """所属情報作成処理を実行する

    Args:
        usecase: 会議体メンバー管理UseCase
        conference_id: 会議体ID
        start_date: 所属開始日
    """
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        status_text.text("所属情報を作成中...")
        progress_bar.progress(0.1)

        input_dto = CreateAffiliationsInputDTO(
            conference_id=conference_id,
            start_date=start_date,
        )
        output = asyncio.run(usecase.create_affiliations(input_dto))

        progress_bar.progress(1.0)
        status_text.text("所属情報作成完了")

        # 結果サマリー表示
        st.success("所属情報の作成が完了しました")
        result_col1, result_col2 = st.columns(2)
        with result_col1:
            st.metric("作成数", output.created_count)
        with result_col2:
            st.metric("スキップ数", output.skipped_count)

        # 作成された所属情報の詳細
        if output.affiliations:
            with st.expander("作成された所属情報の詳細"):
                aff_data = []
                for aff in output.affiliations:
                    aff_data.append(
                        {
                            "政治家名": aff.politician_name,
                            "会議体ID": aff.conference_id,
                            "役職": aff.role or "-",
                            "開始日": str(aff.start_date),
                        }
                    )
                st.dataframe(
                    pd.DataFrame(aff_data),
                    use_container_width=True,
                    hide_index=True,
                )

        st.rerun()

    except Exception:
        logger.exception("所属情報作成中にエラーが発生しました")
        progress_bar.progress(1.0)
        status_text.text("所属情報作成でエラーが発生しました")
        st.error("所属情報作成中にエラーが発生しました。ログを確認してください。")


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


def _render_member_details(
    members: list[Any],
    verify_use_case: Any,
    extracted_member_repo: RepositoryAdapter,
    politician_repo: RepositoryAdapter,
) -> None:
    """Render member details, verification controls, and manual review UI.

    Args:
        members: メンバーリスト
        verify_use_case: 検証UseCase
        extracted_member_repo: 抽出メンバーリポジトリ
        politician_repo: 政治家リポジトリ
    """
    st.markdown("### メンバー詳細と検証状態更新")
    for member in members[:20]:  # 最大20件表示
        badge = get_verification_badge_text(member.is_manually_verified)
        status_label = _get_status_label(member.matching_status)
        with st.expander(f"{member.extracted_name} - {status_label} - {badge}"):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**ID:** {member.id}")
                st.write(f"**名前:** {member.extracted_name}")
                st.write(f"**役職:** {member.extracted_role or '-'}")
                st.write(f"**政党:** {member.extracted_party_name or '-'}")
                st.write(f"**ステータス:** {status_label}")
                if member.matching_confidence is not None:
                    st.write(f"**信頼度:** {member.matching_confidence:.2f}")
                if member.matched_politician_id:
                    st.write(f"**マッチ先政治家ID:** {member.matched_politician_id}")

            with col2:
                _render_verification_control(member, verify_use_case)

            # 手動レビューUI（needs_review / no_match ステータスのみ）
            if member.matching_status in ("needs_review", "no_match", "pending"):
                _render_manual_review(member, extracted_member_repo, politician_repo)


def _get_status_label(status: str) -> str:
    """ステータスの日本語ラベルを取得する

    Args:
        status: ステータス文字列

    Returns:
        日本語ラベル
    """
    labels = {
        "pending": "未マッチング",
        "matched": "マッチング済み",
        "no_match": "マッチなし",
        "needs_review": "要確認",
    }
    return labels.get(status, status)


def _render_manual_review(
    member: Any,
    extracted_member_repo: RepositoryAdapter,
    politician_repo: RepositoryAdapter,
) -> None:
    """手動レビューUIを表示する

    needs_review/no_match/pendingステータスのメンバーに対して、
    マッチング結果の承認/却下、手動での政治家選択を提供します。

    Args:
        member: メンバーエンティティ
        extracted_member_repo: 抽出メンバーリポジトリ
        politician_repo: 政治家リポジトリ
    """
    st.markdown("---")
    st.markdown("**手動マッチング操作**")

    # needs_reviewの場合は承認/却下ボタンを表示
    if member.matching_status == "needs_review" and member.matched_politician_id:
        approve_col, reject_col = st.columns(2)
        with approve_col:
            if st.button(
                "承認（マッチング確定）",
                key=f"approve_{member.id}",
                type="primary",
            ):
                extracted_member_repo.update_matching_result(
                    member_id=member.id,
                    politician_id=member.matched_politician_id,
                    confidence=1.0,
                    status="matched",
                )
                st.success("マッチングを承認しました")
                st.rerun()

        with reject_col:
            if st.button(
                "却下（マッチなしに変更）",
                key=f"reject_{member.id}",
            ):
                extracted_member_repo.update_matching_result(
                    member_id=member.id,
                    politician_id=None,
                    confidence=0.0,
                    status="no_match",
                )
                st.success("マッチングを却下しました")
                st.rerun()

    # 手動で政治家を選択してマッチング
    st.markdown("**手動で政治家を選択**")

    # メンバー名で政治家を検索
    search_name = st.text_input(
        "政治家名で検索",
        value=member.extracted_name,
        key=f"search_politician_{member.id}",
    )

    if search_name:
        # 政治家データはスペース除去済みのため、検索名からもスペースを除去
        normalized_name = search_name.replace(" ", "").replace("\u3000", "")
        candidates = politician_repo.search_by_name(normalized_name)

        if not candidates:
            st.warning(f"「{search_name}」に該当する政治家が見つかりません。")
        else:
            # selectboxの選択肢を作成
            candidate_options: dict[str, int | None] = {"-- 選択してください --": None}
            for c in candidates:
                label = f"{c.name} (ID: {c.id})"
                candidate_options[label] = c.id

            selected = st.selectbox(
                "政治家を選択",
                options=list(candidate_options.keys()),
                key=f"select_politician_{member.id}",
            )

            selected_politician_id = candidate_options[selected]

            if selected_politician_id is not None:
                if st.button(
                    "この政治家にマッチング",
                    key=f"manual_match_{member.id}",
                    type="primary",
                ):
                    extracted_member_repo.update_matching_result(
                        member_id=member.id,
                        politician_id=selected_politician_id,
                        confidence=1.0,
                        status="matched",
                    )
                    st.success("手動マッチングが完了しました")
                    st.rerun()


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
                        entity_id=member.id,
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
