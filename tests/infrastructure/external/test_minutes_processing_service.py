"""Tests for MinutesProcessAgentService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.value_objects.speaker_speech import SpeakerSpeech
from src.infrastructure.external.minutes_processing_service import (
    MinutesProcessAgentService,
)
from src.minutes_divide_processor.models import SpeakerAndSpeechContent


class TestMinutesProcessAgentService:
    """Test cases for MinutesProcessAgentService."""

    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service."""
        mock = MagicMock(spec=ILLMService)
        return mock

    @pytest.fixture
    def service(self, mock_llm_service):
        """Create MinutesProcessAgentService instance."""
        return MinutesProcessAgentService(llm_service=mock_llm_service)

    @pytest.mark.asyncio
    async def test_process_minutes_with_valid_speeches(self, service):
        """Test processing with valid speeches."""
        # Setup - LangGraphから返される正規化済み結果をモック
        mock_results = [
            SpeakerAndSpeechContent(
                speaker="山田太郎",
                speech_content="これは発言内容です。",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
            SpeakerAndSpeechContent(
                speaker="田中花子",
                speech_content="別の発言内容です。",
                chapter_number=2,
                sub_chapter_number=1,
                speech_order=2,
            ),
        ]

        with patch.object(
            service.agent, "run", new_callable=AsyncMock, return_value=mock_results
        ):
            # Execute
            result = await service.process_minutes("議事録テキスト")

            # Verify
            assert len(result) == 2
            assert all(isinstance(speech, SpeakerSpeech) for speech in result)
            assert result[0].speaker == "山田太郎"
            assert result[0].speech_content == "これは発言内容です。"
            assert result[1].speaker == "田中花子"
            assert result[1].speech_content == "別の発言内容です。"

    @pytest.mark.asyncio
    async def test_process_minutes_filters_empty_content(self, service):
        """Test that speeches with empty content are filtered out (safety check)."""
        # Setup - 空のコンテンツが含まれる結果（通常はLLMでフィルタされるが安全のため）
        mock_results = [
            SpeakerAndSpeechContent(
                speaker="山田太郎",
                speech_content="有効な発言",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
            SpeakerAndSpeechContent(
                speaker="田中花子",
                speech_content="",  # Empty content - should be filtered
                chapter_number=2,
                sub_chapter_number=1,
                speech_order=2,
            ),
            SpeakerAndSpeechContent(
                speaker="鈴木一郎",
                speech_content="別の有効な発言",
                chapter_number=3,
                sub_chapter_number=1,
                speech_order=3,
            ),
        ]

        with patch.object(
            service.agent, "run", new_callable=AsyncMock, return_value=mock_results
        ):
            # Execute
            result = await service.process_minutes("議事録テキスト")

            # Verify - only 2 valid speeches should be returned
            assert len(result) == 2
            assert result[0].speaker == "山田太郎"
            assert result[1].speaker == "鈴木一郎"

    @pytest.mark.asyncio
    async def test_process_minutes_filters_empty_speaker(self, service):
        """Test that speeches with empty speaker names are filtered out."""
        # Setup
        mock_results = [
            SpeakerAndSpeechContent(
                speaker="",  # Empty speaker - should be filtered
                speech_content="発言内容",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
            SpeakerAndSpeechContent(
                speaker="田中花子",
                speech_content="有効な発言",
                chapter_number=2,
                sub_chapter_number=1,
                speech_order=2,
            ),
        ]

        with patch.object(
            service.agent, "run", new_callable=AsyncMock, return_value=mock_results
        ):
            # Execute
            result = await service.process_minutes("議事録テキスト")

            # Verify - only 1 valid speech
            assert len(result) == 1
            assert result[0].speaker == "田中花子"

    @pytest.mark.asyncio
    async def test_process_minutes_returns_empty_list_when_all_filtered(self, service):
        """Test that empty list is returned when all speeches are filtered out."""
        # Setup - all invalid speeches
        mock_results = [
            SpeakerAndSpeechContent(
                speaker="",
                speech_content="発言内容",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
            SpeakerAndSpeechContent(
                speaker="田中花子",
                speech_content="",
                chapter_number=2,
                sub_chapter_number=1,
                speech_order=2,
            ),
        ]

        with patch.object(
            service.agent, "run", new_callable=AsyncMock, return_value=mock_results
        ):
            # Execute
            result = await service.process_minutes("議事録テキスト")

            # Verify - empty list
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_process_minutes_passes_role_name_mappings_to_agent(self, service):
        """Test that role_name_mappings is passed to the agent (Issue #946)."""
        # Setup
        mock_results = [
            SpeakerAndSpeechContent(
                speaker="伊藤条一",  # LLMで正規化済み（元は「議長」）
                speech_content="開会を宣言します。",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
        ]

        role_name_mappings = {"議長": "伊藤条一"}

        with patch.object(
            service.agent, "run", new_callable=AsyncMock, return_value=mock_results
        ) as mock_run:
            # Execute
            result = await service.process_minutes(
                "議事録テキスト", role_name_mappings=role_name_mappings
            )

            # Verify - agent.run was called with role_name_mappings
            mock_run.assert_called_once_with(
                "議事録テキスト",
                role_name_mappings=role_name_mappings,
            )
            assert len(result) == 1
            assert result[0].speaker == "伊藤条一"

    @pytest.mark.asyncio
    async def test_process_minutes_with_normalized_results(self, service):
        """Test that LLM-normalized results are converted to domain objects."""
        # Setup - LangGraphで正規化された結果
        # 「市長（松井一郎）」→「松井一郎」に変換済み
        # 「副市長」→マッピングで「田中花子」に変換済み
        # 「部長」→マッピングなしでスキップ済み
        mock_results = [
            SpeakerAndSpeechContent(
                speaker="松井一郎",  # 元は「市長（松井一郎）」
                speech_content="発言1",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
            SpeakerAndSpeechContent(
                speaker="田中花子",  # 元は「副市長」→マッピングで変換
                speech_content="発言2",
                chapter_number=2,
                sub_chapter_number=1,
                speech_order=2,
            ),
            SpeakerAndSpeechContent(
                speaker="西村義直",  # 人名のみ→そのまま
                speech_content="発言3",
                chapter_number=3,
                sub_chapter_number=1,
                speech_order=3,
            ),
        ]

        role_name_mappings = {"副市長": "田中花子"}

        with patch.object(
            service.agent, "run", new_callable=AsyncMock, return_value=mock_results
        ):
            # Execute
            result = await service.process_minutes(
                "議事録テキスト", role_name_mappings=role_name_mappings
            )

            # Verify - 各発言者が正しく変換されている
            assert len(result) == 3
            assert result[0].speaker == "松井一郎"
            assert result[1].speaker == "田中花子"
            assert result[2].speaker == "西村義直"

    @pytest.mark.asyncio
    async def test_process_minutes_without_mappings(self, service):
        """Test processing without role_name_mappings."""
        # Setup
        mock_results = [
            SpeakerAndSpeechContent(
                speaker="西村義直",
                speech_content="議事を進めます。",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
        ]

        with patch.object(
            service.agent, "run", new_callable=AsyncMock, return_value=mock_results
        ) as mock_run:
            # Execute - マッピングなし
            result = await service.process_minutes("議事録テキスト")

            # Verify
            mock_run.assert_called_once_with(
                "議事録テキスト",
                role_name_mappings=None,
            )
            assert len(result) == 1
            assert result[0].speaker == "西村義直"
