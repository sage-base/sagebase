"""Duplicate management subtab for parliamentary group members.

議員団メンバーの重複管理サブタブのUI実装を提供します。
"""

import asyncio

from collections import defaultdict
from typing import Any

import streamlit as st

from sqlalchemy import text

from src.infrastructure.persistence import (
    extracted_parliamentary_group_member_repository_impl as epgmr_impl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter import (  # noqa: E501
    ParliamentaryGroupMemberPresenter,
)


def render_duplicate_management_subtab(
    presenter: ParliamentaryGroupMemberPresenter,
) -> None:
    """Render the duplicate management sub-tab.

    議員団メンバーの重複管理サブタブをレンダリングします。
    同じ名前の抽出メンバーを検出し、重複を解消する機能を提供します。

    Args:
        presenter: 議員団メンバープレゼンター
    """
    st.markdown("### 重複メンバー管理")
    st.markdown("同じ議員団内で同じ名前の抽出メンバーを検出し、重複を解消します。")

    # Note about automatic prevention
    st.info(
        "📝 注意: 新しい抽出では重複は自動的に防止されます。"
        "このツールは既存の重複レコードを管理するためのものです。"
    )

    try:
        # Get all parliamentary groups
        parliamentary_groups = presenter.get_all_parliamentary_groups()

        if not parliamentary_groups:
            st.warning("議員団が登録されていません")
            return

        # Create dictionary for group selection
        group_options = {
            f"{g.name} (ID: {g.id})": g.id
            for g in parliamentary_groups
            if g.name and g.id
        }

        selected_group = st.selectbox(
            "議員団を選択",
            options=list(group_options.keys()),
            key="duplicate_group_select",
        )

        if selected_group:
            group_id = group_options[selected_group]
            _display_duplicates_for_group(group_id)

    except Exception as e:
        st.error(f"重複管理中にエラーが発生しました: {e}")
        import traceback

        st.code(traceback.format_exc())


def _display_duplicates_for_group(group_id: int) -> None:
    """Display and manage duplicates for a specific group.

    Args:
        group_id: 議員団ID
    """
    repo_adapter = RepositoryAdapter(
        epgmr_impl.ExtractedParliamentaryGroupMemberRepositoryImpl
    )

    try:
        members = repo_adapter.get_by_parliamentary_group(group_id)

        if not members:
            st.info("この議員団には抽出されたメンバーがいません")
            return

        # Find duplicates by name
        members_by_name: dict[str, list[Any]] = defaultdict(list)
        for member in members:
            members_by_name[member.extracted_name].append(member)

        # Filter to only show duplicates (names with more than 1 record)
        duplicates = {
            name: member_list
            for name, member_list in members_by_name.items()
            if len(member_list) > 1
        }

        if not duplicates:
            st.success("✅ 重複レコードは見つかりませんでした")
            return

        st.warning(f"⚠️ {len(duplicates)}件の重複する名前が見つかりました")

        # Display each duplicate group
        for name, duplicate_members in duplicates.items():
            _display_duplicate_group(name, duplicate_members, repo_adapter)

    finally:
        repo_adapter.close()


def _display_duplicate_group(
    name: str,
    duplicate_members: list[Any],
    repo_adapter: RepositoryAdapter,
) -> None:
    """Display a group of duplicate members.

    Args:
        name: 重複している名前
        duplicate_members: 重複メンバーのリスト
        repo_adapter: リポジトリアダプター
    """
    st.markdown(f"#### {name} ({len(duplicate_members)}件のレコード)")

    # Display each duplicate record
    for i, member in enumerate(duplicate_members, 1):
        with st.expander(
            f"レコード {i} (ID: {member.id}) - "
            f"抽出日: {member.extracted_at.strftime('%Y-%m-%d %H:%M')}"
        ):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.write(f"**名前:** {member.extracted_name}")
                st.write(f"**役職:** {member.extracted_role or 'なし'}")
                st.write(f"**政党:** {member.extracted_party_name or 'なし'}")
                st.write(f"**選挙区:** {member.extracted_district or 'なし'}")
                st.write(f"**マッチング状態:** {member.matching_status}")
                if member.matched_politician_id:
                    st.write(
                        f"**マッチング済み政治家ID:** {member.matched_politician_id}"
                    )
                st.write(f"**ソースURL:** {member.source_url}")

            with col2:
                # Delete button for each record
                if st.button(
                    "🗑️ 削除",
                    key=f"delete_member_{member.id}",
                    type="secondary",
                ):
                    _delete_member(member.id, repo_adapter)

    st.markdown("---")


def _delete_member(member_id: int, repo_adapter: RepositoryAdapter) -> None:
    """Delete a member record.

    Args:
        member_id: メンバーID
        repo_adapter: リポジトリアダプター
    """
    try:
        # Create an async function to delete
        async def delete_member_async(mid: int) -> None:
            session_factory = repo_adapter.get_async_session_factory()
            async with session_factory() as session:
                delete_query = text(
                    """
                    DELETE FROM extracted_parliamentary_group_members
                    WHERE id = :member_id
                """
                )
                await session.execute(delete_query, {"member_id": mid})
                await session.commit()

        # Run the async delete
        asyncio.run(delete_member_async(member_id))

        st.success(f"レコードID {member_id} を削除しました")
        st.rerun()
    except Exception as e:
        st.error(f"削除エラー: {e}")
