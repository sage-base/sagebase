"""総務省参議院選挙データスクレイパー.

総務省の参議院選挙結果ページから都道府県別XLS/XLSXファイルのURLを抽出し、
ダウンロードする。

ページ構造:
    - メインページ: sangiin{n}/index.html
    - 候補者別データ一覧: sangiin{n}/sangiin{n}_8.html
    - 都道府県別: sangiin{n}/sangiin{n}_8_{code}.html
        各ページに「選挙結果」「得票数」「得票率」のXLS/XLSXリンクがある。

対応回次: 第21回(2007年)〜第27回(2025年)
"""

import logging
import time
import urllib.request

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag


logger = logging.getLogger(__name__)

BASE_URL = "https://www.soumu.go.jp"

# 候補者別データの一覧ページURL
CANDIDATE_DATA_URL_TEMPLATE = (
    BASE_URL
    + "/senkyo/senkyo_s/data/sangiin{election_number}"
    + "/sangiin{election_number}_8.html"
)

# 対応する選挙回次
SANGIIN_SUPPORTED_ELECTIONS = list(range(21, 28))

# 回次→選挙日マッピング
SANGIIN_ELECTION_DATES: dict[int, date] = {
    21: date(2007, 7, 29),
    22: date(2010, 7, 11),
    23: date(2013, 7, 21),
    24: date(2016, 7, 10),
    25: date(2019, 7, 21),
    26: date(2022, 7, 10),
    27: date(2025, 7, 6),
}

# XLSリンクのラベルパターン（選挙区候補者別得票数を優先）
SANGIIN_VOTE_DATA_LABELS = ["選挙結果", "得票数", "候補者"]


@dataclass
class SangiinXlsFileInfo:
    """参議院XLSファイルのメタデータ."""

    url: str
    page_code: str
    """サブページコード（例: "01", "02"）."""
    link_text: str
    """ダウンロードリンクのテキスト."""
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


def get_sangiin_candidate_data_url(election_number: int) -> str:
    """選挙回次の候補者別データ一覧ページURLを返す."""
    return CANDIDATE_DATA_URL_TEMPLATE.format(election_number=election_number)


def fetch_subpage_urls(election_number: int) -> list[tuple[str, str]]:
    """候補者別データ一覧ページからサブページURL一覧を取得する.

    Args:
        election_number: 選挙回次（21-27）

    Returns:
        (サブページコード, 完全URL) のリスト
    """
    main_url = get_sangiin_candidate_data_url(election_number)
    html = _fetch_html(main_url)
    soup = BeautifulSoup(html, "html.parser")

    results: list[tuple[str, str]] = []
    prefix = f"sangiin{election_number}_8_"

    for element in soup.find_all("a", href=True):
        if not isinstance(element, Tag):
            continue
        href = str(element.get("href", ""))
        if prefix not in href:
            continue
        # サブページコードを抽出（例: "01", "47"）
        suffix = href.split(prefix)[-1]
        code = suffix.replace(".html", "")
        if not code.isdigit():
            continue
        full_url = urljoin(main_url, href)
        results.append((code, full_url))

    logger.info("第%d回: %d個のサブページを検出", election_number, len(results))
    return results


def _find_candidate_xls_url(
    soup: BeautifulSoup, base_url: str
) -> tuple[str, str] | None:
    """サブページから候補者別得票数XLSのURLを見つける.

    優先順位:
    1. 「選挙結果」ラベルのXLSリンク
    2. 「得票数」ラベルのXLSリンク
    3. 「候補者」ラベルのXLSリンク
    4. 最初のXLSリンク

    Returns:
        (link_text, full_url) or None
    """
    xls_links: list[tuple[str, str]] = []

    for element in soup.find_all("a", href=True):
        if not isinstance(element, Tag):
            continue
        href = str(element.get("href", ""))
        if not (href.endswith(".xls") or href.endswith(".xlsx")):
            continue
        link_text = element.get_text(strip=True)
        full_url = urljoin(base_url, href)
        xls_links.append((link_text, full_url))

    if not xls_links:
        return None

    # 優先ラベルで検索
    for label in SANGIIN_VOTE_DATA_LABELS:
        for link_text, url in xls_links:
            if label in link_text:
                return link_text, url

    # フォールバック: 最初のXLSリンク
    return xls_links[0]


def fetch_sangiin_xls_urls(
    election_number: int,
) -> list[SangiinXlsFileInfo]:
    """指定選挙回次の都道府県別XLS URL一覧を取得する.

    Args:
        election_number: 選挙回次（21-27）

    Returns:
        XLSファイル情報のリスト
    """
    if election_number not in SANGIIN_SUPPORTED_ELECTIONS:
        logger.error(
            "未対応の選挙回次: %d（対応: %s）",
            election_number,
            SANGIIN_SUPPORTED_ELECTIONS,
        )
        return []

    subpages = fetch_subpage_urls(election_number)
    if not subpages:
        logger.error("サブページが見つかりません")
        return []

    results: list[SangiinXlsFileInfo] = []
    for code, subpage_url in subpages:
        try:
            html = _fetch_html(subpage_url)
        except Exception:
            logger.warning("サブページ取得失敗: code=%s, url=%s", code, subpage_url)
            continue

        soup = BeautifulSoup(html, "html.parser")
        xls_info = _find_candidate_xls_url(soup, subpage_url)

        if xls_info:
            link_text, xls_url = xls_info
            ext = ".xlsx" if xls_url.endswith(".xlsx") else ".xls"
            results.append(
                SangiinXlsFileInfo(
                    url=xls_url,
                    page_code=code,
                    link_text=link_text,
                    file_extension=ext,
                )
            )
        else:
            logger.warning("XLSリンクが見つかりません: code=%s", code)

        # サーバー負荷を避けるためスリープ
        time.sleep(0.5)

    logger.info("第%d回: %d個のXLSファイルを検出", election_number, len(results))
    return results


def download_sangiin_xls_files(
    xls_files: list[SangiinXlsFileInfo],
    dest_dir: Path,
    delay: float = 0.5,
) -> list[tuple[SangiinXlsFileInfo, Path]]:
    """XLSファイルをダウンロードする.

    Args:
        xls_files: ダウンロード対象のXLSファイル情報リスト
        dest_dir: ダウンロード先ディレクトリ
        delay: ダウンロード間のスリープ秒数

    Returns:
        (XLSファイル情報, ダウンロード先パス) のリスト
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    results: list[tuple[SangiinXlsFileInfo, Path]] = []

    for xls_info in xls_files:
        filename = f"page_{xls_info.page_code}{xls_info.file_extension}"
        dest_path = dest_dir / filename

        # キャッシュチェック
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
