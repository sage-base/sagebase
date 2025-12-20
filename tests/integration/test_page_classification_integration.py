"""Integration tests for page classification workflow.

These tests verify the end-to-end flow from HTML content through
classification to navigation decision.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.domain.value_objects.page_classification import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    PageClassification,
    PageType,
)
from src.infrastructure.external.langgraph_nodes.decision_node import (
    should_explore_children,
)
from src.infrastructure.external.llm_page_classifier_service import (
    MAX_HTML_EXCERPT_LENGTH,
    LLMPageClassifierService,
)

# TODO: Update tests for BAML implementation (Issue #816)
# Integration tests need BAML function mocks instead of ILLMService
pytestmark = pytest.mark.skip(
    reason="Tests need to be updated for BAML implementation (Issue #816)"
)


class TestPageClassificationIntegration:
    """Integration tests for page classification workflow."""

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
    async def test_index_page_classification_to_exploration(
        self, classifier_service, mock_llm_service
    ):
        """Test complete flow: index page classification → explore children decision.

        This integration test verifies:
        1. HTML is classified as INDEX_PAGE with high confidence
        2. Decision node correctly decides to explore children
        3. Constants are used consistently throughout the flow
        """
        # Setup: Mock LLM to return INDEX_PAGE classification
        mock_prompt = Mock()
        mock_prompt.format = Mock(return_value="formatted prompt")
        mock_llm_service.get_prompt.return_value = mock_prompt

        mock_response = Mock()
        mock_response.content = f"""{{
            "page_type": "index_page",
            "confidence": {DEFAULT_CONFIDENCE_THRESHOLD + 0.1},
            "reason": "Contains prefecture links",
            "has_child_links": true,
            "has_member_info": false
        }}""".replace("{{", "{").replace("}}", "}")
        mock_llm_service.llm.ainvoke = AsyncMock(return_value=mock_response)

        # Execute: Classify page
        html_content = "<html><body><a href='/tokyo'>Tokyo</a></body></html>"
        classification = await classifier_service.classify_page(
            html_content=html_content,
            current_url="https://example.com/regions",
            party_name="Test Party",
        )

        # Verify: Classification is correct
        assert classification.page_type == PageType.INDEX_PAGE
        assert classification.confidence >= DEFAULT_CONFIDENCE_THRESHOLD
        assert classification.should_explore_children(max_depth_reached=False) is True

        # Execute: Decision node
        state = {
            "classification": {
                "page_type": classification.page_type.value,
                "confidence": classification.confidence,
            },
            "depth": 1,
            "max_depth": 3,
            "pending_urls": [],
        }
        decision = should_explore_children(state)  # type: ignore[arg-type]

        # Verify: Decision is to explore children
        assert decision == "explore_children"

    @pytest.mark.asyncio
    async def test_member_list_page_classification_to_extraction(
        self, classifier_service, mock_llm_service
    ):
        """Test complete flow: member list page → extract members decision.

        This integration test verifies:
        1. HTML is classified as MEMBER_LIST_PAGE with high confidence
        2. Decision node correctly decides to extract members
        3. Member extraction decision is consistent with domain logic
        """
        # Setup: Mock LLM to return MEMBER_LIST_PAGE classification
        mock_prompt = Mock()
        mock_prompt.format = Mock(return_value="formatted prompt")
        mock_llm_service.get_prompt.return_value = mock_prompt

        mock_response = Mock()
        mock_response.content = """{
            "page_type": "member_list_page",
            "confidence": 0.95,
            "reason": "Contains multiple member profiles",
            "has_child_links": false,
            "has_member_info": true
        }"""
        mock_llm_service.llm.ainvoke = AsyncMock(return_value=mock_response)

        # Execute: Classify page
        html_content = (
            "<html><body>"
            "<div class='member'>Yamada Taro</div>"
            "<div class='member'>Suzuki Hanako</div>"
            "</body></html>"
        )
        classification = await classifier_service.classify_page(
            html_content=html_content,
            current_url="https://example.com/members/tokyo",
            party_name="Test Party",
        )

        # Verify: Classification is correct
        assert classification.page_type == PageType.MEMBER_LIST_PAGE
        assert classification.confidence >= DEFAULT_CONFIDENCE_THRESHOLD
        assert classification.should_extract_members() is True
        assert classification.should_explore_children(max_depth_reached=False) is False

        # Execute: Decision node
        state = {
            "classification": {
                "page_type": classification.page_type.value,
                "confidence": classification.confidence,
            },
            "depth": 2,
            "max_depth": 3,
            "pending_urls": [],
        }
        decision = should_explore_children(state)  # type: ignore[arg-type]

        # Verify: Decision is to extract members
        assert decision == "extract_members"

    @pytest.mark.asyncio
    async def test_low_confidence_classification_skips_page(
        self, classifier_service, mock_llm_service
    ):
        """Test complete flow: low confidence classification → skip decision.

        This integration test verifies:
        1. HTML is classified but with low confidence
        2. Domain logic correctly rejects low confidence
        3. Decision node correctly decides to skip
        4. Threshold constant is used consistently
        """
        # Setup: Mock LLM to return low confidence classification
        mock_prompt = Mock()
        mock_prompt.format = Mock(return_value="formatted prompt")
        mock_llm_service.get_prompt.return_value = mock_prompt

        mock_response = Mock()
        mock_response.content = f"""{{
            "page_type": "index_page",
            "confidence": {DEFAULT_CONFIDENCE_THRESHOLD - 0.1},
            "reason": "Uncertain classification",
            "has_child_links": true,
            "has_member_info": false
        }}""".replace("{{", "{").replace("}}", "}")
        mock_llm_service.llm.ainvoke = AsyncMock(return_value=mock_response)

        # Execute: Classify page
        html_content = "<html><body>Ambiguous content</body></html>"
        classification = await classifier_service.classify_page(
            html_content=html_content,
            current_url="https://example.com/page",
            party_name="Test Party",
        )

        # Verify: Classification has low confidence
        assert classification.confidence < DEFAULT_CONFIDENCE_THRESHOLD
        assert classification.is_confident() is False
        assert classification.should_explore_children(max_depth_reached=False) is False

        # Execute: Decision node
        state = {
            "classification": {
                "page_type": classification.page_type.value,
                "confidence": classification.confidence,
            },
            "depth": 1,
            "max_depth": 3,
            "pending_urls": [("https://example.com/next", 1)],
        }
        decision = should_explore_children(state)  # type: ignore[arg-type]

        # Verify: Decision is to continue (skip this page)
        assert decision == "continue"

    @pytest.mark.asyncio
    async def test_html_truncation_integration(
        self, classifier_service, mock_llm_service
    ):
        """Test that HTML truncation constant is applied correctly.

        This integration test verifies:
        1. Long HTML is truncated using MAX_HTML_EXCERPT_LENGTH
        2. Classification still works with truncated content
        3. Truncation limit is respected in the prompt
        """
        # Setup: Mock LLM
        mock_prompt = Mock()
        mock_prompt.format = Mock(return_value="formatted prompt")
        mock_llm_service.get_prompt.return_value = mock_prompt

        mock_response = Mock()
        mock_response.content = """{
            "page_type": "other",
            "confidence": 0.8,
            "reason": "Generic page",
            "has_child_links": false,
            "has_member_info": false
        }"""
        mock_llm_service.llm.ainvoke = AsyncMock(return_value=mock_response)

        # Execute: Classify page with very long HTML
        long_html = "<html><body>" + "x" * 10000 + "</body></html>"
        classification = await classifier_service.classify_page(
            html_content=long_html,
            current_url="https://example.com/page",
        )

        # Verify: Classification succeeded
        assert isinstance(classification, PageClassification)

        # Verify: HTML was truncated in the prompt
        format_call = mock_prompt.format.call_args
        html_excerpt = format_call[1]["html_excerpt"]
        assert len(html_excerpt) == MAX_HTML_EXCERPT_LENGTH
        assert html_excerpt == long_html[:MAX_HTML_EXCERPT_LENGTH]

    @pytest.mark.asyncio
    async def test_max_depth_prevents_exploration(
        self, classifier_service, mock_llm_service
    ):
        """Test that max depth enforcement works end-to-end.

        This integration test verifies:
        1. Even with confident INDEX_PAGE classification
        2. Max depth enforcement prevents further exploration
        3. Domain and infrastructure layers coordinate correctly
        """
        # Setup: Mock LLM to return INDEX_PAGE with high confidence
        mock_prompt = Mock()
        mock_prompt.format = Mock(return_value="formatted prompt")
        mock_llm_service.get_prompt.return_value = mock_prompt

        mock_response = Mock()
        mock_response.content = """{
            "page_type": "index_page",
            "confidence": 0.95,
            "reason": "Clear index page",
            "has_child_links": true,
            "has_member_info": false
        }"""
        mock_llm_service.llm.ainvoke = AsyncMock(return_value=mock_response)

        # Execute: Classify page
        classification = await classifier_service.classify_page(
            html_content="<html>...</html>",
            current_url="https://example.com/deep/page",
        )

        # Verify: Classification would normally allow exploration
        assert classification.page_type == PageType.INDEX_PAGE
        assert classification.is_confident()

        # But: Max depth is reached
        assert classification.should_explore_children(max_depth_reached=True) is False

        # Execute: Decision node at max depth
        state = {
            "classification": {
                "page_type": classification.page_type.value,
                "confidence": classification.confidence,
            },
            "depth": 3,
            "max_depth": 3,
            "pending_urls": [("https://example.com/next", 3)],
        }
        decision = should_explore_children(state)  # type: ignore[arg-type]

        # Verify: Decision is to continue (not explore deeper)
        assert decision == "continue"
