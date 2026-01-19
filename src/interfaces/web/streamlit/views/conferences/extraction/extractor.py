"""Conference member extractor.

会議体から議員情報を抽出する機能を提供します。
"""

import asyncio
import logging

from typing import Any

import pandas as pd
import streamlit as st

from .helpers import parse_conference_row, validate_and_filter_rows

from src.application.usecases.update_extracted_conference_member_from_extraction_usecase import (  # noqa: E501
    UpdateExtractedConferenceMemberFromExtractionUseCase,
)
from src.infrastructure.external.conference_member_extractor.extractor import (
    ConferenceMemberExtractor,
)
from src.infrastructure.persistence.async_session_adapter import NoOpSessionAdapter
from src.infrastructure.persistence.extracted_conference_member_repository_impl import (
    ExtractedConferenceMemberRepositoryImpl,
)
from src.infrastructure.persistence.extraction_log_repository_impl import (
    ExtractionLogRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter


logger = logging.getLogger(__name__)


def extract_members_from_conferences(selected_rows: pd.DataFrame) -> None:
    """選択された会議体から議員情報を抽出する

    選択された会議体のURLから議員情報を抽出し、データベースに保存します。

    Args:
        selected_rows: 選択された会議体のDataFrame
    """
    # バリデーションとフィルタリング
    rows_with_url, should_continue = validate_and_filter_rows(selected_rows)
    if not should_continue:
        return

    # 抽出処理を開始
    st.info(f"{len(rows_with_url)}件の会議体から議員情報を抽出します...")

    # UIコンポーネント
    progress_bar = st.progress(0)
    status_text = st.empty()

    # 抽出処理
    results: list[dict[str, Any]] = []

    # 抽出ログ記録用のUseCaseを作成
    # RepositoryAdapterは各操作で自動コミットするため、NoOpSessionAdapterを使用
    extracted_member_repo_for_usecase = RepositoryAdapter(
        ExtractedConferenceMemberRepositoryImpl
    )
    extraction_log_repo = RepositoryAdapter(ExtractionLogRepositoryImpl)
    session_adapter = NoOpSessionAdapter()

    update_usecase = UpdateExtractedConferenceMemberFromExtractionUseCase(
        extracted_conference_member_repo=extracted_member_repo_for_usecase,  # type: ignore[arg-type]
        extraction_log_repo=extraction_log_repo,  # type: ignore[arg-type]
        session_adapter=session_adapter,
    )

    extractor = ConferenceMemberExtractor(update_usecase=update_usecase)

    try:
        for idx, (_, row) in enumerate(rows_with_url.iterrows()):
            # 行データをパース
            parsed = parse_conference_row(row, idx)
            if parsed is None:
                continue

            conference_id, conference_name, url = parsed

            # ステータス更新
            status_text.text(
                f"処理中: {conference_name} ({idx + 1}/{len(rows_with_url)})"
            )

            # 抽出実行
            result = asyncio.run(
                extractor.extract_and_save_members(
                    conference_id=conference_id,
                    conference_name=conference_name,
                    url=url,
                )
            )
            results.append(result)

            # プログレスバー更新
            progress_bar.progress((idx + 1) / len(rows_with_url))

        # 完了
        status_text.text("抽出処理が完了しました")
        progress_bar.progress(1.0)

        # 結果表示
        _display_extraction_summary(results)

    except Exception as e:
        logger.exception("抽出処理中に予期しないエラーが発生しました")
        st.error(f"抽出処理中にエラーが発生しました: {str(e)}")
    finally:
        extractor.close()


def _display_extraction_summary(results: list[dict[str, Any]]) -> None:
    """抽出結果のサマリーを表示

    抽出件数、保存件数、失敗件数などの統計情報を表示します。

    Args:
        results: 抽出結果のリスト
    """
    st.success("議員情報の抽出が完了しました")

    # 結果詳細
    total_extracted = sum(r.get("extracted_count", 0) for r in results)
    total_saved = sum(r.get("saved_count", 0) for r in results)
    total_failed = sum(r.get("failed_count", 0) for r in results)
    errors = [r for r in results if "error" in r]

    # メトリクス表示
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("抽出件数", total_extracted)
    with col2:
        st.metric("保存件数", total_saved)
    with col3:
        st.metric("失敗件数", total_failed)

    # エラー詳細
    if errors:
        st.error(f"{len(errors)}件の会議体で抽出エラーが発生しました")
        with st.expander("エラー詳細"):
            for error_result in errors:
                error_msg = error_result.get("error", "Unknown error")
                conference_name = error_result.get("conference_name", "不明な会議体")
                st.write(f"- {conference_name}: {error_msg}")

    # 詳細結果を表形式で表示
    with st.expander("詳細結果"):
        result_df = pd.DataFrame(results)
        st.dataframe(result_df, use_container_width=True)
