"""インポーターモジュール共通のユーティリティ関数."""

import re

from datetime import date


# 和暦→西暦変換
WAREKI_MAP: dict[str, int] = {
    "令和": 2018,
    "平成": 1988,
    "昭和": 1925,
    "大正": 1911,
    "明治": 1867,
}


def zen_to_han(text: str) -> str:
    """全角数字・記号を半角に変換する."""
    zen = "０１２３４５６７８９．"
    han = "0123456789."
    table = str.maketrans(zen, han)
    return text.translate(table)


def parse_wareki_date(text: str) -> date | None:
    """和暦の日付文字列を西暦dateに変換する.

    例: "令和６年１０月２７日執行" → date(2024, 10, 27)
    「元年」は1年として扱う。元号と数字の間のスペースも許容する。
    """
    if not text:
        return None
    text = zen_to_han(str(text))
    pattern = r"(令和|平成|昭和|大正|明治)\s*(元|\d+)年\s*(\d+)月\s*(\d+)日"
    match = re.search(pattern, text)
    if not match:
        return None
    era, year_str, month_str, day_str = match.groups()
    base_year = WAREKI_MAP.get(era)
    if base_year is None:
        return None
    year = base_year + (1 if year_str == "元" else int(year_str))
    try:
        return date(year, int(month_str), int(day_str))
    except ValueError:
        return None
