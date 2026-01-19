"""Politician creation form component.

未マッチ発言者に対する政治家作成フォームコンポーネントを提供します。
"""

import asyncio

from uuid import UUID

import streamlit as st

from src.application.dtos.speaker_dto import SpeakerMatchingDTO
from src.application.usecases.link_speaker_to_politician_usecase import (
    LinkSpeakerToPoliticianInputDto,
)
from src.infrastructure.di.container import Container
from src.interfaces.web.streamlit.presenters.politician_presenter import (
    PoliticianPresenter,
)
from src.interfaces.web.streamlit.views.politicians_view import PREFECTURES


def render_politician_creation_form(
    result: SpeakerMatchingDTO,
    user_id: str | None,
) -> None:
    """未マッチ発言者に対する政治家作成フォームを表示.

    発言者情報から政治家を新規作成し、発言者と紐付けるフォームを表示します。

    Args:
        result: マッチング結果DTO
        user_id: 操作ユーザーID
    """
    st.markdown("---")
    st.markdown(f"#### 🆕 「{result.speaker_name}」の政治家を新規作成")

    # DIコンテナとPresenterの初期化
    container = Container.create_for_environment()
    presenter = PoliticianPresenter(container=container)

    # 政党リストを取得
    parties = presenter.get_all_parties()
    party_options = ["無所属"] + [p.name for p in parties]
    party_map = {p.name: p.id for p in parties}

    # 発言者情報を取得（政党名の自動選択用）
    # UseCaseを通じて取得するのが理想だが、Presenterにget_speaker_by_idがないため
    # session_stateから政党名を取得（軽微な妥協）
    speaker_party_name = st.session_state.get(
        f"speaker_party_{result.speaker_id}", None
    )

    # 政党の自動選択を試行
    default_party_index = 0
    if speaker_party_name:
        # 部分一致で検索
        for i, party in enumerate(parties):
            if speaker_party_name in party.name:
                default_party_index = i + 1  # "無所属"の分オフセット
                break

    # 都道府県リスト（空文字を除く）
    prefectures = [p for p in PREFECTURES if p]

    with st.form(f"create_politician_form_{result.speaker_id}"):
        # プリフィル
        name = st.text_input("名前 *", value=result.speaker_name)
        prefecture = st.selectbox("選挙区都道府県 *", prefectures)
        selected_party = st.selectbox("政党", party_options, index=default_party_index)
        district = st.text_input("選挙区 *", placeholder="例: ○○市議会")
        profile_url = st.text_input("プロフィールURL（任意）")

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("登録して紐付け", type="primary")
        with col2:
            cancelled = st.form_submit_button("キャンセル")

        if cancelled:
            st.session_state[f"show_form_{result.speaker_id}"] = False
            st.rerun()

        if submitted:
            _handle_form_submission(
                result,
                user_id,
                presenter,
                container,
                name,
                prefecture,
                selected_party,
                district,
                profile_url,
                party_map,
            )


def _handle_form_submission(
    result: SpeakerMatchingDTO,
    user_id: str | None,
    presenter: PoliticianPresenter,
    container: Container,
    name: str,
    prefecture: str,
    selected_party: str,
    district: str,
    profile_url: str,
    party_map: dict[str, int | None],
) -> None:
    """Handle form submission for politician creation.

    Args:
        result: マッチング結果DTO
        user_id: ユーザーID
        presenter: 政治家プレゼンター
        container: DIコンテナ
        name: 名前
        prefecture: 都道府県
        selected_party: 選択された政党
        district: 選挙区
        profile_url: プロフィールURL
        party_map: 政党名からIDへのマップ
    """
    # バリデーション
    if not name:
        st.error("名前を入力してください")
        return
    if not prefecture:
        st.error("選挙区都道府県を選択してください")
        return
    if not district:
        st.error("選挙区を入力してください")
        return

    # 政党IDを取得
    party_id = party_map.get(selected_party) if selected_party != "無所属" else None

    # UUID変換
    user_uuid: UUID | None = None
    if user_id:
        try:
            user_uuid = UUID(str(user_id))
        except (ValueError, TypeError):
            pass

    # 政治家作成
    success, politician_id, error = presenter.create(
        name=name,
        prefecture=prefecture,
        party_id=party_id,
        district=district,
        profile_url=profile_url if profile_url else None,
        user_id=user_uuid,
    )

    if success and politician_id:
        _link_speaker_to_politician(result, container, politician_id, name, user_uuid)
    else:
        st.error(f"登録に失敗しました: {error}")


def _link_speaker_to_politician(
    result: SpeakerMatchingDTO,
    container: Container,
    politician_id: int,
    name: str,
    user_uuid: UUID | None,
) -> None:
    """Link speaker to created politician.

    Args:
        result: マッチング結果DTO
        container: DIコンテナ
        politician_id: 政治家ID
        name: 政治家名
        user_uuid: ユーザーUUID
    """
    # UseCaseを使用して発言者と政治家を紐付け
    link_usecase = container.use_cases.link_speaker_to_politician_usecase()
    link_result = asyncio.run(
        link_usecase.execute(
            LinkSpeakerToPoliticianInputDto(
                speaker_id=result.speaker_id,
                politician_id=politician_id,
                politician_name=name,
                user_id=user_uuid,
            )
        )
    )

    if link_result.success:
        st.success(
            f"✅ 政治家「{name}」を作成し、発言者と紐付けました（ID: {politician_id}）"
        )

        # フォームを閉じてマッチング結果を更新
        st.session_state[f"show_form_{result.speaker_id}"] = False

        # マッチング結果を更新（UseCaseから返されたDTOを使用）
        results = st.session_state.get("matching_results", [])
        for i, r in enumerate(results):
            if r.speaker_id == result.speaker_id:
                # 更新された結果を反映
                results[i] = link_result.updated_matching_dto
                break
        st.session_state["matching_results"] = results
        st.rerun()
    else:
        st.success(f"✅ 政治家「{name}」を作成しました（ID: {politician_id}）")
        st.warning(f"紐付けに失敗しました: {link_result.error_message}")
