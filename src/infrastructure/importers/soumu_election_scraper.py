"""総務省衆議院選挙データスクレイパー.

総務省のshikuchousonページからXLS/XLSXファイルのURLを抽出し、ダウンロードする。

ページ構造の差異:
    - 第50回 (2024): メインページに直接XLSXリンク（小選挙区/比例代表セクション）
    - 第45-49回: 都道府県別サブページ（shikuchouson_01.html〜47.html）にXLSリンク
"""

import logging
import time
import urllib.request

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from src.infrastructure.importers._constants import PREFECTURE_NAMES


logger = logging.getLogger(__name__)

BASE_URL = "https://www.soumu.go.jp"

# 選挙回次ごとのメインページURL
SHIKUCHOUSON_URL_TEMPLATE = (
    BASE_URL + "/senkyo/senkyo_s/data/shugiin{election_number}/shikuchouson.html"
)

# 都道府県サブページのURL
SUBPAGE_URL_TEMPLATE = (
    BASE_URL
    + "/senkyo/senkyo_s/data/shugiin{election_number}/shikuchouson_{pref_code:02d}.html"
)

# 対応する選挙回次
SUPPORTED_ELECTIONS = list(range(45, 51))

# 第50回は直接リンク形式
DIRECT_LINK_ELECTIONS = {50}

# XLSリンクのラベルパターン（得票数データ）
VOTE_DATA_LABELS = ["得票数", "選挙結果"]


@dataclass
class XlsFileInfo:
    """XLSファイルのメタデータ."""

    url: str
    prefecture_code: int
    prefecture_name: str
    file_extension: str


def _fetch_html(url: str) -> str:
    """URLからHTMLを取得する."""
    logger.info("HTML取得中: %s", url)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; SagebaseBot/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310
        content = response.read()

    # Shift_JISエンコーディングを試行
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
    with urllib.request.urlopen(req, timeout=60) as response:  # noqa: S310
        dest_path.write_bytes(response.read())
    return dest_path


def fetch_xls_urls(election_number: int) -> list[XlsFileInfo]:
    """指定選挙回次の小選挙区XLSファイルURL一覧を取得する.

    Args:
        election_number: 選挙回次（45-50）

    Returns:
        XLSファイル情報のリスト
    """
    if election_number not in SUPPORTED_ELECTIONS:
        logger.error(
            "未対応の選挙回次: %d（対応: %s）",
            election_number,
            SUPPORTED_ELECTIONS,
        )
        return []

    if election_number in DIRECT_LINK_ELECTIONS:
        return _fetch_direct_xls_urls(election_number)
    else:
        return _fetch_subpage_xls_urls(election_number)


def _fetch_direct_xls_urls(election_number: int) -> list[XlsFileInfo]:
    """メインページから直接XLSリンクを取得する（第50回用）."""
    url = SHIKUCHOUSON_URL_TEMPLATE.format(election_number=election_number)
    html = _fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    results: list[XlsFileInfo] = []
    seen_urls: set[str] = set()

    # 小選挙区セクションのリンクを取得
    # ページ内で都道府県名をリンクテキストとして持つXLS/XLSXリンクを抽出
    for element in soup.find_all("a", href=True):
        if not isinstance(element, Tag):
            continue
        href = str(element.get("href", ""))
        link_text = element.get_text(strip=True)

        # XLS/XLSXファイルのみ
        if not (href.endswith(".xlsx") or href.endswith(".xls")):
            continue

        full_url = urljoin(url, href)
        if full_url in seen_urls:
            continue

        # 比例代表のリンクを除外（「ブロック」が含まれる場合）
        if "ブロック" in link_text:
            continue

        # 都道府県名のリンクテキストかチェック（完全一致優先）
        matched_pref_idx = _match_prefecture(link_text)
        if matched_pref_idx is None:
            continue

        ext = ".xlsx" if href.endswith(".xlsx") else ".xls"
        seen_urls.add(full_url)
        results.append(
            XlsFileInfo(
                url=full_url,
                prefecture_code=matched_pref_idx + 1,
                prefecture_name=PREFECTURE_NAMES[matched_pref_idx],
                file_extension=ext,
            )
        )

    logger.info(
        "第%d回: %d個の小選挙区XLSファイルを検出", election_number, len(results)
    )
    return results


def _match_prefecture(text: str) -> int | None:
    """テキストから都道府県名を特定し、インデックスを返す.

    完全一致を優先し、部分一致はフォールバック。
    """
    stripped = text.strip()
    # 完全一致
    for idx, pref_name in enumerate(PREFECTURE_NAMES):
        if stripped == pref_name:
            return idx
    # 部分一致（都道府県名がテキストの先頭にある場合）
    for idx, pref_name in enumerate(PREFECTURE_NAMES):
        if stripped.startswith(pref_name):
            return idx
    return None


def _fetch_subpage_xls_urls(election_number: int) -> list[XlsFileInfo]:
    """サブページからXLSリンクを取得する（第45-49回用）."""
    results: list[XlsFileInfo] = []

    for pref_code in range(1, 48):
        pref_name = PREFECTURE_NAMES[pref_code - 1]
        subpage_url = SUBPAGE_URL_TEMPLATE.format(
            election_number=election_number, pref_code=pref_code
        )

        try:
            html = _fetch_html(subpage_url)
        except Exception:
            logger.warning("サブページ取得失敗: %s (%s)", pref_name, subpage_url)
            continue

        soup = BeautifulSoup(html, "html.parser")

        # XLSリンクを取得（得票数ラベルを優先）
        xls_url = _find_vote_data_xls_url(soup, subpage_url)
        if xls_url:
            ext = ".xlsx" if xls_url.endswith(".xlsx") else ".xls"
            results.append(
                XlsFileInfo(
                    url=xls_url,
                    prefecture_code=pref_code,
                    prefecture_name=pref_name,
                    file_extension=ext,
                )
            )
        else:
            logger.warning("XLSリンクが見つかりません: %s", pref_name)

        # サーバー負荷を避けるためスリープ
        time.sleep(0.5)

    logger.info(
        "第%d回: %d個の小選挙区XLSファイルを検出", election_number, len(results)
    )
    return results


def _find_vote_data_xls_url(soup: BeautifulSoup, base_url: str) -> str | None:
    """サブページから得票数XLSのURLを見つける.

    優先順位:
    1. 「得票数」ラベルのXLSリンク
    2. 「選挙結果」ラベルのXLSリンク
    3. 最初のXLSリンク
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
    for label in VOTE_DATA_LABELS:
        for link_text, url in xls_links:
            if label in link_text:
                return url

    # フォールバック: 最初のXLSリンク
    return xls_links[0][1]


def download_xls_files(
    xls_files: list[XlsFileInfo],
    dest_dir: Path,
    delay: float = 0.5,
) -> list[tuple[XlsFileInfo, Path]]:
    """XLSファイルをダウンロードする.

    Args:
        xls_files: ダウンロード対象のXLSファイル情報リスト
        dest_dir: ダウンロード先ディレクトリ
        delay: ダウンロード間のスリープ秒数

    Returns:
        (XLSファイル情報, ダウンロード先パス) のリスト
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    results: list[tuple[XlsFileInfo, Path]] = []

    for xls_info in xls_files:
        filename = f"pref_{xls_info.prefecture_code:02d}{xls_info.file_extension}"
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


def get_election_page_url(election_number: int) -> str:
    """選挙回次のメインページURLを返す."""
    return SHIKUCHOUSON_URL_TEMPLATE.format(election_number=election_number)
