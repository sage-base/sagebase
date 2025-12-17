"""Tests for member extractor LangGraph tool."""

from typing import Any
from unittest.mock import patch

import pytest

from src.domain.services.interfaces.llm_service import ILLMService
from src.infrastructure.external.langgraph_tools.member_extractor_tool import (
    create_member_extractor_tools,
)
from src.party_member_extractor.models import PartyMemberInfo, PartyMemberList


class MockLLMService(ILLMService):
    """Mock LLM service for testing."""

    model_name: str = "mock-model"
    temperature: float = 0.0

    def __init__(self) -> None:
        self.prompt_templates = {
            "party_member_extract": """
            Extract party members from the following content:
            Party: {party_name}
            Base URL: {base_url}
            Content: {content}
            """
        }

    async def set_history_repository(self, repository: Any) -> None:
        """Mock set history repository."""
        pass

    async def get_processing_history(
        self, reference_type: str | None = None, reference_id: int | None = None
    ) -> list[Any]:
        """Mock get processing history."""
        return []

    async def match_speaker_to_politician(self, context: Any) -> Any:
        """Mock match speaker to politician."""
        return None

    async def extract_speeches_from_text(self, text: str) -> list[dict[str, str]]:
        """Mock extract speeches."""
        return []

    async def extract_party_members(self, html_content: str, party_id: int) -> Any:
        """Mock extract party members."""
        return None

    async def match_conference_member(
        self, member_name: str, party_name: str | None, candidates: list[Any]
    ) -> Any:
        """Mock match conference member."""
        return None

    async def invoke_structured_output_async(
        self,
        prompt_template: str,
        input_data: dict[str, Any],
        schema: Any = None,
        output_model: Any = None,
    ) -> Any:
        """Mock invoke structured output async."""
        # Return mock data based on party name
        if input_data.get("party_name") == "Example Party":
            return PartyMemberList(
                members=[
                    PartyMemberInfo(
                        name="山田太郎",
                        position="衆議院議員",
                        electoral_district="東京1区",
                        prefecture="東京都",
                        profile_url="https://example.com/yamada",
                        party_position="代表",
                    ),
                    PartyMemberInfo(
                        name="田中花子",
                        position="参議院議員",
                        electoral_district="比例代表",
                        prefecture="神奈川県",
                        profile_url="https://example.com/tanaka",
                        party_position=None,
                    ),
                ],
                total_count=2,
                party_name="Example Party",
            )
        return PartyMemberList(members=[], total_count=0, party_name="Unknown")

    def get_prompt(self, prompt_name: str):
        """Return mock prompt template."""

        class MockPrompt:
            def __init__(self, template: str):
                self.template = template

            def format(self, **kwargs: Any) -> str:
                return self.template.format(**kwargs)

        return MockPrompt(self.prompt_templates[prompt_name])

    def get_structured_llm(self, schema: Any):
        """Return mock structured LLM."""

        class MockStructuredLLM:
            def invoke(self, prompt: str):
                # Return mock data based on the prompt
                if "Example Party" in prompt:
                    return PartyMemberList(
                        members=[
                            PartyMemberInfo(
                                name="山田太郎",
                                position="衆議院議員",
                                electoral_district="東京1区",
                                prefecture="東京都",
                                profile_url="https://example.com/yamada",
                                party_position="代表",
                            ),
                            PartyMemberInfo(
                                name="田中花子",
                                position="参議院議員",
                                electoral_district="比例代表",
                                prefecture="神奈川県",
                                profile_url="https://example.com/tanaka",
                                party_position=None,
                            ),
                        ],
                        total_count=2,
                        party_name="Example Party",
                    )
                return PartyMemberList(members=[], total_count=0, party_name="Unknown")

        return MockStructuredLLM()

    def invoke_with_retry(self, chain: Any, inputs: dict[str, Any]) -> Any:
        """Mock invoke with retry."""
        return "Mock response"

    def invoke_llm(self, messages: list[dict[str, str]]) -> str:
        """Mock invoke LLM."""
        return "Mock response"


@pytest.fixture
def mock_llm_service() -> MockLLMService:
    """Create mock LLM service."""
    return MockLLMService()


@pytest.fixture
def sample_html():
    """Create sample HTML for testing."""
    return """
    <html>
        <head><title>党員リスト</title></head>
        <body>
            <main>
                <h1>Example Party 議員一覧</h1>
                <div class="member">
                    <h2>山田太郎</h2>
                    <p>衆議院議員（東京1区）</p>
                    <p>代表</p>
                    <a href="/yamada">プロフィール</a>
                </div>
                <div class="member">
                    <h2>田中花子</h2>
                    <p>参議院議員（比例代表）</p>
                    <a href="/tanaka">プロフィール</a>
                </div>
            </main>
        </body>
    </html>
    """


@pytest.mark.asyncio
async def test_extract_members_from_page_success(
    mock_llm_service: MockLLMService, sample_html: str
) -> None:
    """Test successful member extraction."""
    # Force Pydantic implementation to use mock LLM service
    with patch.dict("os.environ", {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "false"}):
        # Create tools
        tools = create_member_extractor_tools(llm_service=mock_llm_service)
        extract_tool = tools[0]

        # Execute tool
        result = await extract_tool.ainvoke(
            {
                "url": "https://example.com/members",
                "html_content": sample_html,
                "party_name": "Example Party",
            }
        )

        # Verify result
        assert result["success"] is True
        assert result["count"] == 2
        assert result["party_name"] == "Example Party"
        assert len(result["members"]) == 2

        # Verify first member
        member1 = result["members"][0]
        assert member1["name"] == "山田太郎"
        assert member1["position"] == "衆議院議員"
        assert member1["electoral_district"] == "東京1区"
        assert member1["prefecture"] == "東京都"
        assert member1["profile_url"] == "https://example.com/yamada"
        assert member1["party_position"] == "代表"

        # Verify second member
        member2 = result["members"][1]
        assert member2["name"] == "田中花子"
        assert member2["position"] == "参議院議員"
        assert member2["electoral_district"] == "比例代表"
        assert member2["prefecture"] == "神奈川県"
        assert member2["profile_url"] == "https://example.com/tanaka"
        assert member2["party_position"] is None


@pytest.mark.asyncio
async def test_extract_members_from_page_no_members(
    mock_llm_service: MockLLMService,
) -> None:
    """Test extraction when no members are found."""
    # Force Pydantic implementation to use mock LLM service
    with patch.dict("os.environ", {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "false"}):
        # Create tools
        tools = create_member_extractor_tools(llm_service=mock_llm_service)
        extract_tool = tools[0]

        # Execute tool with empty HTML
        result = await extract_tool.ainvoke(
            {
                "url": "https://example.com/empty",
                "html_content": "<html><body></body></html>",
                "party_name": "Unknown Party",
            }
        )

        # Verify result
        # Empty member list is still considered successful extraction
        assert result["success"] is True
        assert result["count"] == 0
        assert result["party_name"] == "Unknown Party"
        assert len(result["members"]) == 0


@pytest.mark.asyncio
async def test_extract_members_from_page_error_handling(
    mock_llm_service: MockLLMService,
) -> None:
    """Test error handling when extractor's internal LLM raises an error.

    When the extractor's internal _extract_from_single_page catches an error,
    it returns None rather than raising. The tool treats this as "no members found"
    rather than an error. This test verifies that behavior.
    """

    # Create a mock LLM service that raises an error
    class ErrorLLMService(MockLLMService):
        def get_structured_llm(self, schema: Any):  # type: ignore[reportIncompatibleMethodOverride]
            class ErrorLLM:
                def invoke(self, prompt: str):
                    raise ValueError("Test error")

            return ErrorLLM()

    # Force Pydantic implementation to use mock LLM service
    with patch.dict("os.environ", {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "false"}):
        # Create tools with error-raising service
        tools = create_member_extractor_tools(llm_service=ErrorLLMService())
        extract_tool = tools[0]

        # Execute tool
        result = await extract_tool.ainvoke(
            {
                "url": "https://example.com/members",
                "html_content": "<html><body>Test</body></html>",
                "party_name": "Test Party",
            }
        )

        # Verify that internal errors are handled gracefully
        # (extractor catches the error and returns empty list,
        # which is still success=True)
        # The error is logged but doesn't propagate to the tool layer
        assert result["success"] is True
        assert result["count"] == 0
        assert result["party_name"] == "Test Party"


@pytest.mark.asyncio
async def test_create_member_extractor_tools_returns_list() -> None:
    """Test that create_member_extractor_tools returns a list of tools."""
    tools = create_member_extractor_tools()
    assert isinstance(tools, list)
    assert len(tools) == 1


@pytest.mark.asyncio
async def test_tool_with_party_id(
    mock_llm_service: MockLLMService, sample_html: str
) -> None:
    """Test tool creation with party_id for history tracking."""
    # Force Pydantic implementation to use mock LLM service
    with patch.dict("os.environ", {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "false"}):
        # Create tools with party_id
        tools = create_member_extractor_tools(
            llm_service=mock_llm_service, party_id=123
        )
        extract_tool = tools[0]

        # Execute tool
        result = await extract_tool.ainvoke(
            {
                "url": "https://example.com/members",
                "html_content": sample_html,
                "party_name": "Example Party",
            }
        )

        # Verify result (party_id doesn't affect output, but ensures no errors)
        assert result["success"] is True
        assert result["count"] == 2


@pytest.mark.asyncio
async def test_extract_with_malformed_html(mock_llm_service: MockLLMService) -> None:
    """Test extraction with malformed HTML.

    Note: BeautifulSoup handles malformed HTML gracefully,
    so extraction may still succeed. This test verifies that
    the tool doesn't crash on malformed input.
    """
    # Force Pydantic implementation to use mock LLM service
    with patch.dict("os.environ", {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "false"}):
        # Create tools
        tools = create_member_extractor_tools(llm_service=mock_llm_service)
        extract_tool = tools[0]

        # Malformed HTML (unclosed tags, missing structure)
        malformed_html = """
        <html>
            <body>
                <div>
                    <h1>Members
                    <p>山田太郎
                </div>
            <!-- Missing closing tags -->
        """

        # Execute tool
        result = await extract_tool.ainvoke(
            {
                "url": "https://example.com/members",
                "html_content": malformed_html,
                "party_name": "Test Party",
            }
        )

        # Should handle gracefully without crashing
        # BeautifulSoup may still parse malformed HTML successfully
        assert "success" in result
        assert "count" in result
        assert "members" in result
        assert result["party_name"] == "Test Party"


@pytest.mark.asyncio
async def test_extract_with_large_content(mock_llm_service: MockLLMService) -> None:
    """Test extraction with very large HTML content (token limit scenario)."""
    # Force Pydantic implementation to use mock LLM service
    with patch.dict("os.environ", {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "false"}):
        # Create tools
        tools = create_member_extractor_tools(llm_service=mock_llm_service)
        extract_tool = tools[0]

        # Generate large HTML (simulate 100KB+ content)
        large_html = "<html><body><main>"
        # Add 1000 member entries
        for i in range(1000):
            large_html += f"""
            <div class="member">
                <h2>議員 {i}</h2>
                <p>役職: 衆議院議員</p>
                <p>選挙区: 東京{i % 25 + 1}区</p>
                <p>経歴: {"長い経歴テキスト" * 50}</p>
            </div>
            """
        large_html += "</main></body></html>"

        # Execute tool
        result = await extract_tool.ainvoke(
            {
                "url": "https://example.com/members",
                "html_content": large_html,
                "party_name": "Large Party",
            }
        )

        # Should either succeed or fail gracefully (no crash)
        assert "success" in result
        assert "count" in result
        assert "members" in result
        assert result["party_name"] == "Large Party"


@pytest.mark.asyncio
async def test_extract_with_invalid_url(mock_llm_service: MockLLMService) -> None:
    """Test extraction with invalid URL."""
    # Force Pydantic implementation to use mock LLM service
    with patch.dict("os.environ", {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "false"}):
        # Create tools
        tools = create_member_extractor_tools(llm_service=mock_llm_service)
        extract_tool = tools[0]

        # Execute tool with invalid URL
        result = await extract_tool.ainvoke(
            {
                "url": "not-a-valid-url",
                "html_content": "<html><body>Test</body></html>",
                "party_name": "Test Party",
            }
        )

        # Should handle gracefully (URL is used for context, not fetching)
        assert "success" in result
        assert "count" in result
        assert result["party_name"] == "Test Party"


@pytest.mark.asyncio
async def test_extract_with_empty_party_name(
    mock_llm_service: MockLLMService,
) -> None:
    """Test extraction with empty party name."""
    # Force Pydantic implementation to use mock LLM service
    with patch.dict("os.environ", {"USE_BAML_PARTY_MEMBER_EXTRACTOR": "false"}):
        # Create tools
        tools = create_member_extractor_tools(llm_service=mock_llm_service)
        extract_tool = tools[0]

        # Execute tool with empty party name
        result = await extract_tool.ainvoke(
            {
                "url": "https://example.com/members",
                "html_content": "<html><body><p>議員リスト</p></body></html>",
                "party_name": "",
            }
        )

        # Should handle gracefully
        assert "success" in result
        assert "count" in result
        assert result["party_name"] == ""
