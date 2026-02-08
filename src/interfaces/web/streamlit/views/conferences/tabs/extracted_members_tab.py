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
    GetElectionCandidatesInputDTO,
    ManageConferenceMembersUseCase,
    ManualMatchInputDTO,
    SearchPoliticiansInputDTO,
    SearchPoliticiansOutputDTO,
)
from src.domain.entities.conference_member import ConferenceMember
from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter


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
    conference_member_repo: RepositoryAdapter | None = None,
) -> None:
    """抽出された議員情報を表示する.

    抽出結果確認タブをレンダリングします。
    会議体でのフィルタリング、手動政治家選択などの機能を提供します。

    Args:
        extracted_member_repo: 抽出メンバーリポジトリ
        conference_repo: 会議体リポジトリ
        manage_members_usecase: 会議体メンバー管理UseCase
        conference_member_repo: 会議体メンバーリポジトリ（Gold Layer表示用）
    """
    st.header("抽出結果確認")

    # 会議体フィルタ
    conferences = conference_repo.get_all()
    conference_options: dict[str, int | None] = {"すべて": None}
    conference_options.update({conf.name: conf.id for conf in conferences})

    selected_conf = st.selectbox(
        "会議体で絞り込み",
        options=list(conference_options.keys()),
        key="filter_extracted_conference",
    )
    conference_id = conference_options[selected_conf]

    # サマリーを1回だけ取得して使い回す
    summary = extracted_member_repo.get_extraction_summary(conference_id)

    # 統計を表示
    _display_summary_statistics(summary)

    # メンバーを取得
    members = _get_and_filter_members(extracted_member_repo, conference_id)

    if not members:
        st.info("該当する抽出結果がありません。")
        return

    # DataFrameに変換して表示
    _display_members_dataframe(members)

    # 詳細表示と手動政治家選択
    _render_member_details(members, manage_members_usecase, conference_member_repo)


def _display_summary_statistics(summary: dict[str, Any]) -> None:
    """サマリー統計を表示する.

    Args:
        summary: サマリー統計
    """
    st.metric("総件数", summary.get("total", 0))


def _get_and_filter_members(
    extracted_member_repo: RepositoryAdapter,
    conference_id: int | None,
) -> list[ExtractedConferenceMember]:
    """メンバーを取得する.

    Args:
        extracted_member_repo: 抽出メンバーリポジトリ
        conference_id: 会議体ID

    Returns:
        メンバーリスト
    """
    if conference_id:
        members = extracted_member_repo.get_by_conference(conference_id)
    else:
        members = extracted_member_repo.get_all(limit=MAX_MEMBERS_FETCH_LIMIT)

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
    """本番提供される会議体-政治家紐付けデータを表示する."""
    if not affiliation_map:
        return

    affiliation = affiliation_map.get(member.id)  # type: ignore[arg-type]
    if affiliation:
        verified_badge = "✅ 検証済み" if affiliation.is_manually_verified else "未検証"
        st.markdown("---")
        st.markdown("**📋 本番提供される会議体-政治家紐付けデータ:**")
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
    manage_members_usecase: ManageConferenceMembersUseCase,
    conference_member_repo: RepositoryAdapter | None = None,
) -> None:
    """メンバー詳細と手動政治家選択UIを表示する.

    Args:
        members: メンバーリスト
        manage_members_usecase: 会議体メンバー管理UseCase
        conference_member_repo: 会議体メンバーリポジトリ（Gold Layer表示用）
    """
    st.markdown("### メンバー詳細")

    display_members = members[:DETAILS_DISPLAY_LIMIT]
    affiliation_map = _fetch_affiliation_map(display_members, conference_member_repo)

    # 当選者情報をconference_idごとに1回だけ取得してキャッシュ
    election_cache: dict[int, SearchPoliticiansOutputDTO] = {}
    for member in display_members:
        cid = member.conference_id
        if cid not in election_cache:
            election_cache[cid] = _run_async(
                manage_members_usecase.get_election_candidates(
                    GetElectionCandidatesInputDTO(conference_id=cid)
                )
            )

    for member in display_members:
        # 紐付け状態を取得
        affiliation = affiliation_map.get(member.id)  # type: ignore[arg-type]
        is_linked = affiliation is not None

        # 紐付け状態チェックボックスと名前を横並びで表示
        col1, col2 = st.columns([0.1, 0.9])
        with col1:
            st.checkbox(
                "紐付け済",
                value=is_linked,
                disabled=True,
                key=f"linked_status_{member.id}",
                label_visibility="collapsed",
                help="紐付け実施済み" if is_linked else "未紐付け",
            )
        with col2:
            with st.expander(f"{member.extracted_name}"):
                st.write(f"**ID:** {member.id}")
                st.write(f"**名前:** {member.extracted_name}")
                st.write(f"**役職:** {member.extracted_role or '-'}")
                st.write(f"**政党:** {member.extracted_party_name or '-'}")

                _render_affiliation_info(
                    member, affiliation_map, conference_member_repo
                )

                # 手動政治家選択UI（所属情報が未作成の場合）
                if not is_linked:
                    cached = election_cache.get(member.conference_id)
                    _render_manual_match(member, manage_members_usecase, cached)


def _render_manual_match(
    member: ExtractedConferenceMember,
    manage_members_usecase: ManageConferenceMembersUseCase,
    election_candidates_result: SearchPoliticiansOutputDTO | None = None,
) -> None:
    """手動政治家選択UIを表示する.

    会議体にelection_idが設定されている場合、当選者を優先表示します。
    「当選者以外も表示」チェックボックスで全政治家の名前検索も可能です。
    election_idが未設定の場合は従来通り名前検索のみ表示します。

    Args:
        member: メンバーエンティティ
        manage_members_usecase: 会議体メンバー管理UseCase
        election_candidates_result: キャッシュ済み当選者候補
    """
    st.markdown("---")
    st.markdown("**手動で政治家を選択**")

    if election_candidates_result is None:
        election_candidates_result = SearchPoliticiansOutputDTO(candidates=[])
    has_election_candidates = len(election_candidates_result.candidates) > 0

    if has_election_candidates:
        show_all = st.checkbox(
            "当選者以外も表示",
            key=f"show_all_politicians_{member.id}",
        )
    else:
        show_all = True

    candidate_options: dict[str, int | None] = {
        "-- 選択してください --": None,
    }

    if has_election_candidates and not show_all:
        for c in election_candidates_result.candidates:
            label = f"{c.name} (ID: {c.id})"
            candidate_options[label] = c.id
    else:
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
                return

            if has_election_candidates:
                election_ids = {c.id for c in election_candidates_result.candidates}
                elected = [c for c in search_result.candidates if c.id in election_ids]
                others = [
                    c for c in search_result.candidates if c.id not in election_ids
                ]
                if elected:
                    for c in elected:
                        label = f"⭐ {c.name} (ID: {c.id})"
                        candidate_options[label] = c.id
                for c in others:
                    label = f"{c.name} (ID: {c.id})"
                    candidate_options[label] = c.id
            else:
                for c in search_result.candidates:
                    label = f"{c.name} (ID: {c.id})"
                    candidate_options[label] = c.id
        else:
            return

    if len(candidate_options) <= 1:
        return

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
                output = _run_async(manage_members_usecase.manual_match(input_dto))
                if output.success:
                    st.success(output.message)
                    st.rerun()
                else:
                    st.error(output.message)
