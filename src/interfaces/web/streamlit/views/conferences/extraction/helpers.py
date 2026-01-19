"""Helper functions for conference member extraction.

会議体メンバー抽出のヘルパー関数を提供します。
"""

import logging

from typing import cast

import pandas as pd
import streamlit as st


logger = logging.getLogger(__name__)


def validate_and_filter_rows(
    selected_rows: pd.DataFrame,
) -> tuple[pd.DataFrame, bool]:
    """選択された会議体をバリデーションしてフィルタリング

    議員紹介URLがない会議体を除外し、処理を継続するかどうかを判定します。

    Args:
        selected_rows: 選択された会議体のDataFrame

    Returns:
        tuple[pd.DataFrame, bool]: (URLを持つ行のDataFrame, 処理を継続するか)
    """
    # 議員紹介URLがない会議体を除外
    rows_with_url = cast(
        pd.DataFrame,
        selected_rows[
            selected_rows["議員紹介URL"].notna() & (selected_rows["議員紹介URL"] != "")
        ],
    )

    if len(rows_with_url) == 0:
        st.warning("選択された会議体には議員紹介URLが登録されていません。")
        return rows_with_url, False

    # URLがない会議体がある場合は警告
    rows_without_url = cast(
        pd.DataFrame,
        selected_rows[
            selected_rows["議員紹介URL"].isna() | (selected_rows["議員紹介URL"] == "")
        ],
    )
    if len(rows_without_url) > 0:
        st.warning(
            f"{len(rows_without_url)}件の会議体は議員紹介URLが未登録のためスキップされます。"
        )

    return rows_with_url, True


def parse_conference_row(row: pd.Series, idx: int) -> tuple[int, str, str] | None:
    """DataFrameの行から会議体情報を安全に抽出

    行データをパースし、会議体ID、会議体名、URLを取得します。

    Args:
        row: DataFrame行
        idx: 行インデックス

    Returns:
        tuple[int, str, str] | None: (会議体ID, 会議体名, URL) または None（エラー時）
    """
    try:
        conference_id = int(row["ID"])
        conference_name = str(row["会議体名"])
        url = str(row["議員紹介URL"])
        return conference_id, conference_name, url
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Invalid row data at index {idx}: {e}, skipping this conference")
        return None
