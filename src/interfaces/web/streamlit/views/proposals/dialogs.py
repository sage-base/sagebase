"""議案管理ビューのダイアログ.

政治家新規作成ダイアログなど、複数のタブモジュールから呼び出されるダイアログを提供します。
"""

import streamlit as st

from src.interfaces.web.streamlit.presenters.politician_presenter import (
    PoliticianPresenter,
)
from src.interfaces.web.streamlit.views.politicians_view import PREFECTURES


@st.dialog("政治家を新規作成")
def show_create_politician_dialog() -> None:
    """政治家作成ダイアログを表示する."""
    politician_presenter = PoliticianPresenter()

    # 政党リストを取得
    parties = politician_presenter.get_all_parties()
    party_options = ["無所属"] + [p.name for p in parties]
    party_map = {p.name: p.id for p in parties}

    # 都道府県リスト（空文字を除く）
    prefectures = [p for p in PREFECTURES if p]

    name = st.text_input("名前 *", key="dialog_politician_name")
    prefecture = st.selectbox(
        "選挙区都道府県 *", prefectures, key="dialog_politician_prefecture"
    )
    selected_party = st.selectbox("政党", party_options, key="dialog_politician_party")
    district = st.text_input(
        "選挙区 *", placeholder="例: ○○市議会", key="dialog_politician_district"
    )
    profile_url = st.text_input(
        "プロフィールURL（任意）", key="dialog_politician_profile_url"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("登録", type="primary", use_container_width=True):
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
            party_id = (
                party_map.get(selected_party) if selected_party != "無所属" else None
            )

            # 政治家を作成
            success, politician_id, error = politician_presenter.create(
                name=name,
                prefecture=prefecture,
                party_id=party_id,
                district=district,
                profile_url=profile_url if profile_url else None,
                user_id=None,
            )

            if success and politician_id:
                st.success(f"政治家「{name}」を作成しました（ID: {politician_id}）")
                # 作成した政治家情報をsession_stateに保存
                st.session_state["created_politician_id"] = politician_id
                st.session_state["created_politician_name"] = name
                st.rerun()
            else:
                st.error(f"登録に失敗しました: {error}")

    with col2:
        if st.button("キャンセル", use_container_width=True):
            st.rerun()
