"""総務省比例代表選挙データソースの実装 — Infrastructure layer.

IProportionalElectionDataSourceServiceの実装。
選挙回次に応じてXLSパーサーまたはGemini PDF抽出を呼び分ける。
"""

import asyncio
import logging
import urllib.request

from pathlib import Path

from src.domain.value_objects.proportional_candidate import (
    ProportionalCandidateRecord,
    ProportionalElectionInfo,
)
from src.infrastructure.importers._constants import (
    PROPORTIONAL_PDF_URLS,
    PROPORTIONAL_SUPPORTED_ELECTIONS,
    PROPORTIONAL_XLS_URLS,
)


logger = logging.getLogger(__name__)


def _download_to(url: str, dest_path: Path) -> Path:
    """ファイルをダウンロードする."""
    logger.info("ダウンロード中: %s → %s", url, dest_path)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; SagebaseBot/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:  # noqa: S310  # nosec B310
        dest_path.write_bytes(response.read())
    return dest_path


class SoumuProportionalDataSource:
    """総務省比例代表データソース実装."""

    def __init__(self, api_key: str | None = None) -> None:
        """初期化.

        Args:
            api_key: Google API Key（PDF抽出に使用、省略時は環境変数から取得）
        """
        self._api_key = api_key

    async def fetch_proportional_candidates(
        self,
        election_number: int,
        download_dir: Path | None = None,
    ) -> tuple[
        ProportionalElectionInfo | None,
        list[ProportionalCandidateRecord],
    ]:
        """比例代表候補者データを取得する."""
        if election_number not in PROPORTIONAL_SUPPORTED_ELECTIONS:
            logger.error(
                "未対応の選挙回次: %d（対応: %s）",
                election_number,
                PROPORTIONAL_SUPPORTED_ELECTIONS,
            )
            return None, []

        if download_dir is None:
            download_dir = Path("tmp") / f"soumu_proportional_{election_number}"
        download_dir.mkdir(parents=True, exist_ok=True)

        if election_number in PROPORTIONAL_XLS_URLS:
            return await self._fetch_from_xls(election_number, download_dir)
        elif election_number in PROPORTIONAL_PDF_URLS:
            return await self._fetch_from_pdf(election_number, download_dir)
        else:
            logger.error("第%d回のデータソースが見つかりません", election_number)
            return None, []

    async def _fetch_from_xls(
        self,
        election_number: int,
        download_dir: Path,
    ) -> tuple[
        ProportionalElectionInfo | None,
        list[ProportionalCandidateRecord],
    ]:
        """XLSファイルから候補者データを取得する."""
        from src.infrastructure.importers.soumu_proportional_xls_parser import (
            parse_proportional_xls,
        )

        url = PROPORTIONAL_XLS_URLS[election_number]
        ext = ".xlsx" if url.endswith(".xlsx") else ".xls"
        file_path = download_dir / f"proportional_{election_number}{ext}"

        if not (file_path.exists() and file_path.stat().st_size > 0):
            logger.info("XLSダウンロード中: %s", url)
            await asyncio.to_thread(_download_to, url, file_path)

        logger.info("XLSパース中: %s", file_path)
        return await asyncio.to_thread(parse_proportional_xls, file_path)

    async def _fetch_from_pdf(
        self,
        election_number: int,
        download_dir: Path,
    ) -> tuple[
        ProportionalElectionInfo | None,
        list[ProportionalCandidateRecord],
    ]:
        """PDFファイルからGemini APIで候補者データを抽出する."""
        from src.infrastructure.importers.soumu_proportional_pdf_extractor import (
            extract_from_pdf,
        )

        url = PROPORTIONAL_PDF_URLS[election_number]
        file_path = download_dir / f"proportional_{election_number}.pdf"

        if not (file_path.exists() and file_path.stat().st_size > 0):
            logger.info("PDFダウンロード中: %s", url)
            await asyncio.to_thread(_download_to, url, file_path)

        logger.info("Gemini PDF抽出中: %s", file_path)
        return await asyncio.to_thread(
            extract_from_pdf,
            file_path,
            election_number,
            self._api_key,
        )
