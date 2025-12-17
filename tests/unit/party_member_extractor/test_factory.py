"""Tests for party member extractor factory"""

from unittest.mock import Mock, patch

from src.party_member_extractor.factory import PartyMemberExtractorFactory


class TestPartyMemberExtractorFactory:
    """Test cases for PartyMemberExtractorFactory"""

    def test_create_pydantic_extractor_default(self):
        """Pydantic実装の作成テスト（デフォルト）"""
        # USE_BAML_PARTY_MEMBER_EXTRACTORが設定されていない場合、
        # またはfalseの場合、Pydantic実装を返す

        with patch.dict(
            "os.environ",
            {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "false", "GOOGLE_API_KEY": "test-key"},
            clear=True,
        ):
            # Mock LLMServiceFactory to avoid needing real API key
            with patch("src.party_member_extractor.extractor.LLMServiceFactory"):
                extractor = PartyMemberExtractorFactory.create()

                # Assert - should be Pydantic implementation
                assert extractor.__class__.__name__ == "PartyMemberExtractor"

    def test_create_pydantic_extractor_explicit(self):
        """Pydantic実装の作成テスト（明示的にfalse指定）"""
        with patch.dict(
            "os.environ",
            {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "false", "GOOGLE_API_KEY": "test-key"},
        ):
            # Mock LLMServiceFactory to avoid needing real API key
            with patch("src.party_member_extractor.extractor.LLMServiceFactory"):
                extractor = PartyMemberExtractorFactory.create()

                # Assert
                assert extractor.__class__.__name__ == "PartyMemberExtractor"

    def test_create_baml_extractor(self):
        """BAML実装の作成テスト"""
        with patch.dict("os.environ", {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "true"}):
            extractor = PartyMemberExtractorFactory.create()

            # Assert - should be BAML implementation
            assert extractor.__class__.__name__ == "BAMLPartyMemberExtractor"

    def test_create_baml_extractor_uppercase(self):
        """BAML実装の作成テスト（大文字TRUE）"""
        with patch.dict("os.environ", {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "TRUE"}):
            extractor = PartyMemberExtractorFactory.create()

            # Assert
            assert extractor.__class__.__name__ == "BAMLPartyMemberExtractor"

    def test_create_with_parameters(self):
        """パラメータ付き作成テスト"""
        mock_llm_service = Mock()
        mock_llm_service.get_structured_llm.return_value = Mock()
        mock_llm_service.get_prompt.return_value = Mock()
        party_id = 123
        mock_proc_logger = Mock()

        with patch.dict(
            "os.environ",
            {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "false", "GOOGLE_API_KEY": "test-key"},
        ):
            extractor = PartyMemberExtractorFactory.create(
                llm_service=mock_llm_service,
                party_id=party_id,
                proc_logger=mock_proc_logger,
            )

            # Assert
            assert extractor.__class__.__name__ == "PartyMemberExtractor"
            # Verify parameters were passed correctly
            assert extractor.party_id == party_id

    def test_create_baml_with_parameters(self):
        """BAML実装のパラメータ付き作成テスト"""
        mock_llm_service = Mock()
        party_id = 456
        mock_proc_logger = Mock()

        with patch.dict("os.environ", {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "true"}):
            extractor = PartyMemberExtractorFactory.create(
                llm_service=mock_llm_service,
                party_id=party_id,
                proc_logger=mock_proc_logger,
            )

            # Assert
            assert extractor.__class__.__name__ == "BAMLPartyMemberExtractor"
            # Verify parameters were passed correctly
            assert extractor.party_id == party_id

    def test_factory_returns_consistent_interface(self):
        """Factoryが一貫したインターフェースを返すテスト"""
        # Both implementations should have the same interface
        with patch.dict(
            "os.environ",
            {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "false", "GOOGLE_API_KEY": "test-key"},
        ):
            # Mock LLMServiceFactory to avoid needing real API key
            with patch("src.party_member_extractor.extractor.LLMServiceFactory"):
                pydantic_extractor = PartyMemberExtractorFactory.create()

        with patch.dict("os.environ", {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "true"}):
            baml_extractor = PartyMemberExtractorFactory.create()

        # Assert - both should have the same public methods
        assert hasattr(pydantic_extractor, "extract_from_pages")
        assert hasattr(baml_extractor, "extract_from_pages")
