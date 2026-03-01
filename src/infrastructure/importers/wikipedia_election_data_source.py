"""Wikipedia衆議院選挙データソース.

Wikipedia APIからWikitextを取得し、当選者データを抽出する。
第1-44回（1890-2005年）に対応。
第1-40回: 中選挙区制（大選挙区制含む）
第41-44回: 小選挙区比例代表並立制
"""

import asyncio
import logging

from datetime import date
from pathlib import Path

from src.domain.value_objects.election_candidate import CandidateRecord, ElectionInfo
from src.infrastructure.importers._utils import fetch_wikipedia_wikitext
from src.infrastructure.importers.wikipedia_election_wikitext_parser import (
    parse_all_wikitext,
)


logger = logging.getLogger(__name__)

ELECTION_DATES: dict[int, date] = {
    1: date(1890, 7, 1),
    2: date(1892, 2, 15),
    3: date(1894, 3, 1),
    4: date(1894, 9, 1),
    5: date(1898, 3, 15),
    6: date(1898, 8, 10),
    7: date(1902, 8, 10),
    8: date(1903, 3, 1),
    9: date(1904, 3, 1),
    10: date(1908, 5, 15),
    11: date(1912, 5, 15),
    12: date(1915, 3, 25),
    13: date(1917, 4, 20),
    14: date(1920, 5, 10),
    15: date(1924, 5, 10),
    16: date(1928, 2, 20),
    17: date(1930, 2, 20),
    18: date(1932, 2, 20),
    19: date(1936, 2, 20),
    20: date(1937, 4, 30),
    21: date(1942, 4, 30),
    22: date(1946, 4, 10),
    23: date(1947, 4, 25),
    24: date(1949, 1, 23),
    25: date(1952, 10, 1),
    26: date(1953, 4, 19),
    27: date(1955, 2, 27),
    28: date(1958, 5, 22),
    29: date(1960, 11, 20),
    30: date(1963, 11, 21),
    31: date(1967, 1, 29),
    32: date(1969, 12, 27),
    33: date(1972, 12, 10),
    34: date(1976, 12, 5),
    35: date(1979, 10, 7),
    36: date(1980, 6, 22),
    37: date(1983, 12, 18),
    38: date(1986, 7, 6),
    39: date(1990, 2, 18),
    40: date(1993, 7, 18),
    41: date(1996, 10, 20),
    42: date(2000, 6, 25),
    43: date(2003, 11, 9),
    44: date(2005, 9, 11),
}

SUPPORTED_ELECTIONS: list[int] = list(range(1, 45))


class WikipediaElectionDataSource:
    """Wikipedia小選挙区+比例代表当選者テンプレートからの選挙データソース."""

    async def fetch_candidates(
        self,
        election_number: int,
        download_dir: Path | None = None,
    ) -> tuple[ElectionInfo | None, list[CandidateRecord]]:
        """Wikipedia Wikitextから当選者データを取得する."""
        if election_number not in SUPPORTED_ELECTIONS:
            logger.error(
                "第%d回はサポート対象外（対応: %s）",
                election_number,
                SUPPORTED_ELECTIONS,
            )
            return None, []

        logger.info("第%d回衆議院選挙のWikitextを取得中...", election_number)
        page_title = f"第{election_number}回衆議院議員総選挙"
        wikitext = await asyncio.to_thread(fetch_wikipedia_wikitext, page_title)
        logger.info("Wikitext取得完了（%d文字）", len(wikitext))

        candidates = parse_all_wikitext(wikitext, election_number)
        logger.info("当選者 %d名を抽出（小選挙区+比例代表）", len(candidates))

        election_info = ElectionInfo(
            election_number=election_number,
            election_date=ELECTION_DATES[election_number],
        )

        return election_info, candidates
