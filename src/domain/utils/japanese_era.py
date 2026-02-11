"""和暦⇔西暦変換ユーティリティ

和暦（令和・平成・昭和・大正）と西暦の相互変換を行うモジュール。
元号の定義はリストで管理し、新元号追加が容易な構造としている。
"""

import re

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class EraDefinition:
    """元号の定義"""

    name: str
    start_year: int  # 西暦での開始年
    end_year: int | None  # 西暦での終了年（Noneは現在進行中）


# 元号定義（新しい順）
# 注意: 元号の重複期間（例: 昭和64年/平成元年）は年単位で区切り、
# 旧元号の最終年は範囲外として扱う。歴史的には昭和64年（1989/1/1〜1/7）等が
# 実在するが、本実装では簡易的に対応しない。
ERA_DEFINITIONS: list[EraDefinition] = [
    EraDefinition(name="令和", start_year=2019, end_year=None),
    EraDefinition(name="平成", start_year=1989, end_year=2019),
    EraDefinition(name="昭和", start_year=1926, end_year=1989),
    EraDefinition(name="大正", start_year=1912, end_year=1926),
]

# 和暦文字列のパースパターン（「令和5年3月15日」「令和元年」等）
_WAREKI_DATE_PATTERN = re.compile(
    r"(?P<era>" + "|".join(e.name for e in ERA_DEFINITIONS) + r")"
    r"(?P<year>\d+|元)年"
    r"(?:(?P<month>\d+)月(?:(?P<day>\d+)日)?)?"
)


class JapaneseEraConverter:
    """和暦⇔西暦の変換を行うコンバーター"""

    def __init__(self) -> None:
        self._eras = ERA_DEFINITIONS
        self._era_map = {e.name: e for e in self._eras}

    def to_western_year(self, era_name: str, era_year: int) -> int:
        """和暦年を西暦年に変換する

        Args:
            era_name: 元号名（例: "令和"）
            era_year: 元号年（例: 5）

        Returns:
            西暦年（例: 2023）

        Raises:
            ValueError: 不正な元号名または範囲外の年
        """
        era = self._era_map.get(era_name)
        if era is None:
            valid_names = ", ".join(e.name for e in self._eras)
            raise ValueError(
                f"不正な元号名です: '{era_name}'（対応元号: {valid_names}）"
            )

        if era_year < 1:
            raise ValueError(
                f"元号年は1以上である必要があります: {era_name}{era_year}年"
            )

        western_year = era.start_year + era_year - 1

        # 元号の終了年を超えていないか検証
        if era.end_year is not None and western_year >= era.end_year:
            max_year = era.end_year - era.start_year
            raise ValueError(
                f"{era_name}{era_year}年は範囲外です（{era_name}は{max_year}年まで）"
            )

        return western_year

    def to_japanese_era(self, western_year: int) -> tuple[str, int]:
        """西暦年を和暦年に変換する

        複数の元号にまたがる年は、新しい元号を返す。

        Args:
            western_year: 西暦年（例: 2023）

        Returns:
            (元号名, 元号年)のタプル（例: ("令和", 5)）

        Raises:
            ValueError: 対応範囲外の西暦年
        """
        for era in self._eras:
            if western_year >= era.start_year:
                era_year = western_year - era.start_year + 1
                return (era.name, era_year)

        min_year = self._eras[-1].start_year
        raise ValueError(
            f"対応範囲外の西暦年です: {western_year}（{min_year}年以降に対応）"
        )

    def parse_date(self, text: str) -> date:
        """和暦文字列をdateオブジェクトに変換する

        対応フォーマット:
        - 「令和5年3月15日」→ date(2023, 3, 15)
        - 「令和5年3月」→ date(2023, 3, 1)
        - 「令和5年」→ date(2023, 1, 1)
        - 「令和元年5月1日」→ date(2019, 5, 1)（「元年」= 1年）

        Args:
            text: 和暦文字列

        Returns:
            dateオブジェクト

        Raises:
            ValueError: パースできない文字列、または不正な日付
        """
        match = _WAREKI_DATE_PATTERN.fullmatch(text.strip())
        if match is None:
            raise ValueError(f"和暦文字列をパースできません: '{text}'")

        era_name = match.group("era")
        year_str = match.group("year")
        era_year = 1 if year_str == "元" else int(year_str)
        month = int(match.group("month")) if match.group("month") else 1
        day = int(match.group("day")) if match.group("day") else 1

        western_year = self.to_western_year(era_name, era_year)

        try:
            return date(western_year, month, day)
        except ValueError:
            raise ValueError(
                f"不正な日付です: {text}（{western_year}年{month}月{day}日）"
            ) from None

    def format_date(self, d: date) -> str:
        """dateオブジェクトを和暦文字列に変換する

        Args:
            d: dateオブジェクト

        Returns:
            和暦文字列（例: "令和5年3月15日"）

        Raises:
            ValueError: 対応範囲外の日付
        """
        era_name, era_year = self.to_japanese_era(d.year)
        return f"{era_name}{era_year}年{d.month}月{d.day}日"
