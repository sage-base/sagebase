"""総務省参議院比例代表データスクレイパー.

総務省のindexページから参議院比例代表XLS/XLSXファイルのURLを抽出し、
ダウンロードする。

ページ構造:
    - indexページ: sangiin{n}/index.html
    - 比例代表XLSリンクは「比例代表」を含むリンクテキストで配置
    - XLSファイルは /main_content/NNNNNN.xls 形式

対応回次: 第21回(2007年)〜第27回(2025年)
"""

import logging
import time
import urllib.request

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from src.infrastructure.importers.soumu_sangiin_election_scraper import (
    SANGIIN_SUPPORTED_ELECTIONS,
)


logger = logging.getLogger(__name__)

BASE_URL = "https://www.soumu.go.jp"
INDEX_URL_TEMPLATE = (
    BASE_URL + "/senkyo/senkyo_s/data/sangiin{election_number}/index.html"
)

PROPORTIONAL_LINK_LABELS = ["名簿登載者別得票数", "比例代表"]


@dataclass
class SangiinProportionalXlsInfo:
    """参議院比例代表XLSファイルのメタデータ."""

    url: str
    link_text: str
    file_extension: str


def _fetch_html(url: str) -> str:
    """URLからHTMLを取得する."""
    logger.info("HTML取得中: %s", url)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; SagebaseBot/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310  # nosec B310
        content = response.read()

    for encoding in ["utf-8", "shift_jis", "euc-jp", "cp932"]:
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue

    return content.decode("utf-8", errors="replace")


def _download_file(url: str, dest_path: Path) -> Path:
    """ファイルをダウンロードする."""
    logger.info("ダウンロード中: %s → %s", url, dest_path)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; SagebaseBot/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:  # noqa: S310  # nosec B310
        dest_path.write_bytes(response.read())
    return dest_path


def fetch_sangiin_proportional_xls_urls(
    election_number: int,
) -> list[SangiinProportionalXlsInfo]:
    """indexページから比例代表XLSファイルURLを取得する.

    Args:
        election_number: 選挙回次（21-27）

    Returns:
        比例代表XLSファイル情報のリスト
    """
    if election_number not in SANGIIN_SUPPORTED_ELECTIONS:
        logger.error(
            "未対応の選挙回次: %d（対応: %s）",
            election_number,
            SANGIIN_SUPPORTED_ELECTIONS,
        )
        return []

    index_url = INDEX_URL_TEMPLATE.format(election_number=election_number)
    try:
        html = _fetch_html(index_url)
    except Exception:
        logger.exception("indexページ取得失敗: %s", index_url)
        return []

    soup = BeautifulSoup(html, "html.parser")
    results: list[SangiinProportionalXlsInfo] = []

    for element in soup.find_all("a", href=True):
        if not isinstance(element, Tag):
            continue
        href = str(element.get("href", ""))
        link_text = element.get_text(strip=True)

        if not (href.endswith(".xls") or href.endswith(".xlsx")):
            continue

        is_proportional = any(label in link_text for label in PROPORTIONAL_LINK_LABELS)
        if not is_proportional:
            continue

        full_url = urljoin(index_url, href)
        ext = ".xlsx" if href.endswith(".xlsx") else ".xls"
        results.append(
            SangiinProportionalXlsInfo(
                url=full_url,
                link_text=link_text,
                file_extension=ext,
            )
        )

    logger.info(
        "第%d回: %d個の比例代表XLSファイルを検出", election_number, len(results)
    )
    return results


def download_sangiin_proportional_xls(
    xls_files: list[SangiinProportionalXlsInfo],
    dest_dir: Path,
    delay: float = 0.5,
) -> list[tuple[SangiinProportionalXlsInfo, Path]]:
    """比例代表XLSファイルをダウンロードする.

    Args:
        xls_files: ダウンロード対象のXLSファイル情報リスト
        dest_dir: ダウンロード先ディレクトリ
        delay: ダウンロード間のスリープ秒数

    Returns:
        (XLSファイル情報, ダウンロード先パス) のリスト
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    results: list[tuple[SangiinProportionalXlsInfo, Path]] = []

    for idx, xls_info in enumerate(xls_files):
        filename = f"proportional_{idx}{xls_info.file_extension}"
        dest_path = dest_dir / filename

        if dest_path.exists() and dest_path.stat().st_size > 0:
            logger.info("キャッシュ利用: %s", dest_path)
            results.append((xls_info, dest_path))
            continue

        try:
            _download_file(xls_info.url, dest_path)
            results.append((xls_info, dest_path))
        except Exception:
            logger.exception("ダウンロード失敗: %s", xls_info.url)
            continue

        time.sleep(delay)

    logger.info("%d / %d ファイルをダウンロード完了", len(results), len(xls_files))
    return results
