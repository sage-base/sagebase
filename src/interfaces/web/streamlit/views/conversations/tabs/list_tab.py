"""List tab for conversations.

発言一覧タブのUI実装を提供します。
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
from src.infrastructure.persistence.conversation_repository_impl import (
    ConversationRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.components import (
    get_verification_badge_text,
    render_verification_filter,
)


def render_conversations_list_tab() -> None:
    """Render the conversations list tab.

    発言一覧タブをレンダリングします。
    会議でのフィルタリング、発言者名での検索、検証状態の更新などの機能を提供します。
    """
    st.subheader("発言一覧")

    # Initialize repositories
    conversation_repo = RepositoryAdapter(ConversationRepositoryImpl)
    meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)

    # Get all meetings for filter
    meetings = meeting_repo.get_all()
    meeting_options: dict[str, int | None] = {"すべて": None}
    meeting_options.update({m.name or f"会議 {m.id}": m.id for m in meetings[:100]})

    # Filters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        selected_meeting = st.selectbox(
            "会議選択", list(meeting_options.keys()), key="conv_meeting_filter"
        )
        meeting_id = meeting_options[selected_meeting]

    with col2:
        search_text = st.text_input("発言者名で検索", key="conv_speaker_search")

    with col3:
        limit = st.number_input(
            "表示件数", min_value=10, max_value=500, value=50, key="conv_limit"
        )

    with col4:
        verification_filter = render_verification_filter(key="conv_verification")

    # Load conversations
    if meeting_id:
        conversations = conversation_repo.get_by_meeting(meeting_id, limit=limit)
    else:
        conversations = conversation_repo.get_all(limit=limit)

    # Filter by speaker name
    if search_text:
        conversations = [
            c
            for c in conversations
            if c.speaker_name and search_text.lower() in c.speaker_name.lower()
        ]

    # Filter by verification status
    if verification_filter is not None:
        conversations = [
            c for c in conversations if c.is_manually_verified == verification_filter
        ]

    if not conversations:
        st.info("該当する発言レコードがありません")
        return

    # Statistics
    st.markdown(f"### 検索結果: {len(conversations)}件")

    verified_count = sum(1 for c in conversations if c.is_manually_verified)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("手動検証済み", f"{verified_count}件")
    with col2:
        st.metric("未検証", f"{len(conversations) - verified_count}件")

    # Initialize verification use case
    verify_use_case = MarkEntityAsVerifiedUseCase(
        conversation_repository=conversation_repo  # type: ignore[arg-type]
    )

    # Convert to DataFrame
    data = []
    for c in conversations:
        comment_preview = c.comment[:100] + "..." if len(c.comment) > 100 else c.comment
        data.append(
            {
                "ID": c.id,
                "発言者": c.speaker_name or "-",
                "議事録ID": c.minutes_id,
                "発言内容": comment_preview,
                "検証状態": get_verification_badge_text(c.is_manually_verified),
            }
        )

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Detail and verification section
    _render_detail_section(conversations, verify_use_case)


def _render_detail_section(conversations: list[Any], verify_use_case: Any) -> None:
    """Render conversation detail and verification section.

    Args:
        conversations: 発言リスト
        verify_use_case: 検証UseCase
    """
    st.markdown("### 発言詳細と検証状態更新")

    for conversation in conversations[:20]:  # Limit to 20 for performance
        speaker = conversation.speaker_name or "-"
        comment_short = (
            conversation.comment[:50] + "..."
            if len(conversation.comment) > 50
            else conversation.comment
        )
        badge = get_verification_badge_text(conversation.is_manually_verified)
        with st.expander(f"{speaker}: {comment_short} - {badge}"):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**ID:** {conversation.id}")
                st.write(f"**発言者:** {speaker}")
                st.write(f"**議事録ID:** {conversation.minutes_id}")
                st.markdown("**発言内容:**")
                st.text_area(
                    "発言内容",
                    value=conversation.comment,
                    height=150,
                    disabled=True,
                    label_visibility="collapsed",
                    key=f"content_{conversation.id}",
                )

            with col2:
                _render_verification_control(conversation, verify_use_case)


def _render_verification_control(conversation: Any, verify_use_case: Any) -> None:
    """Render verification control for a conversation.

    Args:
        conversation: 発言エンティティ
        verify_use_case: 検証UseCase
    """
    st.markdown("#### 検証状態")
    current_verified = conversation.is_manually_verified
    new_verified = st.checkbox(
        "手動検証済み",
        value=current_verified,
        key=f"verify_conv_{conversation.id}",
        help="チェックすると、AI再実行でこのデータが上書きされなくなります",
    )

    if new_verified != current_verified:
        if st.button(
            "検証状態を更新",
            key=f"update_verify_conv_{conversation.id}",
            type="primary",
        ):
            result = asyncio.run(
                verify_use_case.execute(
                    MarkEntityAsVerifiedInputDto(
                        entity_type=EntityType.CONVERSATION,
                        entity_id=conversation.id,
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
