"""政党メンバー抽出サービスインターフェースのテスト

IPartyMemberExtractorServiceインターフェースの動作を検証します。
このテストでは、インターフェースの契約が正しく定義されていることを確認します。
"""

from datetime import datetime

import pytest

from src.domain.dtos.party_member_dto import (
    ExtractedPartyMemberDTO,
    PartyMemberExtractionResultDTO,
)
from src.domain.interfaces.party_member_extractor_service import (
    IPartyMemberExtractorService,
)


class MockPartyMemberExtractorService(IPartyMemberExtractorService):
    """テスト用のモック実装"""

    async def extract_members(
        self, party_id: int, url: str
    ) -> PartyMemberExtractionResultDTO:
        """モック実装: 固定のメンバーを返す"""
        members = [
            ExtractedPartyMemberDTO(name="山田太郎", position="衆議院議員"),
            ExtractedPartyMemberDTO(name="佐藤花子", position="参議院議員"),
        ]
        return PartyMemberExtractionResultDTO(
            party_id=party_id,
            url=url,
            extracted_members=members,
            extraction_date=datetime(2025, 12, 13, 10, 30, 0),
        )


class TestIPartyMemberExtractorService:
    """IPartyMemberExtractorServiceのテスト"""

    @pytest.mark.asyncio
    async def test_interface_can_be_implemented(self) -> None:
        """インターフェースを実装できること"""
        # Arrange
        service = MockPartyMemberExtractorService()

        # Act
        result = await service.extract_members(party_id=1, url="https://example.com")

        # Assert
        assert isinstance(result, PartyMemberExtractionResultDTO)
        assert result.party_id == 1
        assert result.url == "https://example.com"
        assert len(result.extracted_members) == 2

    @pytest.mark.asyncio
    async def test_interface_returns_correct_dto_type(self) -> None:
        """インターフェースが正しいDTO型を返すこと"""
        # Arrange
        service = MockPartyMemberExtractorService()

        # Act
        result = await service.extract_members(party_id=1, url="https://example.com")

        # Assert
        assert isinstance(result, PartyMemberExtractionResultDTO)
        assert all(
            isinstance(member, ExtractedPartyMemberDTO)
            for member in result.extracted_members
        )

    @pytest.mark.asyncio
    async def test_interface_method_is_async(self) -> None:
        """インターフェースのメソッドが非同期であること"""
        # Arrange
        service = MockPartyMemberExtractorService()

        # Act & Assert
        # このメソッドがawait可能であることを確認
        result = await service.extract_members(party_id=1, url="https://example.com")
        assert result is not None

    def test_interface_is_abstract(self) -> None:
        """インターフェースが抽象クラスであること"""
        # Assert
        with pytest.raises(TypeError):
            # 抽象クラスを直接インスタンス化できないことを確認
            IPartyMemberExtractorService()  # type: ignore
