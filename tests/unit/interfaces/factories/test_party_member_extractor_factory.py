"""政党メンバー抽出器ファクトリーのテスト

PartyMemberExtractorFactoryの動作を検証します。
"""

from unittest.mock import MagicMock, patch

from src.domain.interfaces.party_member_extractor_service import (
    IPartyMemberExtractorService,
)
from src.infrastructure.external.party_member_extractor.baml_extractor import (
    BAMLPartyMemberExtractor,
)
from src.infrastructure.external.party_member_extractor.pydantic_extractor import (
    PydanticPartyMemberExtractor,
)
from src.interfaces.factories.party_member_extractor_factory import (
    PartyMemberExtractorFactory,
)


class TestPartyMemberExtractorFactory:
    """PartyMemberExtractorFactoryのテスト"""

    def test_create_baml_extractor_by_default(self) -> None:
        """デフォルトでBAML実装を返すこと（USE_BAML_PARTY_MEMBER_EXTRACTOR=true）"""
        # Arrange
        with patch.dict("os.environ", {}, clear=False):
            # Act
            extractor = PartyMemberExtractorFactory.create()

        # Assert
        assert isinstance(extractor, IPartyMemberExtractorService)
        assert isinstance(extractor, BAMLPartyMemberExtractor)

    def test_create_pydantic_extractor_when_flag_is_false(self) -> None:
        """環境変数がfalseの場合にPydantic実装を返すこと"""
        # Arrange
        mock_llm_service = MagicMock()

        with patch.dict(
            "os.environ", {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "false"}, clear=False
        ):
            # Act
            extractor = PartyMemberExtractorFactory.create(llm_service=mock_llm_service)

        # Assert
        assert isinstance(extractor, IPartyMemberExtractorService)
        assert isinstance(extractor, PydanticPartyMemberExtractor)

    def test_create_baml_extractor_when_flag_is_true(self) -> None:
        """環境変数がtrueの場合にBAML実装を返すこと"""
        # Arrange
        with patch.dict(
            "os.environ", {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "true"}, clear=False
        ):
            # Act
            extractor = PartyMemberExtractorFactory.create()

        # Assert
        assert isinstance(extractor, IPartyMemberExtractorService)
        assert isinstance(extractor, BAMLPartyMemberExtractor)

    def test_create_returns_interface_type(self) -> None:
        """ファクトリーが常にインターフェース型を返すこと"""
        # Arrange
        mock_llm_service = MagicMock()

        # Act - Pydantic
        pydantic_extractor = PartyMemberExtractorFactory.create(
            llm_service=mock_llm_service
        )

        # Act - BAML
        with patch.dict(
            "os.environ", {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "true"}, clear=False
        ):
            baml_extractor = PartyMemberExtractorFactory.create()

        # Assert
        assert isinstance(pydantic_extractor, IPartyMemberExtractorService)
        assert isinstance(baml_extractor, IPartyMemberExtractorService)
