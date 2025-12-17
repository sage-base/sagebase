"""政党メンバーDTOのテスト

ExtractedPartyMemberDTOとPartyMemberExtractionResultDTOの
動作を検証します。
"""

from datetime import datetime

from src.domain.dtos.party_member_dto import (
    ExtractedPartyMemberDTO,
    PartyMemberExtractionResultDTO,
)


class TestExtractedPartyMemberDTO:
    """ExtractedPartyMemberDTOのテスト"""

    def test_create_with_required_fields_only(self) -> None:
        """必須フィールドのみでDTOを作成できること"""
        # Arrange & Act
        dto = ExtractedPartyMemberDTO(name="山田太郎")

        # Assert
        assert dto.name == "山田太郎"
        assert dto.position is None
        assert dto.electoral_district is None
        assert dto.prefecture is None
        assert dto.profile_url is None
        assert dto.party_position is None

    def test_create_with_all_fields(self) -> None:
        """すべてのフィールドを指定してDTOを作成できること"""
        # Arrange & Act
        dto = ExtractedPartyMemberDTO(
            name="山田太郎",
            position="衆議院議員",
            electoral_district="東京1区",
            prefecture="東京都",
            profile_url="https://example.com/profile",
            party_position="幹事長",
        )

        # Assert
        assert dto.name == "山田太郎"
        assert dto.position == "衆議院議員"
        assert dto.electoral_district == "東京1区"
        assert dto.prefecture == "東京都"
        assert dto.profile_url == "https://example.com/profile"
        assert dto.party_position == "幹事長"

    def test_dataclass_equality(self) -> None:
        """dataclassの等価性が正しく機能すること"""
        # Arrange
        dto1 = ExtractedPartyMemberDTO(
            name="山田太郎", position="衆議院議員", electoral_district="東京1区"
        )
        dto2 = ExtractedPartyMemberDTO(
            name="山田太郎", position="衆議院議員", electoral_district="東京1区"
        )
        dto3 = ExtractedPartyMemberDTO(name="佐藤花子", position="参議院議員")

        # Assert
        assert dto1 == dto2
        assert dto1 != dto3


class TestPartyMemberExtractionResultDTO:
    """PartyMemberExtractionResultDTOのテスト"""

    def test_create_with_required_fields_only(self) -> None:
        """必須フィールドのみでDTOを作成できること"""
        # Arrange
        members = [
            ExtractedPartyMemberDTO(name="山田太郎"),
            ExtractedPartyMemberDTO(name="佐藤花子"),
        ]

        # Act
        dto = PartyMemberExtractionResultDTO(
            party_id=1, url="https://example.com/members", extracted_members=members
        )

        # Assert
        assert dto.party_id == 1
        assert dto.url == "https://example.com/members"
        assert len(dto.extracted_members) == 2
        assert dto.extracted_members[0].name == "山田太郎"
        assert dto.extracted_members[1].name == "佐藤花子"
        assert dto.extraction_date is None
        assert dto.error is None

    def test_create_with_all_fields(self) -> None:
        """すべてのフィールドを指定してDTOを作成できること"""
        # Arrange
        members = [ExtractedPartyMemberDTO(name="山田太郎")]
        extraction_date = datetime(2025, 12, 13, 10, 30, 0)

        # Act
        dto = PartyMemberExtractionResultDTO(
            party_id=1,
            url="https://example.com/members",
            extracted_members=members,
            extraction_date=extraction_date,
            error=None,
        )

        # Assert
        assert dto.party_id == 1
        assert dto.url == "https://example.com/members"
        assert len(dto.extracted_members) == 1
        assert dto.extraction_date == extraction_date
        assert dto.error is None

    def test_create_with_error(self) -> None:
        """エラー情報を持つDTOを作成できること"""
        # Arrange & Act
        dto = PartyMemberExtractionResultDTO(
            party_id=1,
            url="https://example.com/members",
            extracted_members=[],
            error="Network error",
        )

        # Assert
        assert dto.party_id == 1
        assert len(dto.extracted_members) == 0
        assert dto.error == "Network error"

    def test_create_with_empty_members(self) -> None:
        """メンバーが空のDTOを作成できること"""
        # Arrange & Act
        dto = PartyMemberExtractionResultDTO(
            party_id=1, url="https://example.com/members", extracted_members=[]
        )

        # Assert
        assert dto.party_id == 1
        assert len(dto.extracted_members) == 0
        assert dto.error is None

    def test_dataclass_equality(self) -> None:
        """dataclassの等価性が正しく機能すること"""
        # Arrange
        members1 = [ExtractedPartyMemberDTO(name="山田太郎")]
        members2 = [ExtractedPartyMemberDTO(name="山田太郎")]
        members3 = [ExtractedPartyMemberDTO(name="佐藤花子")]

        dto1 = PartyMemberExtractionResultDTO(
            party_id=1, url="https://example.com/members", extracted_members=members1
        )
        dto2 = PartyMemberExtractionResultDTO(
            party_id=1, url="https://example.com/members", extracted_members=members2
        )
        dto3 = PartyMemberExtractionResultDTO(
            party_id=1, url="https://example.com/members", extracted_members=members3
        )

        # Assert
        assert dto1 == dto2
        assert dto1 != dto3
