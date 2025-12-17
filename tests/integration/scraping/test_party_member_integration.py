"""Integration tests for party member scraping"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.party_member_extractor.factory import PartyMemberExtractorFactory
from src.party_member_extractor.models import (
    PartyMemberInfo,
    PartyMemberList,
    WebPageContent,
)


class TestPartyMemberIntegration:
    """統合テストクラス"""

    @pytest.mark.asyncio
    async def test_full_scraping_flow(self):
        """完全なスクレイピングフローのテスト"""
        # Force Pydantic implementation for this test
        import os

        os.environ["USE_BAML_PARTY_MEMBER_EXTRACTOR"] = "false"

        # HTMLフェッチャーのモック
        mock_pages = [
            WebPageContent(
                url="https://example.com/members/page1",
                html_content="""
                <html><body>
                    <main>
                        <div class="member">
                            <h3>統合太郎</h3>
                            <p>衆議院議員</p>
                            <p>東京1区</p>
                        </div>
                    </main>
                </body></html>
                """,
                page_number=1,
            )
        ]

        # LLMのモック結果
        mock_llm_result = PartyMemberList(
            members=[
                PartyMemberInfo(
                    name="統合太郎",
                    position="衆議院議員",
                    electoral_district="東京1区",
                    prefecture="東京都",
                )
            ],
            total_count=1,
            party_name="統合テスト党",
        )

        # モックの設定
        with patch(
            "src.party_member_extractor.html_fetcher.PartyMemberPageFetcher"
        ) as mock_fetcher:
            mock_fetcher_instance = AsyncMock()
            mock_fetcher_instance.fetch_all_pages.return_value = mock_pages
            mock_fetcher.return_value.__aenter__.return_value = mock_fetcher_instance

            with patch(
                "src.party_member_extractor.extractor.LLMServiceFactory"
            ) as mock_factory:
                mock_service = Mock()
                mock_extraction_llm = Mock()
                mock_extraction_llm.invoke.return_value = mock_llm_result
                mock_service.get_structured_llm.return_value = mock_extraction_llm
                mock_service.invoke_prompt.return_value = mock_llm_result
                mock_factory.return_value.create_advanced.return_value = mock_service

                # エクストラクター作成
                extractor = PartyMemberExtractorFactory.create()

                # フェッチとエクストラクト実行
                # Note: We're mocking PartyMemberPageFetcher above, so we use the mock
                result = extractor.extract_from_pages(mock_pages, "統合テスト党")

                # アサーション
                assert len(result.members) == 1
                assert result.members[0].name == "統合太郎"
                assert result.members[0].position == "衆議院議員"
                assert result.members[0].prefecture == "東京都"

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """エラーリカバリーのテスト"""
        # Force Pydantic implementation for this test
        import os

        os.environ["USE_BAML_PARTY_MEMBER_EXTRACTOR"] = "false"

        # 一部のページでエラーが発生
        mock_pages = [
            WebPageContent(
                url="https://example.com/page1",
                html_content="<html><body><main>Page 1 content</main></body></html>",
                page_number=1,
            ),
            WebPageContent(
                url="https://example.com/page2",
                html_content="<html><body><main>Page 2 content</main></body></html>",
                page_number=2,
            ),
            WebPageContent(
                url="https://example.com/page3",
                html_content="<html><body><main>Page 3 content</main></body></html>",
                page_number=3,
            ),
        ]

        # LLMのモック（2ページ目でエラー）
        with patch(
            "src.party_member_extractor.extractor.LLMServiceFactory"
        ) as mock_factory:
            mock_service = Mock()
            mock_extraction_llm = Mock()

            # Setup mock service attributes
            mock_service.temperature = 0.1
            mock_service.model_name = "test-model"
            mock_service.get_structured_llm.return_value = mock_extraction_llm

            # Mock get_prompt
            mock_prompt = Mock()
            mock_prompt.format.return_value = "Test prompt"
            mock_service.get_prompt.return_value = mock_prompt

            # Setup extraction_llm.invoke to return results with error on 2nd page
            mock_extraction_llm.invoke.side_effect = [
                PartyMemberList(
                    members=[PartyMemberInfo(name="成功太郎", position="衆議院議員")],
                    total_count=1,
                ),
                Exception("LLM Error"),  # エラー
                PartyMemberList(
                    members=[PartyMemberInfo(name="成功花子", position="参議院議員")],
                    total_count=1,
                ),
            ]
            mock_factory.return_value.create_advanced.return_value = mock_service

            extractor = PartyMemberExtractorFactory.create()
            result = extractor.extract_from_pages(mock_pages, "エラーテスト党")

            # アサーション（エラーページをスキップして続行）
            assert len(result.members) == 2
            assert result.members[0].name == "成功太郎"
            assert result.members[1].name == "成功花子"
