"""Matching tab for conversations.

発言マッチングタブのUI実装を提供します。
"""

import asyncio

import streamlit as st

from ..components.politician_creation_form import render_politician_creation_form

from src.application.dtos.speaker_dto import SpeakerMatchingDTO
from src.application.usecases.authenticate_user_usecase import (
    AuthenticateUserUseCase,
)
from src.infrastructure.di.container import Container
from src.infrastructure.persistence.conversation_repository_impl import (
    ConversationRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.auth import google_sign_in


def render_matching_tab() -> None:
    """Render the matching tab.

    発言マッチングタブをレンダリングします。
    LLMによる発言者と政治家のマッチング機能を提供します。
    """
    st.subheader("発言マッチング")

    st.markdown("""
    ### LLMによる発言者マッチング

    発言者と政治家のマッチングを行います。
    """)

    # Get user info
    user_info: dict[str, str] | None = google_sign_in.get_user_info()
    if not user_info:
        st.warning("ユーザー情報を取得できません。ログインしてください。")
        return

    # Display current user
    user_name = user_info.get("name", "Unknown")
    user_email = user_info.get("email", "Unknown")
    st.info(f"実行ユーザー: {user_name} ({user_email})")

    # 会議選択フィルター
    meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)
    conversation_repo = RepositoryAdapter(ConversationRepositoryImpl)

    meetings = meeting_repo.get_all()
    meeting_options: dict[str, int | None] = {"すべて": None}
    meeting_options.update({m.name or f"会議 {m.id}": m.id for m in meetings[:100]})

    col1, col2 = st.columns([2, 1])
    with col1:
        selected_meeting = st.selectbox(
            "会議選択",
            list(meeting_options.keys()),
            key="matching_meeting_filter",
            help="マッチング対象の会議を選択します",
        )
        meeting_id = meeting_options[selected_meeting]

    with col2:
        limit = st.number_input(
            "処理件数上限",
            min_value=1,
            max_value=100,
            value=10,
            key="matching_limit",
            help="一度に処理する発言者数の上限",
        )

    # 選択した会議の発言者数を表示
    if meeting_id:
        conversations = conversation_repo.get_by_meeting(meeting_id, limit=1000)
        speaker_ids = list({c.speaker_id for c in conversations if c.speaker_id})
        st.caption(f"選択した会議の発言者数: {len(speaker_ids)}名")
    else:
        speaker_ids = None
        st.caption("すべての発言者を対象とします")

    if st.button("マッチング実行", type="primary"):
        _execute_matching(user_info, speaker_ids, int(limit))

    # マッチング結果の表示
    _display_matching_results()


def _execute_matching(
    user_info: dict[str, str],
    speaker_ids: list[int] | None,
    limit: int,
) -> None:
    """Execute speaker matching.

    Args:
        user_info: ユーザー情報
        speaker_ids: 発言者IDリスト（Noneの場合は全て）
        limit: 処理件数上限
    """
    with st.spinner("マッチング処理を実行中..."):
        try:
            # Get container for repositories and use cases
            container = Container.create_for_environment()

            # Initialize use cases
            auth_usecase = AuthenticateUserUseCase(
                user_repository=container.repositories.user_repository()
            )
            # DIコンテナからMatchSpeakersUseCaseを取得
            match_usecase = container.use_cases.match_speakers_usecase()

            # Authenticate user and get user_id
            email = user_info.get("email", "")
            name = user_info.get("name")
            user = asyncio.run(auth_usecase.execute(email=email, name=name))

            # Execute matching with user_id
            # 会議が選択されている場合はspeaker_idsを渡す
            results = asyncio.run(
                match_usecase.execute(
                    use_llm=True,
                    speaker_ids=speaker_ids,
                    limit=limit if not speaker_ids else None,
                    user_id=user.user_id,
                )
            )

            # マッチング結果をsession_stateに保存
            st.session_state["matching_results"] = results
            st.session_state["matching_user_id"] = user.user_id

            # Display results
            st.success(
                f"マッチング処理が完了しました。{len(results)}件の発言者を処理しました。"
            )

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            import traceback

            st.code(traceback.format_exc())


def _display_matching_results() -> None:
    """Display matching results from session state."""
    results: list[SpeakerMatchingDTO] = st.session_state.get("matching_results", [])
    if results:
        # Show summary
        matched_count = sum(1 for r in results if r.matched_politician_id)
        st.metric("マッチング成功", f"{matched_count}/{len(results)}")

        # Show details in expandable section
        with st.expander("マッチング詳細", expanded=True):
            for result in results:
                if result.matched_politician_id:
                    # マッチ成功: 従来通りの表示
                    st.write(
                        f"✅ {result.speaker_name} → {result.matched_politician_name} "
                        f"({result.matching_method}, "
                        f"信頼度: {result.confidence_score:.2f})"
                    )
                else:
                    # 未マッチ: 政治家作成サジェストを表示
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(
                            f"❌ {result.speaker_name} → マッチなし "
                            f"({result.matching_method}, "
                            f"信頼度: {result.confidence_score:.2f})"
                        )
                    with col2:
                        form_key = f"show_form_{result.speaker_id}"
                        if st.button(
                            "🆕 政治家を新規作成",
                            key=f"create_pol_btn_{result.speaker_id}",
                        ):
                            st.session_state[form_key] = True
                            st.rerun()

                    # 作成フォームの表示
                    if st.session_state.get(form_key, False):
                        render_politician_creation_form(
                            result=result,
                            user_id=st.session_state.get("matching_user_id"),
                        )
