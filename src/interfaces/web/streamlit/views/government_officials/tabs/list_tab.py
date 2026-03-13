"""Government officials list tab.

政府関係者の一覧表示・検索・編集・削除機能を提供します。
"""

from datetime import date

import streamlit as st

from src.application.dtos.government_official_dto import GovernmentOfficialOutputItem
from src.interfaces.web.streamlit.presenters.government_official_presenter import (
    GovernmentOfficialPresenter,
)


def render_list_tab(presenter: GovernmentOfficialPresenter) -> None:
    """一覧タブをレンダリングする."""
    # 検索フィルタ
    name_search = st.text_input(
        "名前検索",
        key="gov_official_name_search",
        placeholder="名前で検索...",
    )

    # データ取得
    if name_search:
        officials = presenter.search(name_search)
    else:
        officials = presenter.load_data()

    if not officials:
        st.info("該当する政府関係者がありません")
        return

    # メトリクス
    st.metric("合計", f"{len(officials)}件")

    # テーブル表示
    df = presenter.to_dataframe(officials)
    if df is not None:
        st.dataframe(df, use_container_width=True, hide_index=True)

    # 詳細セクション
    st.markdown("### 個別操作")

    for official in officials[:30]:
        with st.expander(f"{official.name}（役職{len(official.positions)}件）"):
            _render_official_detail(presenter, official)


def _render_official_detail(
    presenter: GovernmentOfficialPresenter,
    official: GovernmentOfficialOutputItem,
) -> None:
    """政府関係者の詳細情報を表示する."""
    col_info, col_action = st.columns([1, 1])

    with col_info:
        st.markdown("**基本情報**")
        st.write(f"ID: {official.id}")
        st.write(f"名前: {official.name}")
        # 役職履歴
        if official.positions:
            st.markdown("**役職履歴**")
            for pos in official.positions:
                period = ""
                if pos.start_date:
                    period = f"{pos.start_date}"
                    if pos.end_date:
                        period += f" 〜 {pos.end_date}"
                    else:
                        period += " 〜 現在"
                st.write(f"- {pos.organization} / {pos.position}")
                if period:
                    st.caption(f"  期間: {period}")
                if pos.source_note:
                    st.caption(f"  備考: {pos.source_note}")

        # 紐付きSpeaker
        linked_speakers = presenter.get_linked_speakers(official.id)
        if linked_speakers:
            st.markdown("**紐付きSpeaker**")
            for s in linked_speakers:
                st.write(f"- {s.name}（発言{s.conversation_count}回）")

    with col_action:
        _render_edit_form(presenter, official)
        st.divider()
        _render_add_position_form(presenter, official)
        st.divider()
        _render_delete_button(presenter, official)


def _render_edit_form(
    presenter: GovernmentOfficialPresenter,
    official: GovernmentOfficialOutputItem,
) -> None:
    """編集フォームを表示する."""
    st.markdown("**編集**")
    with st.form(key=f"edit_official_{official.id}"):
        new_name = st.text_input("名前", value=official.name)

        if st.form_submit_button("更新"):
            success, error = presenter.update(
                id=official.id,
                name=new_name,
            )
            if success:
                st.success("更新しました")
                st.rerun()
            else:
                st.error(f"更新に失敗: {error}")


def _render_add_position_form(
    presenter: GovernmentOfficialPresenter,
    official: GovernmentOfficialOutputItem,
) -> None:
    """役職追加フォームを表示する."""
    st.markdown("**役職追加**")
    with st.form(key=f"add_pos_{official.id}"):
        org = st.text_input("組織名", key=f"pos_org_{official.id}")
        pos = st.text_input("役職名", key=f"pos_name_{official.id}")
        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input(
                "開始日",
                value=None,
                key=f"pos_start_{official.id}",
            )
        with col_end:
            end_date = st.date_input(
                "終了日",
                value=None,
                key=f"pos_end_{official.id}",
            )
        note = st.text_input("備考", key=f"pos_note_{official.id}")

        if st.form_submit_button("役職を追加"):
            if not org or not pos:
                st.error("組織名と役職名は必須です")
            else:
                # date_inputは常にdate型を返すが、デフォルト値がNoneの場合がある
                start_val: date | None = start_date if start_date else None
                end_val: date | None = end_date if end_date else None
                success, error = presenter.add_position(
                    official_id=official.id,
                    organization=org,
                    position=pos,
                    start_date=start_val,
                    end_date=end_val,
                    source_note=note or None,
                )
                if success:
                    st.success("役職を追加しました")
                    st.rerun()
                else:
                    st.error(f"追加に失敗: {error}")


def _render_delete_button(
    presenter: GovernmentOfficialPresenter,
    official: GovernmentOfficialOutputItem,
) -> None:
    """削除ボタンを表示する."""
    if st.button(
        "削除",
        key=f"del_official_{official.id}",
        type="secondary",
    ):
        success, error = presenter.delete(official.id)
        if success:
            st.success("削除しました")
            st.rerun()
        else:
            st.error(f"削除に失敗: {error}")
