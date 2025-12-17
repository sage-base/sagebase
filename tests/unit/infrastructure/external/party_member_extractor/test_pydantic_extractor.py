"""政党メンバー抽出器（Pydantic実装）のテスト

PydanticPartyMemberExtractorの動作を検証します。
このテストでは、LLMの呼び出しをモックして外部APIコストを発生させません。
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# baml_clientモジュールをモック
sys.modules["baml_client"] = MagicMock()
sys.modules["baml_client.async_client"] = MagicMock()

from src.domain.dtos.party_member_dto import (  # noqa: E402
    ExtractedPartyMemberDTO,
    PartyMemberExtractionResultDTO,
)
from src.infrastructure.external.party_member_extractor.pydantic_extractor import (  # noqa: E402, E501
    PydanticPartyMemberExtractor,
)


class TestPydanticPartyMemberExtractor:
    """PydanticPartyMemberExtractorのテスト"""

    @pytest.mark.asyncio
    async def test_extract_members_success(self) -> None:
        """メンバー抽出が成功すること"""
        # Arrange
        mock_llm_service = MagicMock()
        extractor = PydanticPartyMemberExtractor(llm_service=mock_llm_service)

        # モックの抽出結果
        mock_party_member_list = MagicMock()
        mock_member1 = MagicMock()
        mock_member1.name = "山田太郎"
        mock_member1.position = "衆議院議員"
        mock_member1.electoral_district = "東京1区"
        mock_member1.prefecture = "東京都"
        mock_member1.profile_url = "https://example.com/yamada"
        mock_member1.party_position = "幹事長"

        mock_party_member_list.members = [mock_member1]

        # HTMLフェッチをモック
        mock_html = "<html><body><h1>党員一覧</h1></body></html>"

        with patch.object(
            extractor, "_fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_html

            with patch.object(
                extractor, "_extract_members_with_pydantic", new_callable=AsyncMock
            ) as mock_extract:
                mock_extract.return_value = [
                    ExtractedPartyMemberDTO(
                        name="山田太郎",
                        position="衆議院議員",
                        electoral_district="東京1区",
                        prefecture="東京都",
                        profile_url="https://example.com/yamada",
                        party_position="幹事長",
                    )
                ]

                # Act
                result = await extractor.extract_members(
                    party_id=1, url="https://example.com/members"
                )

        # Assert
        assert isinstance(result, PartyMemberExtractionResultDTO)
        assert result.party_id == 1
        assert result.url == "https://example.com/members"
        assert len(result.extracted_members) == 1
        assert result.error is None

        member1 = result.extracted_members[0]
        assert member1.name == "山田太郎"
        assert member1.position == "衆議院議員"

    @pytest.mark.asyncio
    async def test_extract_members_html_fetch_error(self) -> None:
        """HTML取得エラー時にエラーメッセージを含む結果を返すこと"""
        # Arrange
        mock_llm_service = MagicMock()
        extractor = PydanticPartyMemberExtractor(llm_service=mock_llm_service)

        with patch.object(
            extractor, "_fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = None

            # Act
            result = await extractor.extract_members(
                party_id=1, url="https://example.com/members"
            )

        # Assert
        assert isinstance(result, PartyMemberExtractionResultDTO)
        assert len(result.extracted_members) == 0
        assert result.error is not None
        assert "URLからコンテンツを取得できませんでした" in result.error

    @pytest.mark.asyncio
    async def test_implements_interface(self) -> None:
        """インターフェースを正しく実装していること"""
        # Arrange
        from src.domain.interfaces.party_member_extractor_service import (
            IPartyMemberExtractorService,
        )

        mock_llm_service = MagicMock()
        extractor = PydanticPartyMemberExtractor(llm_service=mock_llm_service)

        # Assert
        assert isinstance(extractor, IPartyMemberExtractorService)
