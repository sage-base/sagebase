"""Tests for BAML party member extractor"""

from unittest.mock import AsyncMock, patch

import pytest

from src.party_member_extractor.baml_llm_extractor import BAMLPartyMemberExtractor
from src.party_member_extractor.models import WebPageContent


class TestBAMLPartyMemberExtractor:
    """Test cases for BAMLPartyMemberExtractor"""

    @pytest.fixture
    def extractor(self):
        """Create a BAMLPartyMemberExtractor instance"""
        return BAMLPartyMemberExtractor()

    @pytest.fixture
    def sample_page(self):
        """サンプルWebページ"""
        return WebPageContent(
            url="https://example.com/members",
            html_content="""
            <html>
            <body>
                <main>
                    <h1>議員一覧</h1>
                    <div class="member">
                        <h3>山田太郎</h3>
                        <p>衆議院議員</p>
                        <p>東京1区</p>
                        <a href="/profile/yamada">プロフィール</a>
                    </div>
                    <div class="member">
                        <h3>鈴木花子</h3>
                        <p>参議院議員</p>
                        <p>比例代表</p>
                        <p>幹事長</p>
                    </div>
                </main>
            </body>
            </html>
            """,
            page_number=1,
        )

    def test_extract_from_pages_success(self, extractor, sample_page):
        """複数ページからの抽出テスト（成功）"""

        # Mock BAML result
        class MockMember:
            def __init__(
                self,
                name,
                position=None,
                electoral_district=None,
                prefecture=None,
                profile_url=None,
                party_position=None,
            ):
                self.name = name
                self.position = position
                self.electoral_district = electoral_district
                self.prefecture = prefecture
                self.profile_url = profile_url
                self.party_position = party_position

        mock_result = [
            MockMember(
                "山田太郎",
                "衆議院議員",
                "東京1区",
                "東京都",
                "/profile/yamada",
                None,
            ),
            MockMember("鈴木花子", "参議院議員", "比例代表", None, None, "幹事長"),
        ]

        with patch(
            "src.party_member_extractor.baml_llm_extractor.b.ExtractPartyMembers",
            new_callable=AsyncMock,
            create=True,
        ) as mock_baml:
            mock_baml.return_value = mock_result

            # Execute
            result = extractor.extract_from_pages([sample_page], "テスト党")

            # Assert
            assert len(result.members) == 2
            assert result.members[0].name == "山田太郎"
            assert result.members[0].position == "衆議院議員"
            assert result.members[0].electoral_district == "東京1区"
            assert result.members[0].prefecture == "東京都"
            assert result.members[0].profile_url == "https://example.com/profile/yamada"
            assert result.members[1].name == "鈴木花子"
            assert result.members[1].party_position == "幹事長"

            # Verify BAML was called
            mock_baml.assert_called_once()

    def test_extract_from_pages_empty_result(self, extractor, sample_page):
        """空の結果のテスト"""
        with patch(
            "src.party_member_extractor.baml_llm_extractor.b.ExtractPartyMembers",
            new_callable=AsyncMock,
            create=True,
        ) as mock_baml:
            mock_baml.return_value = []

            # Execute
            result = extractor.extract_from_pages([sample_page], "テスト党")

            # Assert
            assert result.members == []
            assert result.total_count == 0

    def test_extract_from_pages_error_handling(self, extractor, sample_page):
        """エラーハンドリングのテスト"""
        with patch(
            "src.party_member_extractor.baml_llm_extractor.b.ExtractPartyMembers",
            new_callable=AsyncMock,
            create=True,
        ) as mock_baml:
            mock_baml.side_effect = Exception("BAML error")

            # Execute
            result = extractor.extract_from_pages([sample_page], "テスト党")

            # Assert - should return empty list on error
            assert result.members == []
            assert result.total_count == 0

    def test_truncates_long_content(self, extractor, caplog):
        """長いコンテンツの切り詰めテスト"""
        # Create very long HTML content
        long_html = "x" * 60000  # More than 50000 chars

        class MockMember:
            def __init__(
                self,
                name,
                position=None,
                electoral_district=None,
                prefecture=None,
                profile_url=None,
                party_position=None,
            ):
                self.name = name
                self.position = position
                self.electoral_district = electoral_district
                self.prefecture = prefecture
                self.profile_url = profile_url
                self.party_position = party_position

        page = WebPageContent(
            url="https://example.com/members",
            html_content=f"<html><body><main>{long_html}</main></body></html>",
            page_number=1,
        )

        with patch(
            "src.party_member_extractor.baml_llm_extractor.b.ExtractPartyMembers",
            new_callable=AsyncMock,
            create=True,
        ) as mock_baml:
            mock_baml.return_value = [MockMember("山田太郎", "衆議院議員")]

            # Execute
            extractor.extract_from_pages([page], "テスト党")

            # Assert - should log warning about truncation
            assert "Content too long" in caplog.text
            assert "truncating to 50000 chars" in caplog.text

            # Assert - BAML should be called with truncated content
            call_args = mock_baml.call_args[0]
            assert len(call_args[0]) <= 50003  # 50000 + "..."
            assert call_args[0].endswith("...")

    def test_duplicate_removal(self, extractor):
        """重複除去のテスト"""

        class MockMember:
            def __init__(
                self,
                name,
                position=None,
                electoral_district=None,
                prefecture=None,
                profile_url=None,
                party_position=None,
            ):
                self.name = name
                self.position = position
                self.electoral_district = electoral_district
                self.prefecture = prefecture
                self.profile_url = profile_url
                self.party_position = party_position

        # First page returns member A
        # Second page returns member A (duplicate) and member B
        mock_results = [
            [MockMember("重複太郎", "衆議院議員")],
            [
                MockMember("重複太郎", "参議院議員"),  # 同じ名前
                MockMember("別人次郎", "衆議院議員"),
            ],
        ]

        pages = [
            WebPageContent(
                url="https://example.com/1",
                html_content="<html><body><main>test1</main></body></html>",
                page_number=1,
            ),
            WebPageContent(
                url="https://example.com/2",
                html_content="<html><body><main>test2</main></body></html>",
                page_number=2,
            ),
        ]

        with patch(
            "src.party_member_extractor.baml_llm_extractor.b.ExtractPartyMembers",
            new_callable=AsyncMock,
            create=True,
        ) as mock_baml:
            mock_baml.side_effect = mock_results

            # Execute
            result = extractor.extract_from_pages(pages, "テスト党")

            # Assert - should have 2 unique members (duplicate removed)
            assert len(result.members) == 2
            names = [m.name for m in result.members]
            assert "重複太郎" in names
            assert "別人次郎" in names

    def test_url_conversion(self, extractor):
        """相対URL→絶対URLの変換テスト"""

        class MockMember:
            def __init__(
                self,
                name,
                position=None,
                electoral_district=None,
                prefecture=None,
                profile_url=None,
                party_position=None,
            ):
                self.name = name
                self.position = position
                self.electoral_district = electoral_district
                self.prefecture = prefecture
                self.profile_url = profile_url
                self.party_position = party_position

        mock_result = [
            MockMember("田中三郎", "衆議院議員", profile_url="/profile/tanaka")
        ]

        page = WebPageContent(
            url="https://example.com/members",
            html_content="<html><body><main>test</main></body></html>",
            page_number=1,
        )

        with patch(
            "src.party_member_extractor.baml_llm_extractor.b.ExtractPartyMembers",
            new_callable=AsyncMock,
            create=True,
        ) as mock_baml:
            mock_baml.return_value = mock_result

            # Execute
            result = extractor.extract_from_pages([page], "テスト党")

            # Assert - relative URL should be converted to absolute URL
            assert result.members[0].profile_url == "https://example.com/profile/tanaka"

    def test_extract_with_optional_fields(self, extractor, sample_page):
        """オプションフィールドありのテスト"""

        class MockMember:
            def __init__(
                self,
                name,
                position=None,
                electoral_district=None,
                prefecture=None,
                profile_url=None,
                party_position=None,
            ):
                self.name = name
                self.position = position
                self.electoral_district = electoral_district
                self.prefecture = prefecture
                self.profile_url = profile_url
                self.party_position = party_position

        # Member with no optional fields
        mock_result = [
            MockMember("山田太郎", None, None, None, None, None),
            MockMember("田中花子", "委員長", None, None, None, None),
        ]

        with patch(
            "src.party_member_extractor.baml_llm_extractor.b.ExtractPartyMembers",
            new_callable=AsyncMock,
            create=True,
        ) as mock_baml:
            mock_baml.return_value = mock_result

            # Execute
            result = extractor.extract_from_pages([sample_page], "委員会")

            # Assert
            assert len(result.members) == 2
            assert result.members[0].name == "山田太郎"
            assert result.members[0].position is None
            assert result.members[0].party_position is None
            assert result.members[1].name == "田中花子"
            assert result.members[1].position == "委員長"

    def test_extract_main_content(self, extractor):
        """メインコンテンツ抽出のテスト"""
        from bs4 import BeautifulSoup

        html = """
        <html>
        <body>
            <header>ヘッダー</header>
            <nav>ナビゲーション</nav>
            <main>
                <h1>議員一覧</h1>
                <div class="member">山田太郎</div>
            </main>
            <footer>フッター</footer>
        </body>
        </html>
        """

        soup = BeautifulSoup(html, "html.parser")

        # Test
        content = extractor._extract_main_content(soup)

        # Assert
        assert "議員一覧" in content
        assert "山田太郎" in content
        assert "ヘッダー" not in content  # Should be excluded
        assert "フッター" not in content  # Should be excluded

    def test_clean_text(self, extractor):
        """テキストクリーンアップのテスト"""
        text = """


        山田太郎

        衆議院議員


        東京1区

        """

        # Test
        cleaned = extractor._clean_text(text)

        # Assert
        lines = cleaned.split("\n")
        assert len(lines) == 3
        assert lines[0] == "山田太郎"
        assert lines[1] == "衆議院議員"
        assert lines[2] == "東京1区"

    def test_get_base_url(self, extractor):
        """ベースURL取得のテスト"""
        test_cases = [
            ("https://example.com/members/page1", "https://example.com/"),
            ("http://test.jp/path/to/page", "http://test.jp/"),
            ("https://sub.domain.com:8080/page", "https://sub.domain.com:8080/"),
        ]

        for url, expected in test_cases:
            assert extractor._get_base_url(url) == expected
