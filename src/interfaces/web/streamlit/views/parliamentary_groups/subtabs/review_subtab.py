"""Review subtab for parliamentary group members.

議員団メンバーレビューサブタブのUI実装を提供します。
"""

import logging

from typing import Any

import streamlit as st

from src.interfaces.web.streamlit.components import render_verification_filter
from src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter import (  # noqa: E501
    ParliamentaryGroupMemberPresenter,
)


logger = logging.getLogger(__name__)


def render_member_review_subtab(presenter: ParliamentaryGroupMemberPresenter) -> None:
    """Render the member review sub-tab.

    議員団メンバーのレビューサブタブをレンダリングします。
    メンバーのフィルタリング、一括操作、個別操作などの機能を提供します。

    Args:
        presenter: 議員団メンバープレゼンター
    """
    st.markdown("### 抽出メンバーレビュー")

    # Display success/error messages from session state
    if "review_success_message" in st.session_state:
        st.success(st.session_state.review_success_message)
        del st.session_state.review_success_message

    if "review_error_message" in st.session_state:
        st.error(st.session_state.review_error_message)
        del st.session_state.review_error_message

    # Get parliamentary groups for filter
    parliamentary_groups = presenter.get_all_parliamentary_groups()

    # Filters section
    members, verification_filter = _render_filters(presenter, parliamentary_groups)

    if not members:
        st.info("該当するレコードがありません")
        return

    # Filter by verification status
    if verification_filter is not None:
        members = [m for m in members if m.is_manually_verified == verification_filter]

    if not members:
        st.info("該当するレコードがありません")
        return

    # Display statistics
    st.markdown(f"### 検索結果: {len(members)}件")

    # Bulk actions
    _render_bulk_actions(presenter, members)

    # Display data table
    _render_data_table(presenter, members, parliamentary_groups)


def _render_filters(
    presenter: ParliamentaryGroupMemberPresenter,
    parliamentary_groups: list[Any],
) -> tuple[list[Any], bool | None]:
    """Render filter controls.

    Args:
        presenter: 議員団メンバープレゼンター
        parliamentary_groups: 議員団リスト

    Returns:
        tuple[list, bool | None]: (フィルタリングされたメンバー, 検証フィルター)
    """
    st.markdown("#### フィルター")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Parliamentary group filter
        group_options = ["すべて"] + [g.name for g in parliamentary_groups if g.name]
        group_map = {g.name: g.id for g in parliamentary_groups if g.id and g.name}
        selected_group = st.selectbox("議員団", group_options)
        group_id = group_map.get(selected_group) if selected_group != "すべて" else None

    with col2:
        # Status filter (multi-select)
        status_options = {
            "⏳ 紐付け未実行": "pending",
            "✅ マッチ済み": "matched",
            "❌ マッチなし": "no_match",
        }
        selected_status_labels = st.multiselect(
            "ステータス",
            options=list(status_options.keys()),
            default=["⏳ 紐付け未実行"],
        )
        selected_statuses = [status_options[label] for label in selected_status_labels]

    with col3:
        # Name search
        search_name = st.text_input("名前検索", placeholder="例: 山田")

    with col4:
        # Verification filter
        verification_filter = render_verification_filter(key="pg_member_verification")

    # Get filtered members
    members = presenter.get_filtered_extracted_members(
        parliamentary_group_id=group_id,
        statuses=selected_statuses,
        search_name=search_name if search_name else None,
        limit=100,
    )

    return members, verification_filter


def _render_bulk_actions(
    presenter: ParliamentaryGroupMemberPresenter,
    members: list[Any],
) -> None:
    """Render bulk action controls.

    Args:
        presenter: 議員団メンバープレゼンター
        members: メンバーリスト
    """
    st.markdown("### 一括アクション")
    col1, col2, col3 = st.columns(3)

    # Initialize session state for selected items
    if "selected_members" not in st.session_state:
        st.session_state.selected_members = []

    with col1:
        if st.button("全選択", key="select_all_members"):
            st.session_state.selected_members = [m.id for m in members if m.id]

    with col2:
        if st.button("選択解除", key="deselect_all_members"):
            st.session_state.selected_members = []

    with col3:
        selected_count = len(st.session_state.selected_members)
        st.metric("選択数", f"{selected_count}件")

    # Bulk action buttons
    if selected_count > 0:
        st.markdown("#### 選択したレコードに対する操作")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("一括承認", type="primary", key="bulk_approve_members"):
                with st.spinner("承認処理中..."):
                    success, failed, message = presenter.bulk_review(
                        st.session_state.selected_members, "approve"
                    )
                    if success > 0:
                        st.success(f"✅ {success}件を承認しました")
                    if failed > 0:
                        st.error(f"❌ {failed}件の承認に失敗しました")
                    st.session_state.selected_members = []
                    st.rerun()

        with col2:
            if st.button("一括却下", key="bulk_reject_members"):
                with st.spinner("却下処理中..."):
                    success, failed, message = presenter.bulk_review(
                        st.session_state.selected_members, "reject"
                    )
                    if success > 0:
                        st.success(f"✅ {success}件を却下しました")
                    if failed > 0:
                        st.error(f"❌ {failed}件の却下に失敗しました")
                    st.session_state.selected_members = []
                    st.rerun()


def _render_data_table(
    presenter: ParliamentaryGroupMemberPresenter,
    members: list[Any],
    parliamentary_groups: list[Any],
) -> None:
    """Render the data table with member details.

    Args:
        presenter: 議員団メンバープレゼンター
        members: メンバーリスト
        parliamentary_groups: 議員団リスト
    """
    st.markdown("### データ一覧")

    # Convert to DataFrame for display
    df = presenter.to_dataframe(members, parliamentary_groups)

    if df is not None:
        # Add checkboxes for each row
        for idx, member in enumerate(members):
            if member.id is None:
                continue

            col1, col2 = st.columns([1, 9])

            with col1:
                selected = st.checkbox(
                    "選択",
                    key=f"check_member_{member.id}",
                    value=member.id in st.session_state.selected_members,
                    label_visibility="hidden",
                )
                if selected and member.id not in st.session_state.selected_members:
                    st.session_state.selected_members.append(member.id)
                elif not selected and member.id in st.session_state.selected_members:
                    st.session_state.selected_members.remove(member.id)

            with col2:
                status = df.iloc[idx]["ステータス"]
                group = df.iloc[idx]["議員団"]
                with st.expander(f"{member.extracted_name} ({group}) - {status}"):
                    _render_member_detail(presenter, member, df.iloc[idx])


def _render_member_detail(
    presenter: ParliamentaryGroupMemberPresenter,
    member: Any,
    df_row: Any,
) -> None:
    """Render member detail view.

    Args:
        presenter: 議員団メンバープレゼンター
        member: メンバーエンティティ
        df_row: DataFrameの行
    """
    # Display details
    col_a, col_b = st.columns(2)
    with col_a:
        st.write(f"**ID:** {member.id}")
        st.write(f"**名前:** {member.extracted_name}")
        st.write(f"**役職:** {member.extracted_role or '-'}")
        st.write(f"**政党:** {member.extracted_party_name or '-'}")
        st.write(f"**選挙区:** {member.extracted_district or '-'}")

    with col_b:
        st.write(f"**議員団:** {df_row['議員団']}")
        st.write(f"**ステータス:** {df_row['ステータス']}")
        st.write(f"**検証状態:** {df_row['検証状態']}")
        st.write(f"**マッチした政治家:** {df_row['マッチした政治家']}")
        st.write(f"**信頼度:** {df_row['信頼度']}")
        st.write(f"**抽出日時:** {df_row['抽出日時']}")

    # Verification status update section
    _render_verification_section(presenter, member)

    # Individual action buttons
    _render_action_buttons(presenter, member)


def _render_verification_section(
    presenter: ParliamentaryGroupMemberPresenter,
    member: Any,
) -> None:
    """Render verification status update section.

    Args:
        presenter: 議員団メンバープレゼンター
        member: メンバーエンティティ
    """
    st.markdown("---")
    st.markdown("##### 検証状態")
    verify_col1, verify_col2 = st.columns([2, 1])

    with verify_col1:
        current_verified = member.is_manually_verified
        new_verified = st.checkbox(
            "手動検証済みとしてマーク",
            value=current_verified,
            key=f"verify_pg_member_{member.id}",
            help="チェックすると、AI再実行でこのデータが上書きされなくなります",
        )

    with verify_col2:
        if new_verified != current_verified:
            if st.button(
                "更新",
                key=f"update_verify_pg_{member.id}",
                type="primary",
            ):
                success, error = presenter.update_verification_status(
                    member.id,
                    new_verified,  # type: ignore[arg-type]
                )
                if success:
                    status_text = "手動検証済み" if new_verified else "未検証"
                    st.session_state["review_success_message"] = (
                        f"検証状態を「{status_text}」に更新しました"
                    )
                    st.rerun()
                else:
                    st.session_state["review_error_message"] = (
                        f"更新に失敗しました: {error}"
                    )


def _render_action_buttons(
    presenter: ParliamentaryGroupMemberPresenter,
    member: Any,
) -> None:
    """Render individual action buttons.

    Args:
        presenter: 議員団メンバープレゼンター
        member: メンバーエンティティ
    """
    st.markdown("---")
    col_1, col_2, col_3 = st.columns(3)

    with col_1:
        if st.button(
            "✅ 承認",
            key=f"approve_member_{member.id}",
            type="primary",
            disabled=member.matching_status != "matched",
            help=(
                "マッチ済みのメンバーのみ承認できます"
                if member.matching_status != "matched"
                else "このメンバーを承認します"
            ),
        ):
            if member.id is not None:
                success, message = presenter.review_extracted_member(
                    member.id, "approve"
                )
                if success:
                    st.session_state["review_success_message"] = message
                else:
                    st.session_state["review_error_message"] = message
                st.rerun()

    with col_2:
        if st.button("❌ 却下", key=f"reject_member_{member.id}"):
            if member.id is not None:
                success, message = presenter.review_extracted_member(
                    member.id, "reject"
                )
                if success:
                    st.session_state["review_success_message"] = message
                else:
                    st.session_state["review_error_message"] = message
                st.rerun()

    with col_3:
        if st.button("🔗 手動マッチ", key=f"manual_match_{member.id}"):
            st.session_state[f"matching_{member.id}"] = True

    # Manual matching dialog
    if st.session_state.get(f"matching_{member.id}", False):
        _render_manual_matching_dialog(presenter, member)


def _render_manual_matching_dialog(
    presenter: ParliamentaryGroupMemberPresenter,
    member: Any,
) -> None:
    """Render manual matching dialog.

    Args:
        presenter: 議員団メンバープレゼンター
        member: メンバーエンティティ
    """
    with st.container():
        st.markdown("#### 手動マッチング")

        # Search filters
        search_col1, search_col2 = st.columns(2)

        with search_col1:
            search_politician_name = st.text_input(
                "政治家名で検索",
                value=member.extracted_name,
                key=f"search_pol_{member.id}",
            )

        with search_col2:
            # Get all political parties for filter options
            all_political_parties = presenter.get_all_political_parties()
            party_filter_options = ["すべて", "無所属"] + [
                p.name for p in all_political_parties if p.name
            ]

            # Set default to extracted party if available
            default_index = 0
            if member.extracted_party_name:
                try:
                    default_index = party_filter_options.index(
                        member.extracted_party_name
                    )
                except ValueError:
                    default_index = 0

            selected_party_filter = st.selectbox(
                "政党で絞り込み",
                party_filter_options,
                index=default_index,
                key=f"party_filter_{member.id}",
            )

        # Initialize search result state
        search_key = f"search_results_{member.id}"
        if search_key not in st.session_state:
            st.session_state[search_key] = None

        if st.button("検索", key=f"search_button_{member.id}", type="primary"):
            _execute_politician_search(
                presenter,
                member,
                search_politician_name or "",
                selected_party_filter,
                search_key,
            )

        # Display search results from session state
        politicians = st.session_state[search_key]

        if politicians is not None:
            _display_search_results(presenter, member, politicians, search_key)


def _execute_politician_search(
    presenter: ParliamentaryGroupMemberPresenter,
    member: Any,
    search_name: str,
    party_filter: str,
    search_key: str,
) -> None:
    """Execute politician search.

    Args:
        presenter: 議員団メンバープレゼンター
        member: メンバーエンティティ
        search_name: 検索名
        party_filter: 政党フィルター
        search_key: セッション状態のキー
    """
    # Search with name only (party filtering done below)
    politicians = presenter.search_politicians(search_name, None)

    # Filter by party name if specified
    if party_filter != "すべて" and politicians:
        # Get party names for filtering
        filtered_politicians = []
        for p in politicians:
            if p.political_party_id:
                party_name = presenter.get_party_name_by_id(p.political_party_id)
                if party_filter.lower() in party_name.lower():
                    filtered_politicians.append(p)
            elif party_filter == "無所属":
                filtered_politicians.append(p)
        politicians = filtered_politicians

    # Store search results in session state
    st.session_state[search_key] = politicians


def _display_search_results(
    presenter: ParliamentaryGroupMemberPresenter,
    member: Any,
    politicians: list[Any],
    search_key: str,
) -> None:
    """Display politician search results.

    Args:
        presenter: 議員団メンバープレゼンター
        member: メンバーエンティティ
        politicians: 政治家リスト
        search_key: セッション状態のキー
    """
    if politicians:
        st.markdown(f"**検索結果: {len(politicians)}件**")

        # Display politician options with party names
        def format_politician(p: Any) -> str:
            party_name = "無所属"
            if p.political_party_id:
                party_name = presenter.get_party_name_by_id(p.political_party_id)
            district = p.district or "-"
            return f"{p.name} ({party_name}) - {district}"

        politician_options = [format_politician(p) for p in politicians]
        politician_map = {format_politician(p): p.id for p in politicians if p.id}

        selected_politician = st.selectbox(
            "マッチする政治家を選択",
            politician_options,
            key=f"select_pol_{member.id}",
        )

        # Confidence score
        confidence = st.slider(
            "信頼度",
            min_value=0.0,
            max_value=1.0,
            value=0.8,
            step=0.05,
            key=f"confidence_{member.id}",
        )

        # Match button
        col_match, col_cancel = st.columns(2)
        with col_match:
            if st.button(
                "マッチング実行",
                key=f"execute_match_{member.id}",
                type="primary",
            ):
                _execute_matching(
                    presenter,
                    member,
                    politician_map[selected_politician],
                    confidence,
                    search_key,
                )

        with col_cancel:
            if st.button("キャンセル", key=f"cancel_match_{member.id}"):
                st.session_state[f"matching_{member.id}"] = False
                del st.session_state[search_key]
                st.rerun()
    else:
        st.warning("該当する政治家が見つかりませんでした")
        if st.button("閉じる", key=f"close_no_results_{member.id}"):
            st.session_state[f"matching_{member.id}"] = False
            del st.session_state[search_key]
            st.rerun()


def _execute_matching(
    presenter: ParliamentaryGroupMemberPresenter,
    member: Any,
    politician_id: int,
    confidence: float,
    search_key: str,
) -> None:
    """Execute the matching operation.

    Args:
        presenter: 議員団メンバープレゼンター
        member: メンバーエンティティ
        politician_id: 政治家ID
        confidence: 信頼度
        search_key: セッション状態のキー
    """
    logger.info(f"Match button clicked for member {member.id}")
    logger.info(
        f"Calling review_extracted_member: "
        f"member_id={member.id}, "
        f"politician_id={politician_id}, "
        f"confidence={confidence}"
    )

    if member.id is not None:
        success, message = presenter.review_extracted_member(
            member.id,
            "match",
            politician_id,
            confidence,
        )

        logger.info(
            f"review_extracted_member returned: success={success}, message={message}"
        )

        if success:
            st.session_state["review_success_message"] = message
            st.session_state[f"matching_{member.id}"] = False
            if search_key in st.session_state:
                del st.session_state[search_key]
            st.rerun()
        else:
            st.session_state["review_error_message"] = message
            st.session_state[f"matching_{member.id}"] = False
            if search_key in st.session_state:
                del st.session_state[search_key]
            st.rerun()
