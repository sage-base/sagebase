"""Speakers list tab for conversations.

発言者一覧タブのUI実装を提供します。
未マッチSpeakerの確認・手動紐付け・非政治家分類の機能を提供します。
"""

import asyncio

from uuid import UUID

import pandas as pd
import streamlit as st

from src.application.usecases.authenticate_user_usecase import (
    AuthenticateUserUseCase,
)
from src.application.usecases.link_speaker_to_politician_usecase import (
    LinkSpeakerToPoliticianInputDto,
)
from src.application.usecases.mark_speaker_as_non_politician_usecase import (
    MarkSpeakerAsNonPoliticianInputDto,
)
from src.domain.services.speaker_classifier import SkipReason
from src.domain.value_objects.speaker_with_conversation_count import (
    SpeakerWithConversationCount,
)
from src.infrastructure.di.container import Container
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.infrastructure.persistence.speaker_repository_impl import (
    SpeakerRepositoryImpl,
)
from src.interfaces.web.streamlit.auth import google_sign_in


# 詳細操作セクションに表示するSpeakerの最大数（パフォーマンスのため制限）
_MAX_DETAIL_SPEAKERS = 30


def render_speakers_list_tab() -> None:
    """Render the speakers list tab.

    発言者一覧タブをレンダリングします。
    未マッチSpeakerの手動紐付け・非政治家分類の機能を提供します。
    """
    st.subheader("発言者一覧")

    speaker_repo = RepositoryAdapter(SpeakerRepositoryImpl)
    politician_repo = RepositoryAdapter(PoliticianRepositoryImpl)

    # フィルタ行
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        name_search = st.text_input(
            "名前検索", key="spk_name_search", placeholder="名前で検索..."
        )

    with col2:
        match_options = {"すべて": None, "未マッチ": False, "マッチ済み": True}
        selected_match = st.selectbox(
            "マッチ状態",
            list(match_options.keys()),
            key="spk_match_filter",
        )
        has_politician_id = match_options[selected_match]

    with col3:
        skip_reason_options: dict[str, str | None] = {
            "すべて": None,
            "未分類": "__none__",
        }
        for sr in SkipReason:
            skip_reason_options[sr.display_label] = sr.value
        selected_skip = st.selectbox(
            "分類状態",
            list(skip_reason_options.keys()),
            key="spk_skip_filter",
        )
        skip_reason_filter = skip_reason_options[selected_skip]

    with col4:
        limit = st.number_input(
            "表示件数",
            min_value=10,
            max_value=500,
            value=50,
            key="spk_limit",
        )

    # データ取得
    speakers: list[SpeakerWithConversationCount] = (
        speaker_repo.get_speakers_with_conversation_count(
            limit=int(limit),
            name_search=name_search or None,
            has_politician_id=has_politician_id,
            skip_reason=skip_reason_filter,
        )
    )

    if not speakers:
        st.info("該当する発言者がありません")
        return

    # 統計メトリクス（表示中のデータに基づく）
    total = len(speakers)
    matched = unmatched = non_politician = 0
    for s in speakers:
        if s.politician_id is not None:
            matched += 1
        elif s.is_politician:
            unmatched += 1
        else:
            non_politician += 1

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("表示中", f"{total}件")
    with col2:
        st.metric("マッチ済み", f"{matched}件")
    with col3:
        st.metric("未マッチ", f"{unmatched}件")
    with col4:
        st.metric("非政治家", f"{non_politician}件")

    # テーブル表示
    data = []
    for s in speakers:
        status = _get_match_status(s)
        classification = _get_classification_label(s)
        data.append(
            {
                "ID": s.id,
                "名前": s.name,
                "読み": s.name_yomi or "-",
                "発言数": s.conversation_count,
                "政党": s.political_party_name or "-",
                "状態": status,
                "分類": classification,
            }
        )

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 詳細セクション
    _render_speaker_detail_section(speakers, speaker_repo, politician_repo)


def _get_match_status(speaker: SpeakerWithConversationCount) -> str:
    """マッチ状態のラベルを返す."""
    if speaker.politician_id is not None:
        if speaker.is_manually_verified:
            return "手動マッチ済み"
        return "自動マッチ済み"
    if not speaker.is_politician:
        return "非政治家"
    return "未マッチ"


def _get_classification_label(speaker: SpeakerWithConversationCount) -> str:
    """分類ラベルを返す."""
    if speaker.skip_reason:
        try:
            return SkipReason(speaker.skip_reason).display_label
        except ValueError:
            return speaker.skip_reason
    return "-"


def _render_speaker_detail_section(
    speakers: list[SpeakerWithConversationCount],
    speaker_repo: RepositoryAdapter,
    politician_repo: RepositoryAdapter,
) -> None:
    """発言者の詳細操作セクションを表示する."""
    st.markdown("### 個別操作")

    if len(speakers) > _MAX_DETAIL_SPEAKERS:
        st.caption(f"上位{_MAX_DETAIL_SPEAKERS}件の操作パネルを表示しています")

    for speaker in speakers[:_MAX_DETAIL_SPEAKERS]:
        status = _get_match_status(speaker)
        with st.expander(
            f"{speaker.name}（発言{speaker.conversation_count}回）— {status}"
        ):
            _render_speaker_actions(speaker, speaker_repo, politician_repo)


def _render_speaker_actions(
    speaker: SpeakerWithConversationCount,
    speaker_repo: RepositoryAdapter,
    politician_repo: RepositoryAdapter,
) -> None:
    """個別Speakerの操作UIを表示する."""
    # 現在の情報
    col_info, col_action = st.columns([1, 2])

    with col_info:
        st.markdown("**現在の情報**")
        st.write(f"ID: {speaker.id}")
        st.write(f"読み: {speaker.name_yomi or '未設定'}")
        st.write(f"政党: {speaker.political_party_name or '未設定'}")
        st.write(f"役職: {speaker.position or '未設定'}")
        if speaker.matching_confidence is not None:
            st.write(f"信頼度: {speaker.matching_confidence:.2f}")

    with col_action:
        tab_match, tab_classify = st.tabs(["政治家にマッチ", "非政治家として分類"])

        with tab_match:
            _render_politician_match_section(speaker, politician_repo)

        with tab_classify:
            _render_non_politician_section(speaker)


def _render_politician_match_section(
    speaker: SpeakerWithConversationCount,
    politician_repo: RepositoryAdapter,
) -> None:
    """政治家マッチセクションを表示する."""
    search_query = st.text_input(
        "候補政治家を検索",
        value=speaker.name,
        key=f"pol_search_{speaker.id}",
        placeholder="政治家名を入力...",
    )

    if search_query:
        candidates = politician_repo.search_by_name(search_query)
        if candidates:
            st.caption(f"{len(candidates)}件の候補が見つかりました")
            for candidate in candidates[:10]:
                col_name, col_detail, col_btn = st.columns([2, 2, 1])
                with col_name:
                    st.write(f"**{candidate.name}**")
                with col_detail:
                    details = []
                    if candidate.furigana:
                        details.append(candidate.furigana)
                    if candidate.prefecture:
                        details.append(candidate.prefecture)
                    if candidate.district:
                        details.append(candidate.district)
                    st.write(" / ".join(details) if details else "-")
                with col_btn:
                    if st.button(
                        "マッチ",
                        key=f"match_{speaker.id}_{candidate.id}",
                        type="primary",
                    ):
                        _execute_link(speaker.id, candidate.id, candidate.name)
        else:
            st.info("候補が見つかりません")


def _render_non_politician_section(
    speaker: SpeakerWithConversationCount,
) -> None:
    """非政治家分類セクションを表示する."""
    skip_reason_choices = {
        sr.display_label: sr.value for sr in SkipReason if sr != SkipReason.HOMONYM
    }
    selected_reason = st.selectbox(
        "分類理由",
        list(skip_reason_choices.keys()),
        key=f"skip_reason_{speaker.id}",
    )

    if st.button(
        "非政治家としてマーク",
        key=f"mark_non_pol_{speaker.id}",
        type="secondary",
    ):
        _execute_mark_non_politician(speaker.id, skip_reason_choices[selected_reason])


def _execute_link(speaker_id: int, politician_id: int, politician_name: str) -> None:
    """政治家紐付けを実行する."""
    try:
        container = Container.create_for_environment()

        user_info = google_sign_in.get_user_info()
        user_id = _get_user_id(user_info, container)

        usecase = container.use_cases.link_speaker_to_politician_usecase()

        result = asyncio.run(
            usecase.execute(
                LinkSpeakerToPoliticianInputDto(
                    speaker_id=speaker_id,
                    politician_id=politician_id,
                    politician_name=politician_name,
                    user_id=user_id,
                )
            )
        )

        if result.success:
            st.success(f"{politician_name} にマッチしました")
            st.rerun()
        else:
            st.error(f"マッチに失敗しました: {result.error_message}")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")


def _execute_mark_non_politician(speaker_id: int, skip_reason: str) -> None:
    """非政治家分類を実行する."""
    try:
        container = Container.create_for_environment()
        usecase = container.use_cases.mark_speaker_as_non_politician_usecase()

        result = asyncio.run(
            usecase.execute(
                MarkSpeakerAsNonPoliticianInputDto(
                    speaker_id=speaker_id,
                    skip_reason=skip_reason,
                )
            )
        )

        if result.success:
            st.success("非政治家としてマークしました")
            st.rerun()
        else:
            st.error(f"分類に失敗しました: {result.error_message}")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")


def _get_user_id(
    user_info: dict[str, str] | None, container: Container | None = None
) -> UUID | None:
    """ユーザー情報からユーザーIDを取得する."""
    if not user_info:
        return None
    try:
        if container is None:
            container = Container.create_for_environment()
        auth_usecase = AuthenticateUserUseCase(
            user_repository=container.repositories.user_repository()
        )
        email = user_info.get("email", "")
        name = user_info.get("name")
        user = asyncio.run(auth_usecase.execute(email=email, name=name))
        return user.user_id
    except Exception:
        return None
