"""選挙結果メンバー管理ページ."""

import streamlit as st

from src.interfaces.web.streamlit.presenters.election_member_presenter import (
    ElectionMemberPresenter,
)
from src.interfaces.web.streamlit.presenters.election_presenter import (
    ElectionPresenter,
)
from src.interfaces.web.streamlit.presenters.governing_body_presenter import (
    GoverningBodyPresenter,
)


def render_election_members_page() -> None:
    """選挙結果メンバー管理ページを描画する."""
    st.header("選挙結果メンバー管理")
    st.markdown("選挙ごとの当選者・落選者を管理します")

    presenter = ElectionMemberPresenter()
    election_presenter = ElectionPresenter()
    gb_presenter = GoverningBodyPresenter()

    tab1, tab2, tab3 = st.tabs(["一覧", "新規登録", "編集・削除"])

    with tab1:
        render_list_tab(presenter, election_presenter, gb_presenter)

    with tab2:
        render_create_tab(presenter, election_presenter, gb_presenter)

    with tab3:
        render_edit_delete_tab(presenter, election_presenter, gb_presenter)


def _select_election(
    gb_presenter: GoverningBodyPresenter,
    election_presenter: ElectionPresenter,
    key_prefix: str,
) -> int | None:
    """開催主体 → 選挙のカスケード選択を描画し、選択された選挙IDを返す."""
    governing_bodies = gb_presenter.load_data()
    if not governing_bodies:
        st.info("開催主体が登録されていません。先に開催主体を登録してください。")
        return None

    gb_options = {f"{gb.name} ({gb.type})": gb.id for gb in governing_bodies}
    selected_gb_name = st.selectbox(
        "開催主体を選択",
        options=list(gb_options.keys()),
        key=f"{key_prefix}_gb_select",
    )
    if selected_gb_name is None:
        return None
    selected_gb_id = gb_options.get(selected_gb_name)
    if selected_gb_id is None:
        return None

    elections = election_presenter.load_elections_by_governing_body(selected_gb_id)
    if not elections:
        st.info("この開催主体には選挙が登録されていません。")
        return None

    election_options = {
        f"第{e.term_number}期 ({e.election_date})"
        + (f" - {e.election_type}" if e.election_type else ""): e.id
        for e in elections
    }
    selected_election_name = st.selectbox(
        "選挙（期）を選択",
        options=list(election_options.keys()),
        key=f"{key_prefix}_election_select",
    )
    if selected_election_name is None:
        return None
    return election_options.get(selected_election_name)


def _build_politician_map(presenter: ElectionMemberPresenter) -> dict[int, str]:
    """政治家ID→名前のマッピングを構築する."""
    politicians = presenter.load_politicians()
    return {
        p.id: p.name
        for p in politicians
        if p.id is not None  # type: ignore[misc]
    }


def render_list_tab(
    presenter: ElectionMemberPresenter,
    election_presenter: ElectionPresenter,
    gb_presenter: GoverningBodyPresenter,
) -> None:
    """一覧タブを描画する."""
    st.subheader("選挙結果メンバー一覧")

    election_id = _select_election(gb_presenter, election_presenter, "list")
    if election_id is None:
        return

    st.divider()

    members = presenter.load_members_by_election(election_id)
    if not members:
        st.info("この選挙にはメンバーが登録されていません。")
        return

    politician_map = _build_politician_map(presenter)
    df = presenter.to_dataframe(members, politician_map)
    if df is not None:
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.metric("登録済みメンバー数", f"{len(members)}件")


def render_create_tab(
    presenter: ElectionMemberPresenter,
    election_presenter: ElectionPresenter,
    gb_presenter: GoverningBodyPresenter,
) -> None:
    """新規登録タブを描画する."""
    st.subheader("新規メンバー登録")

    election_id = _select_election(gb_presenter, election_presenter, "create")
    if election_id is None:
        return

    politicians = presenter.load_politicians()
    if not politicians:
        st.warning("政治家が登録されていません。先に政治家を登録してください。")
        return

    politician_options = {
        f"{p.name} (ID: {p.id})": p.id for p in politicians if p.id is not None
    }
    selected_politician_name = st.selectbox(
        "政治家を選択",
        options=list(politician_options.keys()),
        key="create_politician_select",
    )
    if selected_politician_name is None:
        return
    politician_id = politician_options.get(selected_politician_name)
    if politician_id is None:
        return

    st.divider()

    with st.form("create_election_member_form"):
        result_options = presenter.get_result_options()
        selected_result = st.selectbox(
            "結果",
            options=result_options,
            key="create_result",
        )

        votes = st.number_input(
            "得票数（任意）",
            min_value=0,
            value=0,
            step=1,
            key="create_votes",
            help="得票数を入力してください。0の場合は未設定として扱います。",
        )

        rank = st.number_input(
            "順位（任意）",
            min_value=0,
            value=0,
            step=1,
            key="create_rank",
            help="順位を入力してください。0の場合は未設定として扱います。",
        )

        submitted = st.form_submit_button("登録", type="primary")

        if submitted:
            if selected_result is None:
                st.error("結果を選択してください。")
                return

            success, error = presenter.create(
                election_id=election_id,
                politician_id=politician_id,
                result=selected_result,
                votes=votes if votes > 0 else None,
                rank=rank if rank > 0 else None,
            )
            if success:
                st.success("選挙結果メンバーを登録しました。")
                st.rerun()
            else:
                st.error(f"登録に失敗しました: {error}")


def render_edit_delete_tab(
    presenter: ElectionMemberPresenter,
    election_presenter: ElectionPresenter,
    gb_presenter: GoverningBodyPresenter,
) -> None:
    """編集・削除タブを描画する."""
    st.subheader("メンバーの編集・削除")

    election_id = _select_election(gb_presenter, election_presenter, "edit")
    if election_id is None:
        return

    members = presenter.load_members_by_election(election_id)
    if not members:
        st.info("この選挙にはメンバーが登録されていません。")
        return

    politician_map = _build_politician_map(presenter)

    member_options = {
        f"{politician_map.get(m.politician_id, f'ID:{m.politician_id}')} - {m.result}"
        + (f" ({m.votes}票)" if m.votes is not None else ""): m
        for m in members
        if m.id is not None
    }

    selected_member_name = st.selectbox(
        "編集するメンバーを選択",
        options=list(member_options.keys()),
        key="edit_member_select",
    )
    if selected_member_name is None:
        return
    selected_member = member_options.get(selected_member_name)
    if selected_member is None or selected_member.id is None:
        return

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 編集")

        politicians = presenter.load_politicians()
        politician_options = {
            f"{p.name} (ID: {p.id})": p.id for p in politicians if p.id is not None
        }
        politician_names = list(politician_options.keys())
        current_politician_name = next(
            (
                name
                for name, pid in politician_options.items()
                if pid == selected_member.politician_id
            ),
            politician_names[0] if politician_names else None,
        )
        current_politician_index = (
            politician_names.index(current_politician_name)
            if current_politician_name and current_politician_name in politician_names
            else 0
        )

        edit_politician_name = st.selectbox(
            "政治家",
            options=politician_names,
            index=current_politician_index,
            key="edit_politician_select",
        )
        if edit_politician_name is None:
            return
        edit_politician_id = politician_options.get(edit_politician_name)
        if edit_politician_id is None:
            return

        with st.form("edit_election_member_form"):
            result_options = presenter.get_result_options()
            current_result_index = (
                result_options.index(selected_member.result)
                if selected_member.result in result_options
                else 0
            )
            edit_result = st.selectbox(
                "結果",
                options=result_options,
                index=current_result_index,
                key="edit_result",
            )

            edit_votes = st.number_input(
                "得票数（任意）",
                min_value=0,
                value=selected_member.votes if selected_member.votes is not None else 0,
                step=1,
                key="edit_votes",
            )

            edit_rank = st.number_input(
                "順位（任意）",
                min_value=0,
                value=selected_member.rank if selected_member.rank is not None else 0,
                step=1,
                key="edit_rank",
            )

            update_submitted = st.form_submit_button("更新")

            if update_submitted:
                if edit_result is None:
                    st.error("結果を選択してください。")
                    return

                success, error = presenter.update(
                    id=selected_member.id,
                    election_id=election_id,
                    politician_id=edit_politician_id,
                    result=edit_result,
                    votes=edit_votes if edit_votes > 0 else None,
                    rank=edit_rank if edit_rank > 0 else None,
                )
                if success:
                    st.success("選挙結果メンバーを更新しました。")
                    st.rerun()
                else:
                    st.error(f"更新に失敗しました: {error}")

    with col2:
        st.markdown("#### 削除")
        member_name = politician_map.get(
            selected_member.politician_id, f"ID:{selected_member.politician_id}"
        )
        st.warning(f"「{member_name}」の選挙結果を削除します。")

        if st.button(
            "削除",
            key="delete_member_button",
            type="secondary",
        ):
            st.session_state["confirm_delete_election_member"] = True

        if st.session_state.get("confirm_delete_election_member", False):
            st.error(f"「{member_name}」を本当に削除しますか？")
            col_confirm, col_cancel = st.columns(2)
            with col_confirm:
                if st.button("削除を実行", key="execute_delete_member", type="primary"):
                    success, error = presenter.delete(selected_member.id)
                    if success:
                        st.success(f"「{member_name}」を削除しました。")
                        st.session_state["confirm_delete_election_member"] = False
                        st.rerun()
                    else:
                        st.error(f"削除に失敗しました: {error}")
            with col_cancel:
                if st.button("キャンセル", key="cancel_delete_member"):
                    st.session_state["confirm_delete_election_member"] = False
                    st.rerun()


def main():
    """エントリーポイント."""
    render_election_members_page()
