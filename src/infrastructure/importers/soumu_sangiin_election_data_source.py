"""総務省参議院選挙データソース.

総務省が公開するXLS/XLSXファイルから参議院選挙区の全候補者データを取得する。
IElectionDataSourceService プロトコルの実装。
"""

import asyncio
import logging

from pathlib import Path

from src.domain.value_objects.election_candidate import CandidateRecord, ElectionInfo
from src.infrastructure.importers.soumu_sangiin_election_scraper import (
    SANGIIN_ELECTION_DATES,
    download_sangiin_xls_files,
    fetch_sangiin_xls_urls,
)
from src.infrastructure.importers.soumu_sangiin_xls_parser import (
    parse_sangiin_xls_file,
)


logger = logging.getLogger(__name__)


class SoumuSangiinElectionDataSource:
    """総務省XLS/XLSXファイルから参議院選挙区の候補者データを取得するデータソース."""

    async def fetch_candidates(
        self,
        election_number: int,
        download_dir: Path | None = None,
    ) -> tuple[ElectionInfo | None, list[CandidateRecord]]:
        """総務省XLSファイルから候補者データを取得する."""
        # 1. XLSファイルURLを取得（同期I/Oをスレッドプールで実行）
        logger.info("第%d回参議院選挙のXLSファイルURL取得中...", election_number)
        xls_files = await asyncio.to_thread(fetch_sangiin_xls_urls, election_number)
        if not xls_files:
            logger.error("XLSファイルが見つかりません")
            return None, []

        logger.info("%d個のXLSファイルを検出", len(xls_files))

        # 2. ダウンロード（同期I/Oをスレッドプールで実行）
        if download_dir is None:
            download_dir = Path("tmp") / f"soumu_sangiin_election_{election_number}"
        downloaded = await asyncio.to_thread(
            download_sangiin_xls_files, xls_files, download_dir
        )
        if not downloaded:
            logger.error("XLSファイルのダウンロードに失敗")
            return None, []

        # 3. パース
        all_candidates: list[CandidateRecord] = []
        election_info: ElectionInfo | None = None
        seen_districts: set[str] = set()

        for xls_info, file_path in downloaded:
            parsed_info, candidates = await asyncio.to_thread(
                parse_sangiin_xls_file, file_path, election_number
            )
            if parsed_info and election_info is None:
                election_info = parsed_info

            # 重複選挙区チェック（同じ選挙区のデータが複数ページに存在する場合）
            for candidate in candidates:
                if candidate.district_name not in seen_districts:
                    all_candidates.append(candidate)
            if candidates:
                district = candidates[0].district_name
                if district not in seen_districts:
                    seen_districts.add(district)
                    logger.info(
                        "page_%s (%s): %d候補者を抽出",
                        xls_info.page_code,
                        district,
                        len(candidates),
                    )
                else:
                    logger.debug(
                        "重複選挙区スキップ: page_%s (%s)",
                        xls_info.page_code,
                        district,
                    )

        # election_info がない場合、定数マッピングからフォールバック
        if election_info is None and election_number in SANGIIN_ELECTION_DATES:
            election_info = ElectionInfo(
                election_number=election_number,
                election_date=SANGIIN_ELECTION_DATES[election_number],
            )

        logger.info("合計 %d 候補者を抽出", len(all_candidates))
        return election_info, all_candidates
