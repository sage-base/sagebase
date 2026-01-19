"""Create memberships subtab for parliamentary group members.

議員団メンバーシップ作成サブタブのUI実装を提供します。
"""

import asyncio

from datetime import date

import pandas as pd
import streamlit as st

from src.application.usecases.authenticate_user_usecase import AuthenticateUserUseCase
from src.infrastructure.di.container import Container
from src.interfaces.web.streamlit.auth import google_sign_in
from src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter import (  # noqa: E501
    ParliamentaryGroupMemberPresenter,
)


def render_create_memberships_subtab(
    presenter: ParliamentaryGroupMemberPresenter,
) -> None:
    """Render the create memberships sub-tab.

    議員団メンバーシップ作成サブタブをレンダリングします。
    マッチ済みメンバーからメンバーシップを作成する機能を提供します。

    Args:
        presenter: 議員団メンバープレゼンター
    """
    st.markdown("### メンバーシップ作成")
    st.markdown(
        "マッチ済み（matched）のメンバーから、議員団メンバーシップ"
        "（parliamentary_group_memberships）を作成します"
    )

    # Get user info from session (from Google Sign-In)
    user_info: dict[str, str] | None = google_sign_in.get_user_info()
    if not user_info:
        st.warning("ユーザー情報を取得できません。ログインしてください。")
        return

    # Display current user
    user_name = user_info.get("name", "Unknown")
    user_email = user_info.get("email", "Unknown")
    st.info(f"実行ユーザー: {user_name} ({user_email})")

    # Get parliamentary groups
    parliamentary_groups = presenter.get_all_parliamentary_groups()

    # Options
    col1, col2 = st.columns(2)

    with col1:
        group_options = ["すべて"] + [g.name for g in parliamentary_groups if g.name]
        group_map = {g.name: g.id for g in parliamentary_groups if g.id and g.name}
        selected_group = st.selectbox(
            "対象議員団", group_options, key="memberships_group"
        )
        group_id = group_map.get(selected_group) if selected_group != "すべて" else None

    with col2:
        min_confidence = st.slider(
            "最小信頼度", min_value=0.5, max_value=1.0, value=0.7, step=0.05
        )

    # Start date
    start_date = st.date_input(
        "メンバーシップ開始日",
        value=date.today(),
        help="作成されるメンバーシップの所属開始日",
    )

    # Get matched count for preview
    stats = presenter.get_statistics(group_id)
    st.info(
        f"作成対象: {stats['matched']}件のマッチ済みメンバー "
        f"（信頼度 {min_confidence:.2f} 以上）"
    )

    # Re-match button
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "🔄 再マッチング実行",
            help="未処理のメンバーに対してマッチング処理を再実行します",
        ):
            with st.spinner("マッチング処理中..."):
                matched_count, total_count, message = presenter.rematch_members(
                    group_id
                )
                st.info(message)
                if matched_count > 0:
                    st.rerun()

    with col2:
        # Creation button
        if st.button("メンバーシップ作成", type="primary"):
            _create_memberships(
                presenter, user_info, group_id, min_confidence, start_date
            )


def _create_memberships(
    presenter: ParliamentaryGroupMemberPresenter,
    user_info: dict[str, str],
    group_id: int | None,
    min_confidence: float,
    start_date: date,
) -> None:
    """Create memberships from matched members.

    Args:
        presenter: 議員団メンバープレゼンター
        user_info: ユーザー情報
        group_id: 議員団ID（Noneの場合は全て）
        min_confidence: 最小信頼度
        start_date: 開始日
    """
    with st.spinner("メンバーシップを作成中..."):
        try:
            # Authenticate user and get user_id
            container = Container()
            auth_usecase = AuthenticateUserUseCase(
                user_repository=container.repositories.user_repository()
            )

            email = user_info.get("email", "")
            name = user_info.get("name")
            user = asyncio.run(auth_usecase.execute(email=email, name=name))

            # Create memberships with user_id
            created_count, skipped_count, created_memberships = (
                presenter.create_memberships(
                    parliamentary_group_id=group_id,
                    min_confidence=min_confidence,
                    start_date=start_date,
                    user_id=user.user_id,
                )
            )
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            import traceback

            st.code(traceback.format_exc())
            return

        # Display results
        if created_count > 0:
            st.success(f"✅ {created_count}件のメンバーシップを作成しました")
            st.balloons()

        if skipped_count > 0:
            st.warning(f"⚠️ {skipped_count}件をスキップしました")

        # Display created memberships
        if created_memberships:
            st.markdown("#### 作成されたメンバーシップ")
            membership_data = []
            for membership in created_memberships:
                membership_data.append(
                    {
                        "メンバー名": membership["member_name"],
                        "政治家ID": membership["politician_id"],
                        "議員団ID": membership["parliamentary_group_id"],
                        "役職": membership["role"] or "-",
                    }
                )

            df_memberships = pd.DataFrame(membership_data)
            st.dataframe(df_memberships, use_container_width=True)
