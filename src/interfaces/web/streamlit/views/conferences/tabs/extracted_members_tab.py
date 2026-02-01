"""抽出結果確認タブのUI実装.

マッチング実行、所属情報作成、手動レビュー機能を含みます。
"""

import asyncio
import logging

from datetime import date
from typing import Any

import nest_asyncio
import pandas as pd
import streamlit as st

from src.application.usecases.manage_conference_members_usecase import (
    ApproveMatchInputDTO,
    CreateAffiliationsInputDTO,
    ManageConferenceMembersUseCase,
    ManualMatchInputDTO,
    MatchMembersInputDTO,
    RejectMatchInputDTO,
    SearchPoliticiansInputDTO,
)
from src.application.usecases.mark_entity_as_verified_usecase import (
    EntityType,
    MarkEntityAsVerifiedInputDto,
    MarkEntityAsVerifiedUseCase,
)
from src.domain.entities.extracted_conference_member import (
    ExtractedConferenceMember,
    MatchingStatus,
)
from src.infrastructure.exceptions import DatabaseError, LLMError
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.components import (
    get_verification_badge_text,
    render_verification_filter,
)


logger = logging.getLogger(__name__)

MAX_MEMBERS_FETCH_LIMIT = 1000
DETAILS_DISPLAY_LIMIT = 20


def _run_async(coro: Any) -> Any:
    """同期コンテキストから非同期コルーチンを実行するヘルパー.

    RepositoryAdapterと同じnest_asyncioパターンを使用し、
    Streamlitのイベントループ内からも安全に実行できます。
    """
    nest_asyncio.apply()

    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            task = loop.create_task(coro)
            return loop.run_until_complete(task)
        else:
            return loop.run_until_complete(coro)
    except Exception as e:
        logger.error(f"非同期操作の実行に失敗しました: {e}")
        raise


def render_extracted_members(
    extracted_member_repo: RepositoryAdapter,
    conference_repo: RepositoryAdapter,
    manage_members_usecase: ManageConferenceMembersUseCase,
    verify_use_case: MarkEntityAsVerifiedUseCase,
) -> None:
    """抽出された議員情報を表示する.

    抽出結果確認タブをレンダリングします。
    会議体、ステータス、検証状態でのフィルタリング、マッチング実行、
    所属情報作成、手動レビューなどの機能を提供します。

    Args:
        extracted_member_repo: 抽出メンバーリポジトリ
        conference_repo: 会議体リポジトリ
        manage_members_usecase: 会議体メンバー管理UseCase
        verify_use_case: 検証UseCase
    """
    st.header("抽出結果確認")

    # フィルタ列
    col1, col2, col3 = st.columns(3)

    with col1:
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
        status_options: dict[str, str | None] = {
            "すべて": None,
            "未マッチング": MatchingStatus.PENDING.value,
            "マッチング済み": MatchingStatus.MATCHED.value,
            "マッチなし": MatchingStatus.NO_MATCH.value,
            "要確認": MatchingStatus.NEEDS_REVIEW.value,
        }
        selected_status = st.selectbox(
            "ステータスで絞り込み",
            options=list(status_options.keys()),
            key="filter_extracted_status",
        )
        status = status_options[selected_status]

    with col3:
        verification_filter = render_verification_filter(
            key="filter_extracted_verification"
        )

    # サマリーを1回だけ取得して使い回す
    summary = extracted_member_repo.get_extraction_summary(conference_id)

    # マッチング・所属作成アクションセクション
    _render_matching_actions(manage_members_usecase, conference_id, summary)

    # 統計を表示
    _display_summary_statistics(summary)

    # メンバーを取得してフィルタリング
    members = _get_and_filter_members(
        extracted_member_repo, conference_id, status, verification_filter
    )

    if not members:
        st.info("該当する抽出結果がありません。")
        return

    # DataFrameに変換して表示
    _display_members_dataframe(members)

    # 詳細表示と検証状態更新・手動レビュー
    _render_member_details(members, verify_use_case, manage_members_usecase)


def _render_matching_actions(
    usecase: ManageConferenceMembersUseCase,
    conference_id: int | None,
    summary: dict[str, int],
) -> None:
    """マッチング実行と所属情報作成のアクションセクションを表示する.

    Args:
        usecase: 会議体メンバー管理UseCase
        conference_id: 選択中の会議体ID（Noneの場合は全件対象）
        summary: 抽出サマリー統計
    """
    st.markdown("---")
    st.markdown("### マッチング・所属作成")

    col1, col2 = st.columns(2)

    with col1:
        _render_matching_execution(usecase, conference_id, summary)

    with col2:
        _render_affiliation_creation(usecase, conference_id, summary)

    st.markdown("---")


def _render_matching_execution(
    usecase: ManageConferenceMembersUseCase,
    conference_id: int | None,
    summary: dict[str, int],
) -> None:
    """マッチング実行UIを表示する.

    Args:
        usecase: 会議体メンバー管理UseCase
        conference_id: 選択中の会議体ID
        summary: 抽出サマリー統計
    """
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
    """マッチング処理を実行する.

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
        output = _run_async(usecase.match_members(input_dto))

        progress_bar.progress(1.0)
        status_text.text("マッチング完了")

        # session_stateに結果を保存して再描画後も表示
        st.session_state["matching_result"] = {
            "matched": output.matched_count,
            "needs_review": output.needs_review_count,
            "no_match": output.no_match_count,
        }
        st.rerun()

    except LLMError:
        logger.exception("LLMサービスでエラーが発生しました")
        progress_bar.progress(1.0)
        status_text.text("LLMサービスでエラーが発生しました")
        st.error(
            "LLMサービスでエラーが発生しました。APIキーとネットワーク接続を確認してください。"
        )
    except DatabaseError:
        logger.exception("データベースエラーが発生しました")
        progress_bar.progress(1.0)
        status_text.text("データベースエラーが発生しました")
        st.error("データベースエラーが発生しました。接続状態を確認してください。")
    except Exception:
        logger.exception("マッチング処理中にエラーが発生しました")
        progress_bar.progress(1.0)
        status_text.text("マッチング処理でエラーが発生しました")
        st.error("マッチング処理中にエラーが発生しました。ログを確認してください。")


def _render_affiliation_creation(
    usecase: ManageConferenceMembersUseCase,
    conference_id: int | None,
    summary: dict[str, int],
) -> None:
    """所属情報作成UIを表示する.

    Args:
        usecase: 会議体メンバー管理UseCase
        conference_id: 選択中の会議体ID
        summary: 抽出サマリー統計
    """
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
    """所属情報作成処理を実行する.

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
        output = _run_async(usecase.create_affiliations(input_dto))

        progress_bar.progress(1.0)
        status_text.text("所属情報作成完了")

        # session_stateに結果を保存して再描画後も表示
        affiliations_data = []
        if output.affiliations:
            for aff in output.affiliations:
                affiliations_data.append(
                    {
                        "政治家名": aff.politician_name,
                        "会議体ID": aff.conference_id,
                        "役職": aff.role or "-",
                        "開始日": str(aff.start_date),
                    }
                )

        st.session_state["affiliation_result"] = {
            "created": output.created_count,
            "skipped": output.skipped_count,
            "affiliations": affiliations_data,
        }
        st.rerun()

    except DatabaseError:
        logger.exception("データベースエラーが発生しました")
        progress_bar.progress(1.0)
        status_text.text("データベースエラーが発生しました")
        st.error("データベースエラーが発生しました。接続状態を確認してください。")
    except Exception:
        logger.exception("所属情報作成中にエラーが発生しました")
        progress_bar.progress(1.0)
        status_text.text("所属情報作成でエラーが発生しました")
        st.error("所属情報作成中にエラーが発生しました。ログを確認してください。")


def _display_summary_statistics(summary: dict[str, Any]) -> None:
    """サマリー統計を表示する.

    Args:
        summary: サマリー統計
    """
    # session_stateに保存されたマッチング結果を表示
    if "matching_result" in st.session_state:
        result = st.session_state.pop("matching_result")
        st.success("マッチング処理が完了しました")
        r_col1, r_col2, r_col3 = st.columns(3)
        with r_col1:
            st.metric("マッチ成功", result["matched"])
        with r_col2:
            st.metric("要確認", result["needs_review"])
        with r_col3:
            st.metric("該当なし", result["no_match"])

    # session_stateに保存された所属作成結果を表示
    if "affiliation_result" in st.session_state:
        result = st.session_state.pop("affiliation_result")
        st.success("所属情報の作成が完了しました")
        r_col1, r_col2 = st.columns(2)
        with r_col1:
            st.metric("作成数", result["created"])
        with r_col2:
            st.metric("スキップ数", result["skipped"])

        if result["affiliations"]:
            with st.expander("作成された所属情報の詳細"):
                st.dataframe(
                    pd.DataFrame(result["affiliations"]),
                    use_container_width=True,
                    hide_index=True,
                )

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
) -> list[ExtractedConferenceMember]:
    """メンバーを取得してフィルタリングする.

    Args:
        extracted_member_repo: 抽出メンバーリポジトリ
        conference_id: 会議体ID
        status: ステータス
        verification_filter: 検証フィルター

    Returns:
        フィルタリングされたメンバーリスト
    """
    if conference_id:
        members = extracted_member_repo.get_by_conference(conference_id)
    else:
        members = extracted_member_repo.get_all(limit=MAX_MEMBERS_FETCH_LIMIT)

    if status:
        members = [m for m in members if m.matching_status == status]

    if verification_filter is not None:
        members = [m for m in members if m.is_manually_verified == verification_filter]

    return members


def _display_members_dataframe(members: list[ExtractedConferenceMember]) -> None:
    """メンバーをDataFrameとして表示する.

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
    members: list[ExtractedConferenceMember],
    verify_use_case: MarkEntityAsVerifiedUseCase,
    manage_members_usecase: ManageConferenceMembersUseCase,
) -> None:
    """メンバー詳細、検証コントロール、手動レビューUIを表示する.

    Args:
        members: メンバーリスト
        verify_use_case: 検証UseCase
        manage_members_usecase: 会議体メンバー管理UseCase
    """
    st.markdown("### メンバー詳細と検証状態更新")
    for member in members[:DETAILS_DISPLAY_LIMIT]:
        badge = get_verification_badge_text(member.is_manually_verified)
        status_label = _get_status_label(
            member.matching_status, member.is_manually_verified
        )
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

            # 手動レビューUI（needs_review / no_match / pending ステータスのみ）
            if member.matching_status in (
                MatchingStatus.NEEDS_REVIEW,
                MatchingStatus.NO_MATCH,
                MatchingStatus.PENDING,
            ):
                _render_manual_review(member, manage_members_usecase)


def _get_status_label(status: str, is_manually_verified: bool = False) -> str:
    """ステータスの日本語ラベルを取得する.

    matchedステータスの場合、is_manually_verifiedフラグにより
    手動マッチングかLLMマッチングかを区別して表示します。

    Args:
        status: ステータス文字列
        is_manually_verified: 手動検証済みフラグ

    Returns:
        日本語ラベル
    """
    if status == MatchingStatus.MATCHED:
        return "手動マッチング済み" if is_manually_verified else "LLMマッチング済み"

    labels: dict[str, str] = {
        MatchingStatus.PENDING.value: "未マッチング",
        MatchingStatus.NO_MATCH.value: "マッチなし",
        MatchingStatus.NEEDS_REVIEW.value: "要確認",
    }
    return labels.get(status, status)


def _render_manual_review(
    member: ExtractedConferenceMember,
    manage_members_usecase: ManageConferenceMembersUseCase,
) -> None:
    """手動レビューUIを表示する.

    needs_review/no_match/pendingステータスのメンバーに対して、
    マッチング結果の承認/却下、手動での政治家選択を提供します。

    Args:
        member: メンバーエンティティ
        manage_members_usecase: 会議体メンバー管理UseCase
    """
    st.markdown("---")
    st.markdown("**手動マッチング操作**")

    # needs_reviewの場合は承認/却下ボタンを表示
    if (
        member.matching_status == MatchingStatus.NEEDS_REVIEW
        and member.matched_politician_id
    ):
        approve_col, reject_col = st.columns(2)
        with approve_col:
            if st.button(
                "承認（マッチング確定）",
                key=f"approve_{member.id}",
                type="primary",
            ):
                input_dto = ApproveMatchInputDTO(member_id=member.id or 0)
                output = _run_async(manage_members_usecase.approve_match(input_dto))
                if output.success:
                    st.success(output.message)
                    st.rerun()
                else:
                    st.error(output.message)

        with reject_col:
            if st.button(
                "却下（マッチなしに変更）",
                key=f"reject_{member.id}",
            ):
                input_dto = RejectMatchInputDTO(member_id=member.id or 0)
                output = _run_async(manage_members_usecase.reject_match(input_dto))
                if output.success:
                    st.success(output.message)
                    st.rerun()
                else:
                    st.error(output.message)

    # 手動で政治家を選択してマッチング
    st.markdown("**手動で政治家を選択**")

    search_name = st.text_input(
        "政治家名で検索",
        value=member.extracted_name,
        key=f"search_politician_{member.id}",
    )

    if search_name:
        search_dto = SearchPoliticiansInputDTO(name=search_name)
        search_result = _run_async(
            manage_members_usecase.search_politicians(search_dto)
        )

        if not search_result.candidates:
            st.warning(f"「{search_name}」に該当する政治家が見つかりません。")
        else:
            candidate_options: dict[str, int | None] = {"-- 選択してください --": None}
            for c in search_result.candidates:
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
                    input_dto = ManualMatchInputDTO(
                        member_id=member.id or 0,
                        politician_id=selected_politician_id,
                    )
                    output = _run_async(manage_members_usecase.manual_match(input_dto))
                    if output.success:
                        st.success(output.message)
                        st.rerun()
                    else:
                        st.error(output.message)


def _render_verification_control(
    member: ExtractedConferenceMember,
    verify_use_case: MarkEntityAsVerifiedUseCase,
) -> None:
    """メンバーの検証コントロールを表示する.

    Args:
        member: メンバーエンティティ
        verify_use_case: 検証UseCase
    """
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
            assert member.id is not None, "メンバーIDが設定されていません"
            result = _run_async(
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
