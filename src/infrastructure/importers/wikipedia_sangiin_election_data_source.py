"""Wikipedia参議院選挙データソース.

Wikipedia APIからWikitextを取得し、当選者データを抽出する。
第1-27回（1947-2025年）に対応。

第1-12回: 地方区 + 全国区
第13-18回: 選挙区 + 拘束名簿式比例代表
第19-27回: 選挙区 + 非拘束名簿式比例代表
"""

import asyncio
import logging

from datetime import date
from pathlib import Path

from src.domain.value_objects.election_candidate import CandidateRecord, ElectionInfo
from src.infrastructure.importers._utils import fetch_wikipedia_wikitext
from src.infrastructure.importers.wikipedia_sangiin_election_wikitext_parser import (
    parse_sangiin_wikitext,
)


logger = logging.getLogger(__name__)

# 参議院議員通常選挙の選挙日マッピング
SANGIIN_ELECTION_DATES: dict[int, date] = {
    1: date(1947, 4, 20),
    2: date(1950, 6, 4),
    3: date(1953, 4, 24),
    4: date(1956, 7, 8),
    5: date(1959, 6, 2),
    6: date(1962, 7, 1),
    7: date(1965, 7, 4),
    8: date(1968, 7, 7),
    9: date(1971, 6, 27),
    10: date(1974, 7, 7),
    11: date(1977, 7, 10),
    12: date(1980, 6, 22),
    13: date(1983, 6, 26),
    14: date(1986, 7, 6),
    15: date(1989, 7, 23),
    16: date(1992, 7, 26),
    17: date(1995, 7, 23),
    18: date(1998, 7, 12),
    19: date(2001, 7, 29),
    20: date(2004, 7, 11),
    21: date(2007, 7, 29),
    22: date(2010, 7, 11),
    23: date(2013, 7, 21),
    24: date(2016, 7, 10),
    25: date(2019, 7, 21),
    26: date(2022, 7, 10),
    27: date(2025, 7, 6),
}

SUPPORTED_SANGIIN_ELECTIONS: list[int] = list(range(1, 28))


class WikipediaSangiinElectionDataSource:
    """Wikipedia参議院選挙当選者テンプレート/wikitableからの選挙データソース."""

    async def fetch_candidates(
        self,
        election_number: int,
        download_dir: Path | None = None,
    ) -> tuple[ElectionInfo | None, list[CandidateRecord]]:
        """Wikipedia Wikitextから参議院選挙当選者データを取得する."""
        if election_number not in SUPPORTED_SANGIIN_ELECTIONS:
            logger.error(
                "第%d回はサポート対象外（対応: %s）",
                election_number,
                SUPPORTED_SANGIIN_ELECTIONS,
            )
            return None, []

        logger.info("第%d回参議院選挙のWikitextを取得中...", election_number)
        page_title = f"第{election_number}回参議院議員通常選挙"
        wikitext = await asyncio.to_thread(fetch_wikipedia_wikitext, page_title)
        logger.info("Wikitext取得完了（%d文字）", len(wikitext))

        candidates = parse_sangiin_wikitext(wikitext, election_number)
        logger.info(
            "当選者 %d名を抽出（選挙区+比例/全国区）",
            len(candidates),
        )

        election_info = ElectionInfo(
            election_number=election_number,
            election_date=SANGIIN_ELECTION_DATES[election_number],
        )

        return election_info, candidates
