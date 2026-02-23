"""SmartNewsSmriSangiinDataSourceのテスト."""

import json

from pathlib import Path
from typing import Any

import pytest

from src.infrastructure.importers.smartnews_smri_sangiin_data_source import (
    SmartNewsSmriSangiinDataSource,
)


# ヘッダー行
_HEADER = [
    "議員氏名",
    "通称名使用議員の本名",
    "議員個人の紹介ページ",
    "読み方",
    "会派",
    "選挙区",
    "任期満了",
    "写真URL",
    "当選年",
    "当選回数",
    "役職等",
    "役職等の時点",
    "経歴",
    "経歴の時点",
]


def _make_row(
    name: str = "田中太郎",
    real_name: str = "",
    url: str = "https://example.com/tanaka",
    furigana: str = "たなかたろう",
    party: str = "自由民主党",
    district: str = "東京都",
    term_expiry: str = "2028-07-25",
    photo_url: str = "",
    elected_years: str = "2022, 2016",
    election_count: int = 2,
    position: str = "",
    position_date: str = "",
    career: str = "",
    career_date: str = "",
) -> list[Any]:
    """テスト用のデータ行を生成する."""
    return [
        name,
        real_name,
        url,
        furigana,
        party,
        district,
        term_expiry,
        photo_url,
        elected_years,
        election_count,
        position,
        position_date,
        career,
        career_date,
    ]


class TestParseElectedYears:
    """_parse_elected_years のテスト."""

    def test_comma_separated_years(self) -> None:
        """カンマ区切りの年をパースする."""
        result = SmartNewsSmriSangiinDataSource._parse_elected_years("2022, 2016, 2010")
        assert result == [2022, 2016, 2010]

    def test_single_year_string(self) -> None:
        """単一年（文字列）をパースする."""
        result = SmartNewsSmriSangiinDataSource._parse_elected_years("2022")
        assert result == [2022]

    def test_single_year_int(self) -> None:
        """単一年（整数）をパースする."""
        result = SmartNewsSmriSangiinDataSource._parse_elected_years(2022)
        assert result == [2022]

    def test_empty_string(self) -> None:
        """空文字列で空リストを返す."""
        result = SmartNewsSmriSangiinDataSource._parse_elected_years("")
        assert result == []

    def test_sorted_descending(self) -> None:
        """結果が新しい順にソートされる."""
        result = SmartNewsSmriSangiinDataSource._parse_elected_years("2010, 2022, 2016")
        assert result == [2022, 2016, 2010]


class TestParseRow:
    """_parse_row のテスト."""

    def setup_method(self) -> None:
        self.data_source = SmartNewsSmriSangiinDataSource()

    def test_basic_constituency_member(self) -> None:
        """選挙区議員のパース."""
        row = _make_row(
            name="田中太郎",
            furigana="たなかたろう",
            party="自由民主党",
            district="東京都",
            elected_years="2022, 2016",
            election_count=2,
            url="https://example.com/tanaka",
        )
        record = self.data_source._parse_row(row)

        assert record.name == "田中太郎"
        assert record.furigana == "たなかたろう"
        assert record.party_name == "自由民主党"
        assert record.district_name == "東京都"
        assert record.elected_years == [2022, 2016]
        assert record.election_count == 2
        assert record.profile_url == "https://example.com/tanaka"
        assert record.is_proportional is False

    def test_proportional_member(self) -> None:
        """比例区議員のパース."""
        row = _make_row(district="比例", elected_years="2022")
        record = self.data_source._parse_row(row)

        assert record.district_name == "比例"
        assert record.is_proportional is True

    def test_empty_url_becomes_none(self) -> None:
        """空URLがNoneになる."""
        row = _make_row(url="")
        record = self.data_source._parse_row(row)
        assert record.profile_url is None

    def test_insufficient_fields_raises(self) -> None:
        """フィールド数不足でValueErrorが発生する."""
        short_row = ["田中太郎", "", ""]
        with pytest.raises(ValueError, match="フィールド数不足"):
            self.data_source._parse_row(short_row)


class TestFetchCouncillors:
    """fetch_councillors のテスト."""

    def setup_method(self) -> None:
        self.data_source = SmartNewsSmriSangiinDataSource()

    async def test_fetch_basic(self, tmp_path: Path) -> None:
        """基本的なfetch_councillorsの動作テスト."""
        data = [
            _HEADER,
            _make_row(name="議員A", district="東京都", elected_years="2022"),
            _make_row(name="議員B", district="比例", elected_years="2019, 2013"),
        ]
        json_file = tmp_path / "giin.json"
        json_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        records = await self.data_source.fetch_councillors(json_file)

        assert len(records) == 2
        assert records[0].name == "議員A"
        assert records[0].is_proportional is False
        assert records[1].name == "議員B"
        assert records[1].is_proportional is True
        assert records[1].elected_years == [2019, 2013]

    async def test_fetch_empty_data(self, tmp_path: Path) -> None:
        """ヘッダーのみのファイルで空リストを返す."""
        data = [_HEADER]
        json_file = tmp_path / "giin.json"
        json_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        records = await self.data_source.fetch_councillors(json_file)
        assert records == []

    async def test_fetch_skips_malformed_rows(self, tmp_path: Path) -> None:
        """不正な行をスキップして正常行のみ返す."""
        data = [
            _HEADER,
            _make_row(name="正常議員"),
            ["不正な行", "フィールド不足"],
            _make_row(name="正常議員2"),
        ]
        json_file = tmp_path / "giin.json"
        json_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        records = await self.data_source.fetch_councillors(json_file)

        assert len(records) == 2
        assert records[0].name == "正常議員"
        assert records[1].name == "正常議員2"

    async def test_fetch_no_data_rows(self, tmp_path: Path) -> None:
        """データ行が1件もない（ヘッダーすらない）場合."""
        data: list[Any] = []
        json_file = tmp_path / "giin.json"
        json_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        records = await self.data_source.fetch_councillors(json_file)
        assert records == []
