"""総務省参議院選挙スクレイパーの純粋関数テスト."""

from bs4 import BeautifulSoup

from src.infrastructure.importers.soumu_sangiin_election_scraper import (
    SANGIIN_ELECTION_DATES,
    SANGIIN_SUPPORTED_ELECTIONS,
    _find_candidate_xls_url,
    get_sangiin_candidate_data_url,
)


class TestFindCandidateXlsUrl:
    """候補者別XLS URL検索のテスト."""

    def test_senkyokekka_label_preferred(self) -> None:
        """「選挙結果」ラベルが最優先される."""
        html = """
        <html><body>
        <a href="other.xls">その他データ</a>
        <a href="result.xlsx">選挙結果</a>
        <a href="votes.xlsx">得票数</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _find_candidate_xls_url(soup, "https://example.com/page.html")
        assert result is not None
        assert result[1] == "https://example.com/result.xlsx"

    def test_tokuhyousuu_label_fallback(self) -> None:
        """「得票数」ラベルにフォールバックする."""
        html = """
        <html><body>
        <a href="other.xls">その他データ</a>
        <a href="votes.xlsx">得票数</a>
        <a href="rate.xlsx">得票率</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _find_candidate_xls_url(soup, "https://example.com/page.html")
        assert result is not None
        assert result[1] == "https://example.com/votes.xlsx"

    def test_kouhosya_label_fallback(self) -> None:
        """「候補者」ラベルにフォールバックする."""
        html = """
        <html><body>
        <a href="candidate.xls">候補者別データ</a>
        <a href="rate.xlsx">得票率</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _find_candidate_xls_url(soup, "https://example.com/page.html")
        assert result is not None
        assert result[1] == "https://example.com/candidate.xls"

    def test_first_xls_as_fallback(self) -> None:
        """ラベルが一致しない場合、最初のXLSリンクを返す."""
        html = """
        <html><body>
        <a href="data1.xls">データ1</a>
        <a href="data2.xlsx">データ2</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _find_candidate_xls_url(soup, "https://example.com/page.html")
        assert result is not None
        assert result[1] == "https://example.com/data1.xls"

    def test_no_xls_links(self) -> None:
        """XLSリンクがない場合Noneを返す."""
        html = """
        <html><body>
        <a href="page.html">ページ</a>
        <a href="file.pdf">PDFファイル</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _find_candidate_xls_url(soup, "https://example.com/page.html")
        assert result is None

    def test_relative_url_resolved(self) -> None:
        """相対URLが正しく解決される."""
        html = """
        <html><body>
        <a href="../main_content/vote.xlsx">選挙結果</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _find_candidate_xls_url(soup, "https://example.com/senkyo/page.html")
        assert result is not None
        assert result[1] == "https://example.com/main_content/vote.xlsx"


class TestGetSangiinCandidateDataUrl:
    """候補者別データURL生成のテスト."""

    def test_election_26(self) -> None:
        url = get_sangiin_candidate_data_url(26)
        assert "sangiin26" in url
        assert url.endswith("sangiin26_8.html")

    def test_election_21(self) -> None:
        url = get_sangiin_candidate_data_url(21)
        assert "sangiin21" in url


class TestSupportedElections:
    """対応選挙回次のテスト."""

    def test_range(self) -> None:
        assert SANGIIN_SUPPORTED_ELECTIONS == [21, 22, 23, 24, 25, 26, 27]


class TestElectionDates:
    """選挙日マッピングのテスト."""

    def test_all_supported_elections_have_dates(self) -> None:
        for election_number in SANGIIN_SUPPORTED_ELECTIONS:
            assert election_number in SANGIIN_ELECTION_DATES

    def test_election_26_date(self) -> None:
        d = SANGIIN_ELECTION_DATES[26]
        assert d.year == 2022
        assert d.month == 7
        assert d.day == 10
