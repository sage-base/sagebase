"""国会発言バッチ取得タブのUI実装."""

from __future__ import annotations

import time

import pandas as pd
import streamlit as st

from src.application.dtos.kokkai_speech_dto import (
    BatchImportKokkaiSpeechesInputDTO,
    FailedMeetingInfo,
    KokkaiMeetingDTO,
)
from src.interfaces.web.streamlit.presenters.kokkai_batch_import_presenter import (
    KokkaiBatchImportPresenter,
)


_SESSION_KEY_MEETINGS = "kokkai_batch_meetings"


def render_kokkai_batch_tab() -> None:
    """国会発言バッチ取得タブをレンダリングする."""
    st.subheader("国会発言バッチ取得")
    st.markdown("国会会議録APIから発言データを一括取得します。")

    presenter = KokkaiBatchImportPresenter()

    # --- 検索条件 ---
    input_dto = _render_search_form()

    col_fetch, col_import = st.columns(2)

    # --- 会議一覧取得 ---
    with col_fetch:
        fetch_clicked = st.button(
            "会議一覧を取得", key="kokkai_batch_fetch", type="secondary"
        )

    if fetch_clicked:
        if (
            input_dto.session_from is not None
            and input_dto.session_to is not None
            and input_dto.session_from > input_dto.session_to
        ):
            st.error("開始回次は終了回次以下にしてください。")
        else:
            with st.spinner("会議一覧を取得中..."):
                try:
                    meetings = presenter.fetch_meetings(input_dto)
                    st.session_state[_SESSION_KEY_MEETINGS] = meetings
                except Exception as e:
                    st.error(f"会議一覧の取得に失敗しました: {e}")
                    return

    # --- 会議一覧プレビュー ---
    meetings: list[KokkaiMeetingDTO] = st.session_state.get(_SESSION_KEY_MEETINGS, [])
    if meetings:
        _render_meetings_preview(meetings)

    # --- 一括取得 ---
    with col_import:
        import_disabled = not meetings
        import_clicked = st.button(
            "一括取得開始",
            key="kokkai_batch_import",
            type="primary",
            disabled=import_disabled,
        )

    if meetings:
        st.info(
            "取得済みの会議は自動スキップされます。"
            "中断後に同じ条件で再実行すれば続きから取得できます。"
        )

    if import_clicked and meetings:
        _execute_batch_import(presenter, meetings, input_dto)


def _render_search_form() -> BatchImportKokkaiSpeechesInputDTO:
    """検索条件フォームを描画し、入力DTOを返す."""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**回次（国会会期）範囲**")
        c1, c2 = st.columns(2)
        with c1:
            session_from = st.number_input(
                "開始回次",
                min_value=1,
                max_value=300,
                value=213,
                key="kokkai_session_from",
            )
        with c2:
            session_to = st.number_input(
                "終了回次",
                min_value=1,
                max_value=300,
                value=213,
                key="kokkai_session_to",
            )

    with col2:
        st.markdown("**日付範囲（任意）**")
        c3, c4 = st.columns(2)
        with c3:
            from_date = st.date_input("開始日", value=None, key="kokkai_from_date")
        with c4:
            until_date = st.date_input("終了日", value=None, key="kokkai_until_date")

    col3, col4, col5 = st.columns(3)
    with col3:
        house_options = ["指定なし", "衆議院", "参議院"]
        house = st.selectbox("院名", house_options, key="kokkai_house")

    with col4:
        meeting_name = st.text_input(
            "会議名（任意）", key="kokkai_meeting_name", placeholder="例: 本会議"
        )

    with col5:
        sleep_interval = st.number_input(
            "API間隔（秒）（推奨: 2秒以上）",
            min_value=0.0,
            max_value=10.0,
            value=2.0,
            step=0.5,
            key="kokkai_sleep",
        )

    return BatchImportKokkaiSpeechesInputDTO(
        name_of_house=house if house != "指定なし" else None,
        name_of_meeting=meeting_name or None,
        from_date=from_date.isoformat() if from_date else None,
        until_date=until_date.isoformat() if until_date else None,
        session_from=int(session_from),
        session_to=int(session_to),
        sleep_interval=float(sleep_interval),
    )


def _render_meetings_preview(meetings: list[KokkaiMeetingDTO]) -> None:
    """会議一覧のプレビューを表示する."""
    st.markdown(f"### 対象会議: **{len(meetings)}件**")

    df = pd.DataFrame(
        [
            {
                "日付": m.date,
                "院名": m.name_of_house,
                "会議名": m.name_of_meeting,
                "号数": m.issue,
                "回次": m.session,
            }
            for m in meetings[:100]
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    if len(meetings) > 100:
        st.caption(f"※ 先頭100件のみ表示（全{len(meetings)}件）")


def _execute_batch_import(
    presenter: KokkaiBatchImportPresenter,
    meetings: list[KokkaiMeetingDTO],
    input_dto: BatchImportKokkaiSpeechesInputDTO,
) -> None:
    """バッチインポートを実行し、進捗表示する."""
    total = len(meetings)
    progress_bar = st.progress(0, text="バッチインポート準備中...")

    # 結果集計用
    total_imported = 0
    total_skipped = 0
    total_speakers = 0
    total_meetings_created = 0
    errors: list[str] = []
    failed_meetings: list[FailedMeetingInfo] = []

    with st.status(f"バッチインポート実行中（0/{total}）", expanded=True) as status:
        for i, meeting in enumerate(meetings):
            label = (
                f"{meeting.name_of_house}{meeting.name_of_meeting}"
                f" {meeting.issue} ({meeting.date})"
            )
            progress_bar.progress(
                (i) / total,
                text=f"処理中: {label} ({i + 1}/{total})",
            )
            st.write(f"**[{i + 1}/{total}]** {label}")

            try:
                result = presenter.import_single_meeting(meeting.issue_id)
                total_imported += result.total_speeches_imported
                total_skipped += result.total_speeches_skipped
                total_speakers += result.total_speakers_created
                total_meetings_created += result.total_meetings_created

                if result.total_speeches_imported > 0:
                    st.write(
                        f"  → {result.total_speeches_imported}件インポート, "
                        f"{result.total_speakers_created}名新規発言者"
                    )
                elif result.total_speeches_skipped > 0:
                    st.write(
                        f"  → スキップ（取得済み: {result.total_speeches_skipped}件）"
                    )

                if result.errors:
                    for err in result.errors:
                        st.warning(f"  ⚠ {err}")
                    errors.extend(result.errors)

            except Exception as e:
                error_msg = f"会議 {label} の処理中にエラー: {e}"
                st.error(f"  ✗ {error_msg}")
                errors.append(error_msg)
                failed_meetings.append(FailedMeetingInfo.from_meeting(meeting, e))

            # API負荷軽減
            if i < total - 1 and input_dto.sleep_interval > 0:
                time.sleep(input_dto.sleep_interval)

        progress_bar.progress(1.0, text="バッチインポート完了")
        status.update(label=f"バッチインポート完了（{total}件処理）", state="complete")

    # --- 結果サマリ ---
    _render_result_summary(
        total_meetings=total,
        total_meetings_created=total_meetings_created,
        total_imported=total_imported,
        total_skipped=total_skipped,
        total_speakers=total_speakers,
        errors=errors,
        failed_meetings=failed_meetings,
    )


def _render_result_summary(
    *,
    total_meetings: int,
    total_meetings_created: int,
    total_imported: int,
    total_skipped: int,
    total_speakers: int,
    errors: list[str],
    failed_meetings: list[FailedMeetingInfo] | None = None,
) -> None:
    """結果サマリを表示する."""
    st.markdown("### 結果サマリ")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("対象会議数", f"{total_meetings}件")
    with col2:
        st.metric("新規会議作成", f"{total_meetings_created}件")
    with col3:
        st.metric("インポート発言", f"{total_imported}件")
    with col4:
        st.metric("スキップ発言", f"{total_skipped}件")

    col5, col6 = st.columns(2)
    with col5:
        st.metric("新規発言者", f"{total_speakers}名")
    with col6:
        error_count = len(errors)
        st.metric("エラー数", f"{error_count}件")

    if failed_meetings:
        with st.expander(f"エラー会議詳細（{len(failed_meetings)}件）"):
            st.caption(
                "以下の会議でエラーが発生しました。同じ条件で再実行すれば再取得されます。"
            )
            df = pd.DataFrame(
                [
                    {
                        "issueID": fm.issue_id,
                        "回次": fm.session,
                        "院名": fm.name_of_house,
                        "会議名": fm.name_of_meeting,
                        "日付": fm.date,
                        "エラー": fm.error_message,
                    }
                    for fm in failed_meetings
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
    elif errors:
        with st.expander(f"エラー詳細（{len(errors)}件）"):
            for err in errors:
                st.text(err)

    st.info(
        "マッチング率は「統計情報」タブまたは「政治家マッチングAgent」タブで確認できます。"
    )
