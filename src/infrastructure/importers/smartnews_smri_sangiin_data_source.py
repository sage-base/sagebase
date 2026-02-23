"""SmartNews SMRI 参議院議員データソース実装.

smartnews-smri/house-of-councillors リポジトリの giin.json をパースし、
参議院議員データを SangiinCandidateRecord に変換する。

データソース:
    https://github.com/smartnews-smri/house-of-councillors/blob/main/data/giin.json
"""

import json
import logging

from pathlib import Path
from typing import Any

from src.domain.value_objects.sangiin_candidate import SangiinCandidateRecord


logger = logging.getLogger(__name__)

# giin.json のフィールドインデックス
_IDX_NAME = 0  # 議員氏名
_IDX_REAL_NAME = 1  # 通称名使用議員の本名
_IDX_PROFILE_URL = 2  # 議員個人の紹介ページ
_IDX_FURIGANA = 3  # 読み方
_IDX_PARTY = 4  # 会派
_IDX_DISTRICT = 5  # 選挙区
_IDX_TERM_EXPIRY = 6  # 任期満了
_IDX_PHOTO_URL = 7  # 写真URL
_IDX_ELECTED_YEARS = 8  # 当選年
_IDX_ELECTION_COUNT = 9  # 当選回数
_IDX_POSITION = 10  # 役職等
_IDX_POSITION_DATE = 11  # 役職等の時点
_IDX_CAREER = 12  # 経歴
_IDX_CAREER_DATE = 13  # 経歴の時点

_EXPECTED_FIELDS = 14
_PROPORTIONAL_DISTRICT = "比例"


class SmartNewsSmriSangiinDataSource:
    """SmartNews SMRI の giin.json から参議院議員データを取得するデータソース."""

    async def fetch_councillors(self, file_path: Path) -> list[SangiinCandidateRecord]:
        """giin.jsonを読み込み、参議院議員データのリストを返す.

        Args:
            file_path: giin.jsonファイルのパス

        Returns:
            参議院議員候補者レコードのリスト
        """
        raw_data = self._load_json(file_path)

        if len(raw_data) < 2:
            logger.warning("giin.jsonにデータ行がありません")
            return []

        # ヘッダー行（index 0）をスキップ
        records: list[SangiinCandidateRecord] = []
        for i, row in enumerate(raw_data[1:], start=1):
            try:
                record = self._parse_row(row)
                records.append(record)
            except (IndexError, ValueError) as e:
                logger.warning("行 %d のパースに失敗: %s", i, e)
                continue

        logger.info("giin.jsonから %d 件の議員データを取得", len(records))
        return records

    def _load_json(self, file_path: Path) -> list[list[Any]]:
        """JSONファイルを読み込む."""
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)

    def _parse_row(self, row: list[Any]) -> SangiinCandidateRecord:
        """1行分のデータをSangiinCandidateRecordに変換する."""
        if len(row) < _EXPECTED_FIELDS:
            msg = f"フィールド数不足: {len(row)} < {_EXPECTED_FIELDS}"
            raise ValueError(msg)

        name = str(row[_IDX_NAME]).strip()
        furigana = str(row[_IDX_FURIGANA]).strip()
        party_name = str(row[_IDX_PARTY]).strip()
        district_name = str(row[_IDX_DISTRICT]).strip()
        elected_years = self._parse_elected_years(row[_IDX_ELECTED_YEARS])
        election_count = int(row[_IDX_ELECTION_COUNT])
        profile_url = str(row[_IDX_PROFILE_URL]).strip() or None

        return SangiinCandidateRecord(
            name=name,
            furigana=furigana,
            party_name=party_name,
            district_name=district_name,
            elected_years=elected_years,
            election_count=election_count,
            profile_url=profile_url,
            is_proportional=district_name == _PROPORTIONAL_DISTRICT,
        )

    @staticmethod
    def _parse_elected_years(value: Any) -> list[int]:
        """当選年フィールドをパースしてリストに変換する.

        giin.jsonでは「当選年」がカンマ区切り文字列（例: "2019, 2013"）
        または整数値で格納されている。

        Args:
            value: 当選年フィールドの値

        Returns:
            当選年のリスト（新しい順にソート）
        """
        if isinstance(value, int):
            return [value]

        raw = str(value).strip()
        if not raw:
            return []

        years: list[int] = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                years.append(int(part))
        # 新しい順にソート
        years.sort(reverse=True)
        return years
