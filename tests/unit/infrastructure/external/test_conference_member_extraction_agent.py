"""会議体メンバー抽出エージェントのユニットテスト

Issue #903: [LangGraph+BAML] 会議体メンバー抽出のエージェント化
"""

# ruff: noqa: E501  # テストファイルでは長い行を許容

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestConferenceMemberExtractionAgent:
    """ConferenceMemberExtractionAgentのテスト"""

    @pytest.fixture
    def mock_llm(self):
        """モックLLMを作成"""
        mock = MagicMock()
        mock.bind_tools = MagicMock(return_value=mock)
        return mock

    @pytest.fixture
    def agent(self, mock_llm):
        """エージェントインスタンスを作成"""
        with patch(
            "src.infrastructure.external.langgraph_conference_member_extraction_agent.create_conference_member_extraction_tools"
        ) as mock_tools:
            mock_tools.return_value = []

            from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
                ConferenceMemberExtractionAgent,
            )

            return ConferenceMemberExtractionAgent(llm=mock_llm)

    def test_agent_initialization(self, agent):
        """エージェントが正しく初期化されること"""
        assert agent.llm is not None
        assert agent.tools is not None
        assert agent.agent is not None

    def test_agent_compile(self, agent):
        """エージェントがコンパイルできること"""
        compiled = agent.compile()
        assert compiled is not None

    @pytest.mark.asyncio
    async def test_extract_members_returns_result(self, mock_llm):
        """extract_membersが結果を返すこと"""
        from src.domain.dtos.conference_member_dto import ExtractedMemberDTO

        # ツールの結果をモック
        mock_tool_result = {
            "members": [
                {
                    "name": "田中太郎",
                    "role": "委員長",
                    "party_name": "〇〇党",
                    "additional_info": None,
                }
            ],
            "count": 1,
            "success": True,
        }

        with patch(
            "src.infrastructure.external.langgraph_conference_member_extraction_agent.create_conference_member_extraction_tools"
        ):
            with patch(
                "src.infrastructure.external.langgraph_conference_member_extraction_agent.create_react_agent"
            ) as mock_create_agent:
                # エージェントの実行結果をモック
                mock_agent = AsyncMock()
                mock_agent.ainvoke.return_value = {
                    "raw_members": mock_tool_result["members"],
                    "validated_members": mock_tool_result["members"],
                    "final_members": mock_tool_result["members"],
                    "validation_errors": [],
                    "messages": [],
                    "error_message": None,
                }
                mock_create_agent.return_value = mock_agent

                from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
                    ConferenceMemberExtractionAgent,
                )

                agent = ConferenceMemberExtractionAgent(llm=mock_llm)

                result = await agent.extract_members(
                    html_content="<html>test</html>",
                    conference_name="総務委員会",
                )

                assert result["success"] is True
                assert len(result["members"]) == 1
                assert isinstance(result["members"][0], ExtractedMemberDTO)
                assert result["members"][0].name == "田中太郎"

    @pytest.mark.asyncio
    async def test_extract_members_handles_error(self, mock_llm):
        """extract_membersがエラーを適切に処理すること"""
        with patch(
            "src.infrastructure.external.langgraph_conference_member_extraction_agent.create_conference_member_extraction_tools"
        ):
            with patch(
                "src.infrastructure.external.langgraph_conference_member_extraction_agent.create_react_agent"
            ) as mock_create_agent:
                # エージェントがエラーを投げるようにモック
                mock_agent = AsyncMock()
                mock_agent.ainvoke.side_effect = Exception("テストエラー")
                mock_create_agent.return_value = mock_agent

                from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
                    ConferenceMemberExtractionAgent,
                )

                agent = ConferenceMemberExtractionAgent(llm=mock_llm)

                result = await agent.extract_members(
                    html_content="<html>test</html>",
                    conference_name="総務委員会",
                )

                assert result["success"] is False
                assert result["error_message"] is not None
                assert "テストエラー" in result["error_message"]

    @pytest.mark.asyncio
    async def test_extract_members_empty_result(self, mock_llm):
        """extract_membersが空の結果を正しく処理すること"""
        with patch(
            "src.infrastructure.external.langgraph_conference_member_extraction_agent.create_conference_member_extraction_tools"
        ):
            with patch(
                "src.infrastructure.external.langgraph_conference_member_extraction_agent.create_react_agent"
            ) as mock_create_agent:
                # 空の結果を返すようにモック
                mock_agent = AsyncMock()
                mock_agent.ainvoke.return_value = {
                    "raw_members": [],
                    "validated_members": [],
                    "final_members": [],
                    "validation_errors": [],
                    "messages": [],
                    "error_message": None,
                }
                mock_create_agent.return_value = mock_agent

                from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
                    ConferenceMemberExtractionAgent,
                )

                agent = ConferenceMemberExtractionAgent(llm=mock_llm)

                result = await agent.extract_members(
                    html_content="<html>empty</html>",
                    conference_name="総務委員会",
                )

                assert result["success"] is False
                assert len(result["members"]) == 0


class TestMemberExtractorFactory:
    """MemberExtractorFactoryのテスト"""

    def test_create_returns_baml_extractor(self):
        """create()がBAMLMemberExtractorを返すこと"""
        from src.infrastructure.external.conference_member_extractor.baml_extractor import (
            BAMLMemberExtractor,
        )
        from src.infrastructure.external.conference_member_extractor.factory import (
            MemberExtractorFactory,
        )

        extractor = MemberExtractorFactory.create()
        assert isinstance(extractor, BAMLMemberExtractor)

    def test_create_agent_returns_agent(self):
        """create_agent()がConferenceMemberExtractionAgentを返すこと"""
        mock_llm = MagicMock()

        with patch(
            "langchain_google_genai.ChatGoogleGenerativeAI",
            return_value=mock_llm,
        ):
            with patch(
                "src.infrastructure.external.langgraph_conference_member_extraction_agent.create_conference_member_extraction_tools"
            ):
                from src.infrastructure.external.conference_member_extractor.factory import (
                    MemberExtractorFactory,
                )
                from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
                    ConferenceMemberExtractionAgent,
                )

                agent = MemberExtractorFactory.create_agent()
                assert isinstance(agent, ConferenceMemberExtractionAgent)

    def test_create_agent_with_custom_llm(self):
        """create_agent()がカスタムLLMを受け付けること"""
        mock_llm = MagicMock()

        with patch(
            "src.infrastructure.external.langgraph_conference_member_extraction_agent.create_conference_member_extraction_tools"
        ):
            from src.infrastructure.external.conference_member_extractor.factory import (
                MemberExtractorFactory,
            )
            from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
                ConferenceMemberExtractionAgent,
            )

            agent = MemberExtractorFactory.create_agent(llm=mock_llm)
            assert isinstance(agent, ConferenceMemberExtractionAgent)
            assert agent.llm == mock_llm
