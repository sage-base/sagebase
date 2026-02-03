"""抽出結果確認タブのUI実装.

抽出済みメンバーの一覧表示、手動政治家選択機能を含みます。
政治家との紐付けはGold Layer（ConferenceMember）で管理されます。
"""

import asyncio
import logging

from typing import Any

import nest_asyncio
import pandas as pd
import streamlit as st

from src.application.usecases.manage_conference_members_usecase import (
    ManageConferenceMembersUseCase,
    ManualMatchInputDTO,
    SearchPoliticiansInputDTO,
)
from src.application.usecases.mark_entity_as_verified_usecase import (
    EntityType,
    MarkEntityAsVerifiedInputDto,
    MarkEntityAsVerifiedUseCase,
)
from src.domain.entities.conference_member import ConferenceMember
from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
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
    conference_member_repo: RepositoryAdapter | None = None,
) -> None:
    """抽出された議員情報を表示する.

    抽出結果確認タブをレンダリングします。
    会議体、検証状態でのフィルタリング、手動政治家選択などの機能を提供します。

    Args:
        extracted_member_repo: 抽出メンバーリポジトリ
        conference_repo: 会議体リポジトリ
        manage_members_usecase: 会議体メンバー管理UseCase
        verify_use_case: 検証UseCase
        conference_member_repo: 会議体メンバーリポジトリ（Gold Layer表示用）
    """
    st.header("抽出結果確認")

    # フィルタ列
    col1, col2 = st.columns(2)

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
        verification_filter = render_verification_filter(
            key="filter_extracted_verification"
        )

    # サマリーを1回だけ取得して使い回す
    summary = extracted_member_repo.get_extraction_summary(conference_id)

    # 統計を表示
    _display_summary_statistics(summary)

    # メンバーを取得してフィルタリング
    members = _get_and_filter_members(
        extracted_member_repo, conference_id, verification_filter
    )

    if not members:
        st.info("該当する抽出結果がありません。")
        return

    # DataFrameに変換して表示
    _display_members_dataframe(members)

    # 詳細表示と検証状態更新・手動政治家選択
    _render_member_details(
        members, verify_use_case, manage_members_usecase, conference_member_repo
    )


def _display_summary_statistics(summary: dict[str, Any]) -> None:
    """サマリー統計を表示する.

    Args:
        summary: サマリー統計
    """
    st.metric("総件数", summary.get("total", 0))


def _get_and_filter_members(
    extracted_member_repo: RepositoryAdapter,
    conference_id: int | None,
    verification_filter: bool | None,
) -> list[ExtractedConferenceMember]:
    """メンバーを取得してフィルタリングする.

    Args:
        extracted_member_repo: 抽出メンバーリポジトリ
        conference_id: 会議体ID
        verification_filter: 検証フィルター

    Returns:
        フィルタリングされたメンバーリスト
    """
    if conference_id:
        members = extracted_member_repo.get_by_conference(conference_id)
    else:
        members = extracted_member_repo.get_all(limit=MAX_MEMBERS_FETCH_LIMIT)

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
                "検証状態": get_verification_badge_text(member.is_manually_verified),
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
        },
    )


def _fetch_affiliation_map(
    members: list[ExtractedConferenceMember],
    conference_member_repo: RepositoryAdapter | None,
) -> dict[int, ConferenceMember]:
    """表示対象メンバーのGold Layer所属情報をバッチ取得してマップを返す."""
    if conference_member_repo is None:
        return {}

    member_ids = [m.id for m in members if m.id is not None]
    if not member_ids:
        return {}

    try:
        affiliations: list[ConferenceMember] = (
            conference_member_repo.get_by_source_extracted_member_ids(member_ids)
        )
    except Exception:
        logger.warning("Gold Layer所属情報の取得に失敗しました", exc_info=True)
        return {}

    return {
        a.source_extracted_member_id: a
        for a in affiliations
        if a.source_extracted_member_id is not None
    }


def _render_affiliation_info(
    member: ExtractedConferenceMember,
    affiliation_map: dict[int, ConferenceMember],
    conference_member_repo: RepositoryAdapter | None = None,
) -> None:
    """Gold Layer所属情報を表示する."""
    if not affiliation_map:
        return

    affiliation = affiliation_map.get(member.id)  # type: ignore[arg-type]
    if affiliation:
        verified_badge = "✅ 検証済み" if affiliation.is_manually_verified else "未検証"
        st.markdown("---")
        st.markdown("**📋 Gold Layer 所属情報:**")
        st.write(f"　所属ID: {affiliation.id}")
        st.write(f"　政治家ID: {affiliation.politician_id}")
        st.write(f"　会議体ID: {affiliation.conference_id}")
        st.write(f"　役職: {affiliation.role or '-'}")
        st.write(f"　開始日: {affiliation.start_date}")
        st.write(f"　終了日: {affiliation.end_date or '-'}")
        st.write(f"　検証状態: {verified_badge}")

        if conference_member_repo and affiliation.id:
            if st.button(
                "🗑️ 紐付け解除",
                key=f"unlink_affiliation_{affiliation.id}",
                type="secondary",
            ):
                try:
                    conference_member_repo.delete(affiliation.id)
                    st.success("所属情報を削除しました")
                    st.rerun()
                except Exception as e:
                    st.error(f"削除に失敗しました: {e}")
    else:
        st.markdown("---")
        st.write("**所属情報:** 未作成")


def _render_member_details(
    members: list[ExtractedConferenceMember],
    verify_use_case: MarkEntityAsVerifiedUseCase,
    manage_members_usecase: ManageConferenceMembersUseCase,
    conference_member_repo: RepositoryAdapter | None = None,
) -> None:
    """メンバー詳細、検証コントロール、手動政治家選択UIを表示する.

    Args:
        members: メンバーリスト
        verify_use_case: 検証UseCase
        manage_members_usecase: 会議体メンバー管理UseCase
        conference_member_repo: 会議体メンバーリポジトリ（Gold Layer表示用）
    """
    st.markdown("### メンバー詳細と検証状態更新")

    display_members = members[:DETAILS_DISPLAY_LIMIT]
    affiliation_map = _fetch_affiliation_map(display_members, conference_member_repo)

    for member in display_members:
        badge = get_verification_badge_text(member.is_manually_verified)
        with st.expander(f"{member.extracted_name} - {badge}"):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**ID:** {member.id}")
                st.write(f"**名前:** {member.extracted_name}")
                st.write(f"**役職:** {member.extracted_role or '-'}")
                st.write(f"**政党:** {member.extracted_party_name or '-'}")

                _render_affiliation_info(
                    member, affiliation_map, conference_member_repo
                )

            with col2:
                _render_verification_control(member, verify_use_case)

            # 手動政治家選択UI（所属情報が未作成の場合）
            affiliation = affiliation_map.get(member.id)  # type: ignore[arg-type]
            if not affiliation:
                _render_manual_match(member, manage_members_usecase)


def _render_manual_match(
    member: ExtractedConferenceMember,
    manage_members_usecase: ManageConferenceMembersUseCase,
) -> None:
    """手動政治家選択UIを表示する.

    抽出済みメンバーに対して、政治家を検索して紐付けるUIを提供します。

    Args:
        member: メンバーエンティティ
        manage_members_usecase: 会議体メンバー管理UseCase
    """
    st.markdown("---")
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
            candidate_options: dict[str, int | None] = {
                "-- 選択してください --": None,
            }
            for c in search_result.candidates:
                label = f"{c.name} (ID: {c.id})"
                candidate_options[label] = c.id

            with st.form(key=f"manual_match_form_{member.id}"):
                selected = st.selectbox(
                    "政治家を選択",
                    options=list(candidate_options.keys()),
                    key=f"select_politician_{member.id}",
                )

                submitted = st.form_submit_button(
                    "この政治家にマッチング",
                    type="primary",
                )

                if submitted:
                    selected_politician_id = candidate_options[selected]
                    if selected_politician_id is None:
                        st.warning("政治家を選択してください。")
                    else:
                        input_dto = ManualMatchInputDTO(
                            member_id=member.id or 0,
                            politician_id=selected_politician_id,
                        )
                        output = _run_async(
                            manage_members_usecase.manual_match(input_dto)
                        )
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
