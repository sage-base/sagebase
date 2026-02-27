"""総務省参議院比例代表スクレイパーのテスト."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.infrastructure.importers.soumu_sangiin_proportional_scraper import (
    SangiinProportionalXlsInfo,
    download_sangiin_proportional_xls,
    fetch_sangiin_proportional_xls_urls,
)


MOCK_HTML_WITH_PROPORTIONAL = """
<html>
<body>
<a href="/main_content/000001.xls">（１０）党派別名簿登載者別得票数（比例代表）</a>
<a href="/main_content/000002.xls">（３）党派別得票数（比例代表）</a>
<a href="/main_content/000003.xlsx">（１１）名簿登載者別得票数（比例代表）</a>
<a href="/main_content/000004.pdf">PDF資料</a>
<a href="/main_content/000005.xls">選挙区データ</a>
</body>
</html>
"""

MOCK_HTML_NO_PROPORTIONAL = """
<html>
<body>
<a href="/main_content/000001.xls">選挙区データ</a>
<a href="/main_content/000002.pdf">概要</a>
</body>
</html>
"""


class TestFetchSangiinProportionalXlsUrls:
    """indexページからのURL抽出テスト."""

    @patch(
        "src.infrastructure.importers.soumu_sangiin_proportional_scraper._fetch_html"
    )
    def test_extracts_proportional_xls_links(self, mock_fetch: MagicMock) -> None:
        """比例代表XLSリンクを正しく抽出する."""
        mock_fetch.return_value = MOCK_HTML_WITH_PROPORTIONAL
        results = fetch_sangiin_proportional_xls_urls(24)

        assert len(results) == 3
        assert results[0].link_text == "（１０）党派別名簿登載者別得票数（比例代表）"
        assert results[0].file_extension == ".xls"
        assert results[1].link_text == "（３）党派別得票数（比例代表）"
        assert results[2].file_extension == ".xlsx"

    @patch(
        "src.infrastructure.importers.soumu_sangiin_proportional_scraper._fetch_html"
    )
    def test_ignores_non_xls_links(self, mock_fetch: MagicMock) -> None:
        """PDFや非比例代表リンクは除外される."""
        mock_fetch.return_value = MOCK_HTML_WITH_PROPORTIONAL
        results = fetch_sangiin_proportional_xls_urls(24)

        urls = [r.url for r in results]
        assert not any("000004" in u for u in urls)
        assert not any("000005" in u for u in urls)

    @patch(
        "src.infrastructure.importers.soumu_sangiin_proportional_scraper._fetch_html"
    )
    def test_returns_empty_for_no_proportional(self, mock_fetch: MagicMock) -> None:
        """比例代表リンクがない場合は空リスト."""
        mock_fetch.return_value = MOCK_HTML_NO_PROPORTIONAL
        results = fetch_sangiin_proportional_xls_urls(24)
        assert results == []

    def test_unsupported_election_returns_empty(self) -> None:
        """未対応の選挙回次は空リスト."""
        results = fetch_sangiin_proportional_xls_urls(15)
        assert results == []

    @patch(
        "src.infrastructure.importers.soumu_sangiin_proportional_scraper._fetch_html"
    )
    def test_fetch_failure_returns_empty(self, mock_fetch: MagicMock) -> None:
        """HTML取得失敗時は空リスト."""
        mock_fetch.side_effect = OSError("Connection refused")
        results = fetch_sangiin_proportional_xls_urls(24)
        assert results == []

    @patch(
        "src.infrastructure.importers.soumu_sangiin_proportional_scraper._fetch_html"
    )
    def test_urls_are_absolute(self, mock_fetch: MagicMock) -> None:
        """抽出されたURLは絶対URLになっている."""
        mock_fetch.return_value = MOCK_HTML_WITH_PROPORTIONAL
        results = fetch_sangiin_proportional_xls_urls(24)

        for r in results:
            assert r.url.startswith("https://")


class TestDownloadSangiinProportionalXls:
    """XLSダウンロードのテスト."""

    @patch(
        "src.infrastructure.importers.soumu_sangiin_proportional_scraper._download_file"
    )
    @patch("src.infrastructure.importers.soumu_sangiin_proportional_scraper.time.sleep")
    def test_downloads_files(
        self,
        mock_sleep: MagicMock,
        mock_download: MagicMock,
        tmp_path: Path,
    ) -> None:
        """ファイルをダウンロードしてパスを返す."""

        def fake_download(url: str, dest: Path) -> Path:
            dest.write_text("dummy")
            return dest

        mock_download.side_effect = fake_download
        xls_files = [
            SangiinProportionalXlsInfo(
                url="https://example.com/1.xls",
                link_text="テスト",
                file_extension=".xls",
            ),
        ]
        results = download_sangiin_proportional_xls(xls_files, tmp_path, delay=0)
        assert len(results) == 1
        assert results[0][1].exists()

    def test_uses_cache_if_exists(self, tmp_path: Path) -> None:
        """キャッシュファイルが存在する場合はダウンロードしない."""
        cached = tmp_path / "proportional_0.xls"
        cached.write_text("cached data")

        xls_files = [
            SangiinProportionalXlsInfo(
                url="https://example.com/1.xls",
                link_text="テスト",
                file_extension=".xls",
            ),
        ]
        results = download_sangiin_proportional_xls(xls_files, tmp_path, delay=0)
        assert len(results) == 1

    @patch(
        "src.infrastructure.importers.soumu_sangiin_proportional_scraper._download_file"
    )
    @patch("src.infrastructure.importers.soumu_sangiin_proportional_scraper.time.sleep")
    def test_continues_on_download_failure(
        self,
        mock_sleep: MagicMock,
        mock_download: MagicMock,
        tmp_path: Path,
    ) -> None:
        """ダウンロード失敗時もスキップして続行."""
        mock_download.side_effect = OSError("Download failed")
        xls_files = [
            SangiinProportionalXlsInfo(
                url="https://example.com/1.xls",
                link_text="テスト",
                file_extension=".xls",
            ),
        ]
        results = download_sangiin_proportional_xls(xls_files, tmp_path, delay=0)
        assert results == []
