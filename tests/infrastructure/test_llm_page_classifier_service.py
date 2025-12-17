"""Tests for LLM page classifier service."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.domain.value_objects.page_classification import PageClassification, PageType
from src.infrastructure.external.llm_page_classifier_service import (
    LLMPageClassifierService,
)

# TODO: Update tests for BAML implementation (Issue #816)
# These tests need to be updated to mock BAML functions instead of ILLMService
pytestmark = pytest.mark.skip(
    reason="Tests need to be updated for BAML implementation (Issue #816)"
)


class TestLLMPageClassifierService:
    """Test LLM-based page classification service."""

    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service."""
        service = Mock()
        service.get_prompt = Mock()
        service.llm = Mock()
        return service

    @pytest.fixture
    def classifier_service(self, mock_llm_service):
        """Create classifier service with mocked LLM."""
        return LLMPageClassifierService(mock_llm_service)

    @pytest.mark.asyncio
    async def test_classify_index_page(self, classifier_service, mock_llm_service):
        """Test classifying an index page."""
        # Setup mock response
        mock_prompt = Mock()
        mock_prompt.format = Mock(return_value="formatted prompt")
        mock_llm_service.get_prompt.return_value = mock_prompt

        mock_response = Mock()
        mock_response.content = """```json
        {
            "page_type": "index_page",
            "confidence": 0.9,
            "reason": "Page contains many prefecture links",
            "has_child_links": true,
            "has_member_info": false
        }
        ```"""
        mock_llm_service.llm.ainvoke = AsyncMock(return_value=mock_response)

        # Execute
        result = await classifier_service.classify_page(
            html_content="<html>...</html>",
            current_url="https://example.com/members",
            party_name="Test Party",
        )

        # Verify
        assert isinstance(result, PageClassification)
        assert result.page_type == PageType.INDEX_PAGE
        assert result.confidence == 0.9
        assert result.has_child_links is True
        assert result.has_member_info is False

    @pytest.mark.asyncio
    async def test_classify_member_list_page(
        self, classifier_service, mock_llm_service
    ):
        """Test classifying a member list page."""
        # Setup mock response
        mock_prompt = Mock()
        mock_prompt.format = Mock(return_value="formatted prompt")
        mock_llm_service.get_prompt.return_value = mock_prompt

        mock_response = Mock()
        mock_response.content = """
        {
            "page_type": "member_list_page",
            "confidence": 0.95,
            "reason": "Contains multiple member profiles with names and positions",
            "has_child_links": false,
            "has_member_info": true
        }
        """
        mock_llm_service.llm.ainvoke = AsyncMock(return_value=mock_response)

        # Execute
        result = await classifier_service.classify_page(
            html_content="<html>...</html>",
            current_url="https://example.com/members/list",
            party_name="Test Party",
        )

        # Verify
        assert result.page_type == PageType.MEMBER_LIST_PAGE
        assert result.confidence == 0.95
        assert result.has_member_info is True

    @pytest.mark.asyncio
    async def test_classify_other_page(self, classifier_service, mock_llm_service):
        """Test classifying an other type page."""
        # Setup mock response
        mock_prompt = Mock()
        mock_prompt.format = Mock(return_value="formatted prompt")
        mock_llm_service.get_prompt.return_value = mock_prompt

        mock_response = Mock()
        mock_response.content = (
            '{"page_type": "other", "confidence": 0.8, "reason": "News page", '
            '"has_child_links": false, "has_member_info": false}'
        )
        mock_llm_service.llm.ainvoke = AsyncMock(return_value=mock_response)

        # Execute
        result = await classifier_service.classify_page(
            html_content="<html>...</html>",
            current_url="https://example.com/news",
            party_name="Test Party",
        )

        # Verify
        assert result.page_type == PageType.OTHER
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_empty_html_raises_error(self, classifier_service):
        """Test that empty HTML content raises ValueError."""
        with pytest.raises(ValueError, match="HTML content cannot be empty"):
            await classifier_service.classify_page(
                html_content="",
                current_url="https://example.com",
            )

    @pytest.mark.asyncio
    async def test_empty_url_raises_error(self, classifier_service):
        """Test that empty URL raises ValueError."""
        with pytest.raises(ValueError, match="Current URL cannot be empty"):
            await classifier_service.classify_page(
                html_content="<html>...</html>",
                current_url="",
            )

    @pytest.mark.asyncio
    async def test_invalid_page_type_defaults_to_other(
        self, classifier_service, mock_llm_service
    ):
        """Test that invalid page_type defaults to OTHER."""
        # Setup mock response with invalid page_type
        mock_prompt = Mock()
        mock_prompt.format = Mock(return_value="formatted prompt")
        mock_llm_service.get_prompt.return_value = mock_prompt

        mock_response = Mock()
        mock_response.content = (
            '{"page_type": "invalid_type", "confidence": 0.5, "reason": "Test", '
            '"has_child_links": false, "has_member_info": false}'
        )
        mock_llm_service.llm.ainvoke = AsyncMock(return_value=mock_response)

        # Execute
        result = await classifier_service.classify_page(
            html_content="<html>...</html>",
            current_url="https://example.com",
        )

        # Verify - should default to OTHER
        assert result.page_type == PageType.OTHER

    @pytest.mark.asyncio
    async def test_json_parse_error_returns_fallback(
        self, classifier_service, mock_llm_service
    ):
        """Test that JSON parse errors return fallback classification."""
        # Setup mock response with invalid JSON
        mock_prompt = Mock()
        mock_prompt.format = Mock(return_value="formatted prompt")
        mock_llm_service.get_prompt.return_value = mock_prompt

        mock_response = Mock()
        mock_response.content = "This is not valid JSON"
        mock_llm_service.llm.ainvoke = AsyncMock(return_value=mock_response)

        # Execute
        result = await classifier_service.classify_page(
            html_content="<html>...</html>",
            current_url="https://example.com",
        )

        # Verify - should return fallback
        assert result.page_type == PageType.OTHER
        assert result.confidence == 0.3
        assert "Failed to parse" in result.reason

    @pytest.mark.asyncio
    async def test_llm_error_returns_fallback(
        self, classifier_service, mock_llm_service
    ):
        """Test that LLM errors return fallback classification."""
        # Setup mock to raise error
        mock_prompt = Mock()
        mock_prompt.format = Mock(return_value="formatted prompt")
        mock_llm_service.get_prompt.return_value = mock_prompt

        mock_llm_service.llm.ainvoke = AsyncMock(side_effect=Exception("LLM API error"))

        # Execute
        result = await classifier_service.classify_page(
            html_content="<html>...</html>",
            current_url="https://example.com",
        )

        # Verify - should return fallback
        assert result.page_type == PageType.OTHER
        assert result.confidence == 0.0
        assert "Failed to classify" in result.reason

    @pytest.mark.asyncio
    async def test_html_truncation(self, classifier_service, mock_llm_service):
        """Test that HTML content is truncated to 3000 characters."""
        # Setup mock
        mock_prompt = Mock()
        mock_prompt.format = Mock(return_value="formatted prompt")
        mock_llm_service.get_prompt.return_value = mock_prompt

        mock_response = Mock()
        mock_response.content = (
            '{"page_type": "other", "confidence": 0.5, "reason": "Test", '
            '"has_child_links": false, "has_member_info": false}'
        )
        mock_llm_service.llm.ainvoke = AsyncMock(return_value=mock_response)

        # Execute with long HTML
        long_html = "<html>" + "x" * 5000 + "</html>"
        await classifier_service.classify_page(
            html_content=long_html,
            current_url="https://example.com",
        )

        # Verify that format was called with truncated HTML
        format_call = mock_prompt.format.call_args
        html_excerpt = format_call[1]["html_excerpt"]
        assert len(html_excerpt) == 3000
