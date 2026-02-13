"""総務省選挙スクレイパーの純粋関数テスト."""

from bs4 import BeautifulSoup

from src.infrastructure.importers.soumu_election_scraper import (
    SUPPORTED_ELECTIONS,
    _find_vote_data_xls_url,
    _match_prefecture,
    get_election_page_url,
)


class TestMatchPrefecture:
    """都道府県マッチングのテスト."""

    def test_exact_match_hokkaido(self) -> None:
        assert _match_prefecture("北海道") == 0

    def test_exact_match_tokyo(self) -> None:
        assert _match_prefecture("東京都") == 12

    def test_exact_match_osaka(self) -> None:
        assert _match_prefecture("大阪府") == 26

    def test_exact_match_okinawa(self) -> None:
        assert _match_prefecture("沖縄県") == 46

    def test_partial_match(self) -> None:
        """都道府県名がテキスト先頭にある場合の部分一致."""
        assert _match_prefecture("北海道（小選挙区）") == 0

    def test_whitespace_stripped(self) -> None:
        assert _match_prefecture("  東京都  ") == 12

    def test_no_match(self) -> None:
        assert _match_prefecture("不明なテキスト") is None

    def test_empty_string(self) -> None:
        assert _match_prefecture("") is None

    def test_exact_match_preferred_over_partial(self) -> None:
        """完全一致が部分一致より優先される."""
        result = _match_prefecture("京都府")
        assert result == 25  # 京都府のインデックス（東京都ではなく）


class TestFindVoteDataXlsUrl:
    """得票数XLS URL検索のテスト."""

    def test_vote_data_label_preferred(self) -> None:
        """「得票数」ラベルが優先される."""
        html = """
        <html><body>
        <a href="other.xls">その他データ</a>
        <a href="vote.xls">候補者別得票数</a>
        <a href="result.xls">選挙結果データ</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _find_vote_data_xls_url(soup, "https://example.com/page.html")
        assert result == "https://example.com/vote.xls"

    def test_election_result_label_fallback(self) -> None:
        """「選挙結果」ラベルにフォールバックする."""
        html = """
        <html><body>
        <a href="other.xls">その他データ</a>
        <a href="result.xls">選挙結果データ</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _find_vote_data_xls_url(soup, "https://example.com/page.html")
        assert result == "https://example.com/result.xls"

    def test_first_xls_as_fallback(self) -> None:
        """ラベルが一致しない場合、最初のXLSリンクを返す."""
        html = """
        <html><body>
        <a href="data1.xls">データ1</a>
        <a href="data2.xlsx">データ2</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _find_vote_data_xls_url(soup, "https://example.com/page.html")
        assert result == "https://example.com/data1.xls"

    def test_no_xls_links(self) -> None:
        """XLSリンクがない場合Noneを返す."""
        html = """
        <html><body>
        <a href="page.html">ページ</a>
        <a href="file.pdf">PDFファイル</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _find_vote_data_xls_url(soup, "https://example.com/page.html")
        assert result is None

    def test_xlsx_extension_also_matched(self) -> None:
        """xlsxも対象になる."""
        html = """
        <html><body>
        <a href="vote_data.xlsx">得票数データ</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _find_vote_data_xls_url(soup, "https://example.com/page.html")
        assert result == "https://example.com/vote_data.xlsx"

    def test_relative_url_resolved(self) -> None:
        """相対URLが正しく解決される."""
        html = """
        <html><body>
        <a href="../data/vote.xls">得票数</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _find_vote_data_xls_url(soup, "https://example.com/dir/page.html")
        assert result == "https://example.com/data/vote.xls"


class TestGetElectionPageUrl:
    """選挙ページURL生成のテスト."""

    def test_election_50(self) -> None:
        url = get_election_page_url(50)
        assert "shugiin50" in url
        assert url.endswith("shikuchouson.html")

    def test_election_45(self) -> None:
        url = get_election_page_url(45)
        assert "shugiin45" in url


class TestSupportedElections:
    """対応選挙回次のテスト."""

    def test_range(self) -> None:
        assert SUPPORTED_ELECTIONS == [45, 46, 47, 48, 49, 50]
