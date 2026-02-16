"""提出者文字列パーサー.

国会データ等の提出者文字列を解析し、個人名リストと総人数を抽出する。
対応パターン:
- 「熊代昭彦君外四名」（代表者+外N名）
- 「熊代昭彦,谷畑孝,棚橋泰文」（カンマ区切り）
- 「田中太郎」（単一名）
"""

import re
import unicodedata

from src.domain.services.proposal_judge_extraction_service import (
    ProposalJudgeExtractionService,
)
from src.domain.value_objects.parsed_submitter import ParsedSubmitter


# 「外N名」パターン: 敬称の後に「外」+ 数字 + 「名」
_SOTO_PATTERN = re.compile(
    r"^(.+?)(?:君|氏|議員|先生|さん|様)?外([\d０-９一二三四五六七八九十百]+)名$"
)

# 漢数字→数値のマッピング
_KANJI_DIGITS: dict[str, int] = {
    "〇": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}

# カンマ系区切り文字
_COMMA_PATTERN = re.compile(r"[,，、]")


def kansuji_to_int(text: str) -> int:
    """漢数字を整数に変換する.

    「四」→4、「十二」→12、「二十」→20、「百」→100 等に対応。
    算用数字・全角数字の場合はそのまま変換する。

    Args:
        text: 漢数字文字列または数字文字列

    Returns:
        変換後の整数

    Raises:
        ValueError: 変換できない場合
    """
    normalized = unicodedata.normalize("NFKC", text).strip()

    if normalized.isdigit():
        return int(normalized)

    result = 0
    current = 0

    for char in text:
        if char in _KANJI_DIGITS:
            current = _KANJI_DIGITS[char]
        elif char == "十":
            if current == 0:
                current = 1
            result += current * 10
            current = 0
        elif char == "百":
            if current == 0:
                current = 1
            result += current * 100
            current = 0
        else:
            msg = f"変換できない文字: {char}"
            raise ValueError(msg)

    result += current
    return result


def _remove_honorifics(name: str) -> str:
    """敬称を除去する."""
    return ProposalJudgeExtractionService.normalize_politician_name(name)


def parse_submitter_string(raw_name: str) -> ParsedSubmitter:
    """提出者文字列を解析する.

    Args:
        raw_name: 提出者の生文字列

    Returns:
        ParsedSubmitter: パース結果
    """
    text = raw_name.strip()
    if not text:
        return ParsedSubmitter(names=(), total_count=0)

    # パターン1: 「外N名」パターン（例: 「熊代昭彦君外四名」）
    match = _SOTO_PATTERN.match(text)
    if match:
        representative = _remove_honorifics(match.group(1))
        others_count = kansuji_to_int(match.group(2))
        return ParsedSubmitter(
            names=(representative,),
            total_count=1 + others_count,
        )

    # パターン2: カンマ系区切り（例: 「熊代昭彦,谷畑孝,棚橋泰文」）
    if _COMMA_PATTERN.search(text):
        parts = _COMMA_PATTERN.split(text)
        names = tuple(_remove_honorifics(p.strip()) for p in parts if p.strip())
        return ParsedSubmitter(names=names, total_count=len(names))

    # パターン3: 単一名（例: 「田中太郎」「田中太郎君」）
    name = _remove_honorifics(text)
    return ParsedSubmitter(names=(name,), total_count=1)
