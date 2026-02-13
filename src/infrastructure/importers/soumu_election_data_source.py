"""総務省選挙データソースの実装 — Infrastructure layer.

IElectionDataSourceServiceの総務省XLSデータソース実装。
"""

import asyncio
import logging

from pathlib import Path

from src.domain.value_objects.election_candidate import CandidateRecord, ElectionInfo
from src.infrastructure.importers.soumu_election_scraper import (
    download_xls_files,
    fetch_xls_urls,
)
from src.infrastructure.importers.soumu_xls_parser import parse_xls_file


logger = logging.getLogger(__name__)


class SoumuElectionDataSource:
    """総務省XLSファイルからの選挙データソース実装."""

    async def fetch_candidates(
        self,
        election_number: int,
        download_dir: Path | None = None,
    ) -> tuple[ElectionInfo | None, list[CandidateRecord]]:
        """総務省XLSファイルから候補者データを取得する."""
        # 1. XLSファイルURLを取得（同期I/Oをスレッドプールで実行）
        logger.info("第%d回衆議院選挙のXLSファイルURL取得中...", election_number)
        xls_files = await asyncio.to_thread(fetch_xls_urls, election_number)
        if not xls_files:
            logger.error("XLSファイルが見つかりません")
            return None, []

        logger.info("%d個のXLSファイルを検出", len(xls_files))

        # 2. ダウンロード（同期I/Oをスレッドプールで実行）
        if download_dir is None:
            download_dir = Path("tmp") / f"soumu_election_{election_number}"
        downloaded = await asyncio.to_thread(
            download_xls_files, xls_files, download_dir
        )
        if not downloaded:
            logger.error("XLSファイルのダウンロードに失敗")
            return None, []

        # 3. パース
        all_candidates: list[CandidateRecord] = []
        election_info: ElectionInfo | None = None

        for xls_info, file_path in downloaded:
            parsed_info, candidates = await asyncio.to_thread(parse_xls_file, file_path)
            if parsed_info and election_info is None:
                election_info = parsed_info
            all_candidates.extend(candidates)
            logger.info(
                "%s: %d候補者を抽出",
                xls_info.prefecture_name,
                len(candidates),
            )

        logger.info("合計 %d 候補者を抽出", len(all_candidates))
        return election_info, all_candidates
