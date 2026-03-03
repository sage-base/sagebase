"""View for politician management."""

import streamlit as st

from src.interfaces.web.streamlit.presenters.politician_presenter import (
    PoliticianPresenter,
)
from src.seed_generator import SeedGenerator


# 日本の都道府県リスト
PREFECTURES: list[str] = [
    "",  # 未選択用
    "北海道",
    "青森県",
    "岩手県",
    "宮城県",
    "秋田県",
    "山形県",
    "福島県",
    "茨城県",
    "栃木県",
    "群馬県",
    "埼玉県",
    "千葉県",
    "東京都",
    "神奈川県",
    "新潟県",
    "富山県",
    "石川県",
    "福井県",
    "山梨県",
    "長野県",
    "岐阜県",
    "静岡県",
    "愛知県",
    "三重県",
    "滋賀県",
    "京都府",
    "大阪府",
    "兵庫県",
    "奈良県",
    "和歌山県",
    "鳥取県",
    "島根県",
    "岡山県",
    "広島県",
    "山口県",
    "徳島県",
    "香川県",
    "愛媛県",
    "高知県",
    "福岡県",
    "佐賀県",
    "長崎県",
    "熊本県",
    "大分県",
    "宮崎県",
    "鹿児島県",
    "沖縄県",
    "比例代表",
]


def render_politicians_page() -> None:
    """Render the politicians management page."""
    st.header("政治家管理")
    st.markdown("政治家の情報を管理します")

    presenter = PoliticianPresenter()

    # Create tabs
    tabs = st.tabs(["政治家一覧", "新規登録", "編集・削除", "重複統合"])

    with tabs[0]:
        render_politicians_list_tab(presenter)

    with tabs[1]:
        render_new_politician_tab(presenter)

    with tabs[2]:
        render_edit_delete_tab(presenter)

    with tabs[3]:
        render_merge_tab(presenter)


def render_politicians_list_tab(presenter: PoliticianPresenter) -> None:
    """Render the politicians list tab."""
    st.subheader("政治家一覧")

    # SEEDファイル生成セクション（一番上に配置）
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### SEEDファイル生成")
            st.markdown("現在登録されている政治家データからSEEDファイルを生成します")
        with col2:
            if st.button(
                "SEEDファイル生成",
                key="generate_politicians_seed",
                type="primary",
            ):
                with st.spinner("SEEDファイルを生成中..."):
                    try:
                        generator = SeedGenerator()
                        seed_content = generator.generate_politicians_seed()

                        # ファイルを保存
                        output_path = "database/seed_politicians_generated.sql"
                        with open(output_path, "w", encoding="utf-8") as f:
                            f.write(seed_content)

                        st.success(f"✅ SEEDファイルを生成しました: {output_path}")

                        # 生成内容をプレビュー表示
                        with st.expander("生成内容をプレビュー", expanded=False):
                            st.code(seed_content[:5000], language="sql")
                    except Exception as e:
                        st.error(
                            f"❌ SEEDファイル生成中にエラーが発生しました: {str(e)}"
                        )

    st.divider()

    # Get parties for filter
    parties = presenter.get_all_parties()
    # politician_id → 政党名のマッピングを取得（party_membership_history経由）
    politician_party_map = presenter.get_politician_party_map()

    # Filters
    col1, col2 = st.columns(2)

    with col1:
        party_options = ["すべて"] + [p.name for p in parties]
        selected_party = st.selectbox("政党でフィルタ", party_options)

    with col2:
        search_name = st.text_input("名前で検索", placeholder="例: 山田")

    # Load politicians
    politicians = presenter.load_politicians_with_filters(
        search_name=search_name if search_name else None
    )

    # 政党フィルタリング（party_membership_history経由）
    if selected_party != "すべて":
        party_name_filter = selected_party
        politicians = [
            p
            for p in politicians
            if p.id is not None and politician_party_map.get(p.id) == party_name_filter
        ]

    if politicians:
        # Display data in DataFrame with editable prefecture column
        df = presenter.to_dataframe(politicians, parties, politician_party_map)
        if df is not None:
            # 都道府県列をドロップダウンで編集可能にする
            column_config = {
                "ID": st.column_config.NumberColumn("ID", disabled=True),
                "名前": st.column_config.TextColumn("名前", disabled=True),
                "漢字名": st.column_config.TextColumn("漢字名", disabled=True),
                "都道府県": st.column_config.SelectboxColumn(
                    "都道府県",
                    options=PREFECTURES,
                    required=False,
                ),
                "政党": st.column_config.TextColumn("政党", disabled=True),
                "選挙区": st.column_config.TextColumn("選挙区", disabled=True),
                "プロフィールURL": st.column_config.TextColumn(
                    "プロフィールURL", disabled=True
                ),
            }

            edited_df = st.data_editor(
                df,
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                key="politicians_editor",
            )

            # 変更があった行を検出して保存
            if not df.equals(edited_df):
                # 変更された行を特定
                changed_rows = df.compare(edited_df)
                if not changed_rows.empty:
                    st.info("変更を検出しました。保存ボタンで保存してください。")

                    if st.button("変更を保存", type="primary", key="save_pref"):
                        success_count = 0
                        error_count = 0
                        for idx in changed_rows.index.unique():
                            politician_id = int(df.loc[idx, "ID"])
                            new_prefecture = edited_df.loc[idx, "都道府県"]

                            # 元の政治家データを取得
                            original = next(
                                (p for p in politicians if p.id == politician_id), None
                            )
                            if original:
                                user_id = presenter.get_current_user_id()

                                success, error = presenter.update(
                                    id=politician_id,
                                    name=original.name,
                                    prefecture=new_prefecture or "",
                                    district=original.district or "",
                                    profile_url=original.profile_page_url,
                                    user_id=user_id,
                                )
                                if success:
                                    success_count += 1
                                else:
                                    error_count += 1
                                    msg = f"ID {politician_id} の更新に失敗: {error}"
                                    st.error(msg)

                        if success_count > 0:
                            st.success(f"✅ {success_count}件を更新しました")
                            st.rerun()
                        if error_count > 0:
                            st.warning(f"⚠️ {error_count}件の更新に失敗しました")

        # Statistics
        st.markdown("### 統計情報")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("総数", f"{len(politicians)}名")
        with col2:
            party_counts: dict[str, int] = {}
            for p in politicians:
                pname = "無所属"
                if politician_party_map and p.id is not None:
                    pname = politician_party_map.get(p.id, "無所属")
                party_counts[pname] = party_counts.get(pname, 0) + 1
            if party_counts:
                max_party = max(party_counts, key=party_counts.get)  # type: ignore[arg-type]
                st.metric("最多政党", f"{max_party} ({party_counts[max_party]}名)")
        with col3:
            with_url = len([p for p in politicians if p.profile_page_url])
            st.metric("プロフィールURL登録", f"{with_url}名")
    else:
        st.info("政治家が登録されていません")


def render_new_politician_tab(presenter: PoliticianPresenter) -> None:
    """Render the new politician registration tab."""
    st.subheader("新規政治家登録")

    if "new_politician_success_message" in st.session_state:
        st.success(st.session_state.new_politician_success_message)
        del st.session_state.new_politician_success_message

    # 都道府県リスト
    prefectures = [
        "北海道",
        "青森県",
        "岩手県",
        "宮城県",
        "秋田県",
        "山形県",
        "福島県",
        "茨城県",
        "栃木県",
        "群馬県",
        "埼玉県",
        "千葉県",
        "東京都",
        "神奈川県",
        "新潟県",
        "富山県",
        "石川県",
        "福井県",
        "山梨県",
        "長野県",
        "岐阜県",
        "静岡県",
        "愛知県",
        "三重県",
        "滋賀県",
        "京都府",
        "大阪府",
        "兵庫県",
        "奈良県",
        "和歌山県",
        "鳥取県",
        "島根県",
        "岡山県",
        "広島県",
        "山口県",
        "徳島県",
        "香川県",
        "愛媛県",
        "高知県",
        "福岡県",
        "佐賀県",
        "長崎県",
        "熊本県",
        "大分県",
        "宮崎県",
        "鹿児島県",
        "沖縄県",
        "比例代表",
    ]

    with st.form("new_politician_form"):
        name = st.text_input("名前", placeholder="山田太郎")

        prefecture = st.selectbox("選挙区の都道府県 *", prefectures)

        st.info("政党の設定は「政党所属履歴」画面から行ってください。")

        district = st.text_input("選挙区 *", placeholder="東京1区")
        profile_url = st.text_input(
            "プロフィールURL（任意）", placeholder="https://example.com/profile"
        )

        submitted = st.form_submit_button("登録")

        if submitted:
            if not name:
                st.error("名前を入力してください")
            elif not prefecture:
                st.error("選挙区の都道府県を選択してください")
            elif not district:
                st.error("選挙区を入力してください")
            else:
                user_id = presenter.get_current_user_id()
                success, politician_id, error = presenter.create(
                    name,
                    prefecture,
                    district,
                    profile_url if profile_url else None,
                    user_id=user_id,
                )
                if success:
                    st.session_state.new_politician_success_message = (
                        f"政治家「{name}」を登録しました（ID: {politician_id}）"
                    )
                    st.rerun()
                else:
                    st.error(f"登録に失敗しました: {error}")


def render_edit_delete_tab(presenter: PoliticianPresenter) -> None:
    """Render the edit/delete tab."""
    st.subheader("政治家の編集・削除")

    # Load all politicians
    politicians = presenter.load_data()
    if not politicians:
        st.info("編集する政治家がありません")
        return

    # Get parties
    parties = presenter.get_all_parties()

    # ファイル先頭のPREFECTURESを使用（空文字を除く）
    prefectures = [p for p in PREFECTURES if p]

    # フィルターオプション
    st.markdown("#### フィルター")

    # 政党フィルター
    party_filter_options = ["すべて"] + [p.name for p in parties]
    selected_party_filter = st.selectbox(
        "政党でフィルター",
        party_filter_options,
        key="edit_party_filter",
    )

    # 都道府県フィルター
    prefecture_filter_options = ["すべて"] + prefectures
    selected_prefecture_filter = st.selectbox(
        "都道府県でフィルター",
        prefecture_filter_options,
        key="edit_prefecture_filter",
    )

    # チェックボックスフィルター
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_no_prefecture = st.checkbox(
            "都道府県が未設定の政治家のみ", key="filter_no_prefecture"
        )
    with col2:
        filter_no_district = st.checkbox(
            "選挙区が未設定の政治家のみ", key="filter_no_district"
        )
    with col3:
        filter_hiragana_no_kanji = st.checkbox(
            "ひらがな名（漢字名未設定）のみ", key="filter_hiragana_no_kanji"
        )

    # フィルター適用
    filtered_politicians = politicians

    # 政党フィルター（party_membership_history経由）
    politician_party_map = presenter.get_politician_party_map()
    if selected_party_filter != "すべて":
        filtered_politicians = [
            p
            for p in filtered_politicians
            if p.id is not None
            and politician_party_map.get(p.id) == selected_party_filter
        ]

    # 都道府県フィルター
    if selected_prefecture_filter != "すべて":
        filtered_politicians = [
            p
            for p in filtered_politicians
            if p.prefecture == selected_prefecture_filter
        ]

    if filter_no_prefecture:
        filtered_politicians = [p for p in filtered_politicians if not p.prefecture]
    if filter_no_district:
        filtered_politicians = [p for p in filtered_politicians if not p.district]
    if filter_hiragana_no_kanji:
        filtered_politicians = [
            p
            for p in filtered_politicians
            if (p.is_lastname_hiragana or p.is_firstname_hiragana) and not p.kanji_name
        ]

    # フィルター結果の表示
    is_filtered = (
        selected_party_filter != "すべて"
        or selected_prefecture_filter != "すべて"
        or filter_no_prefecture
        or filter_no_district
        or filter_hiragana_no_kanji
    )
    if is_filtered:
        filtered_count = len(filtered_politicians)
        total_count = len(politicians)
        st.info(f"フィルター適用中: {filtered_count}件 / 全{total_count}件")

    if not filtered_politicians:
        st.warning("条件に一致する政治家がいません")
        return

    # Select politician to edit
    politician_options = [f"{p.name} (ID: {p.id})" for p in filtered_politicians]
    selected_politician_str = st.selectbox("編集する政治家を選択", politician_options)

    # Get selected politician
    selected_id = int(selected_politician_str.split("ID: ")[1].replace(")", ""))
    selected_politician = next(p for p in politicians if p.id == selected_id)

    # Edit and delete forms
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 編集")
        with st.form("edit_politician_form"):
            new_name = st.text_input("名前", value=selected_politician.name)

            # 都道府県の現在値を取得
            current_prefecture = selected_politician.prefecture or prefectures[0]
            prefecture_index = (
                prefectures.index(current_prefecture)
                if current_prefecture in prefectures
                else 0
            )
            new_prefecture = st.selectbox(
                "選挙区の都道府県 *",
                prefectures,
                index=prefecture_index,
            )

            current_party = (
                politician_party_map.get(selected_politician.id, "無所属")
                if selected_politician.id is not None
                else "無所属"
            )
            st.text_input("政党（読み取り専用）", value=current_party, disabled=True)
            st.caption("政党の変更は「政党所属履歴」画面から行ってください。")

            new_district = st.text_input(
                "選挙区 *", value=selected_politician.district or ""
            )
            new_kanji_name = st.text_input(
                "漢字名（ひらがな名の場合に設定）",
                value=selected_politician.kanji_name or "",
                placeholder="例: 宮本岳志",
            )
            new_profile_url = st.text_input(
                "プロフィールURL", value=selected_politician.profile_page_url or ""
            )

            submitted = st.form_submit_button("更新")

            if submitted:
                if not new_name:
                    st.error("名前を入力してください")
                elif not new_prefecture:
                    st.error("選挙区の都道府県を選択してください")
                elif not new_district:
                    st.error("選挙区を入力してください")
                else:
                    user_id = presenter.get_current_user_id()
                    success, error = presenter.update(
                        selected_politician.id,  # type: ignore[arg-type]
                        new_name,
                        new_prefecture,
                        new_district,
                        new_profile_url if new_profile_url else None,
                        user_id=user_id,
                        kanji_name=new_kanji_name if new_kanji_name else None,
                    )
                    if success:
                        st.success("政治家を更新しました")
                        st.rerun()
                    else:
                        st.error(f"更新に失敗しました: {error}")

    with col2:
        st.markdown("#### 削除")
        st.warning("政治家を削除すると、関連する発言記録も影響を受けます")

        # セッション状態の初期化（確認ダイアログ用）
        confirm_key = f"confirm_delete_{selected_politician.id}"
        if confirm_key not in st.session_state:
            st.session_state[confirm_key] = False

        if st.button("🗑️ この政治家を削除", type="secondary"):
            user_id = presenter.get_current_user_id()
            # まず紐づきを確認（force=Falseで呼び出し）
            success, error, has_related, related_counts = presenter.delete(
                selected_politician.id,  # type: ignore[arg-type]
                user_id=user_id,
                force=False,
            )
            if success:
                st.success(f"政治家「{selected_politician.name}」を削除しました")
                st.session_state[confirm_key] = False
                st.rerun()
            elif has_related:
                # 関連データがある場合は確認ダイアログを表示
                st.session_state[confirm_key] = True
                st.session_state[f"related_counts_{selected_politician.id}"] = (
                    related_counts
                )
                st.rerun()
            else:
                st.error(f"削除に失敗しました: {error}")

        # 確認ダイアログの表示
        if st.session_state.get(confirm_key, False):
            related_counts = st.session_state.get(
                f"related_counts_{selected_politician.id}", {}
            )
            total_count = sum(related_counts.values()) if related_counts else 0

            # テーブル名の日本語マッピング
            table_names_jp = {
                "speakers": "発言者",
                "parliamentary_group_memberships": "議員団所属",
                "pledges": "公約",
                "party_membership_history": "政党所属履歴",
                "proposal_judges": "議案賛否",
                "conference_members": "会議体所属",
                "extracted_parliamentary_group_members": "抽出済み議員団メンバー",
                "extracted_proposal_judges": "抽出済み議案賛否",
            }

            st.error(
                f"⚠️ この政治家には関連データが{total_count}件あります。\n"
                "削除すると、これらの関連データが解除または削除されます。"
            )

            if related_counts:
                details = []
                for table, count in related_counts.items():
                    if count > 0:
                        jp_name = table_names_jp.get(table, table)
                        details.append(f"{jp_name}: {count}件")
                st.write("関連データの内訳: " + ", ".join(details))

            col_confirm, col_cancel = st.columns(2)
            with col_confirm:
                if st.button(
                    "⚠️ 関連データを解除・削除して削除",
                    type="primary",
                    key=f"force_delete_{selected_politician.id}",
                ):
                    user_id = presenter.get_current_user_id()
                    success, error, _, _ = presenter.delete(
                        selected_politician.id,  # type: ignore[arg-type]
                        user_id=user_id,
                        force=True,
                    )
                    if success:
                        st.success(
                            f"政治家「{selected_politician.name}」を削除しました"
                        )
                        st.session_state[confirm_key] = False
                        # セッション状態のクリーンアップ
                        st.session_state.pop(
                            f"related_counts_{selected_politician.id}", None
                        )
                        st.rerun()
                    else:
                        st.error(f"削除に失敗しました: {error}")
            with col_cancel:
                if st.button(
                    "キャンセル", key=f"cancel_delete_{selected_politician.id}"
                ):
                    st.session_state[confirm_key] = False
                    st.session_state.pop(
                        f"related_counts_{selected_politician.id}", None
                    )
                    st.rerun()

    # 一括処理セクション
    st.divider()
    st.markdown("#### 一括処理")

    if "whitespace_removal_success" in st.session_state:
        st.success(st.session_state.whitespace_removal_success)
        del st.session_state.whitespace_removal_success

    if st.button("🧹 全ての政治家レコードから空白を除去"):
        with st.spinner("空白を除去中..."):
            success, updated_count, error = presenter.remove_whitespace_from_all()
            if success:
                if updated_count > 0:
                    st.session_state.whitespace_removal_success = (
                        f"{updated_count}件の政治家レコードから空白を除去しました"
                    )
                else:
                    st.session_state.whitespace_removal_success = (
                        "空白を含む政治家レコードはありませんでした"
                    )
                st.rerun()
            else:
                st.error(f"空白除去に失敗しました: {error}")


def render_merge_tab(presenter: PoliticianPresenter) -> None:
    """Render the merge tab."""
    st.subheader("重複統合")
    st.markdown("重複している政治家を統合します")

    # Load all politicians
    politicians = presenter.load_data()
    if not politicians or len(politicians) < 2:
        st.info("統合する政治家が不足しています")
        return

    politician_options = [f"{p.name} (ID: {p.id})" for p in politicians]

    col1, col2 = st.columns(2)

    with col1:
        source_str = st.selectbox("統合元（削除される）", politician_options)
        source_id = int(source_str.split("ID: ")[1].replace(")", ""))

    with col2:
        target_str = st.selectbox("統合先（残る）", politician_options)
        target_id = int(target_str.split("ID: ")[1].replace(")", ""))

    if source_id == target_id:
        st.error("同じ政治家を選択することはできません")
    else:
        st.info("統合元のすべてのデータが統合先に移動され、統合元は削除されます")

        if st.button("統合を実行", type="primary"):
            success, error = presenter.merge(source_id, target_id)
            if success:
                st.success("政治家を統合しました")
                st.rerun()
            else:
                st.error(f"統合に失敗しました: {error}")


def main() -> None:
    """Main function for testing."""
    render_politicians_page()


if __name__ == "__main__":
    main()
