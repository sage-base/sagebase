"""総務省参議院比例代表データソース.

IProportionalElectionDataSourceServiceを実装し、
参議院比例代表XLSファイルから候補者データを取得する。
"""

import asyncio
import logging

from pathlib import Path

from src.domain.services.interfaces.proportional_election_data_source_service import (
    IProportionalElectionDataSourceService,
)
from src.domain.value_objects.proportional_candidate import (
    ProportionalCandidateRecord,
    ProportionalElectionInfo,
)
from src.infrastructure.importers.soumu_sangiin_election_scraper import (
    SANGIIN_ELECTION_DATES,
)
from src.infrastructure.importers.soumu_sangiin_proportional_scraper import (
    download_sangiin_proportional_xls,
    fetch_sangiin_proportional_xls_urls,
)
from src.infrastructure.importers.soumu_sangiin_proportional_xls_parser import (
    parse_sangiin_proportional_xls,
)


logger = logging.getLogger(__name__)


class SoumuSangiinProportionalDataSource(IProportionalElectionDataSourceService):
    """総務省参議院比例代表XLSから候補者データを取得するデータソース."""

    async def fetch_proportional_candidates(
        self,
        election_number: int,
        download_dir: Path | None = None,
    ) -> tuple[ProportionalElectionInfo | None, list[ProportionalCandidateRecord]]:
        """総務省XLSファイルから参議院比例代表候補者データを取得する."""
        logger.info("第%d回参議院比例代表のXLSファイルURL取得中...", election_number)
        xls_files = await asyncio.to_thread(
            fetch_sangiin_proportional_xls_urls, election_number
        )
        if not xls_files:
            logger.error("比例代表XLSファイルが見つかりません")
            return None, []

        logger.info("%d個の比例代表XLSファイルを検出", len(xls_files))

        if download_dir is None:
            download_dir = Path("tmp") / f"soumu_sangiin_proportional_{election_number}"
        downloaded = await asyncio.to_thread(
            download_sangiin_proportional_xls, xls_files, download_dir
        )
        if not downloaded:
            logger.error("比例代表XLSファイルのダウンロードに失敗")
            return None, []

        all_candidates: list[ProportionalCandidateRecord] = []
        election_info: ProportionalElectionInfo | None = None

        for _xls_info, file_path in downloaded:
            parsed_info, candidates = await asyncio.to_thread(
                parse_sangiin_proportional_xls, file_path, election_number
            )
            if parsed_info and election_info is None:
                election_info = parsed_info
            # 当選者を含むファイルのみ採用（集計表ファイルを除外）
            if any(c.is_elected for c in candidates):
                all_candidates.extend(candidates)
                break

        if election_info is None and election_number in SANGIIN_ELECTION_DATES:
            election_info = ProportionalElectionInfo(
                election_number=election_number,
                election_date=SANGIIN_ELECTION_DATES[election_number],
            )

        elected = sum(1 for c in all_candidates if c.is_elected)
        logger.info(
            "合計 %d 候補者を抽出（当選 %d 名）",
            len(all_candidates),
            elected,
        )
        return election_info, all_candidates
