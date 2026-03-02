"""Tests for MarkSpeakerAsNonPoliticianUseCase."""

from unittest.mock import AsyncMock

import pytest

from src.application.usecases.mark_speaker_as_non_politician_usecase import (
    MarkSpeakerAsNonPoliticianInputDto,
    MarkSpeakerAsNonPoliticianUseCase,
)
from src.domain.entities.speaker import Speaker


class TestMarkSpeakerAsNonPoliticianUseCase:
    """Test cases for MarkSpeakerAsNonPoliticianUseCase."""

    @pytest.fixture
    def mock_speaker_repo(self):
        """Create mock speaker repository."""
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_speaker_repo):
        """Create MarkSpeakerAsNonPoliticianUseCase instance."""
        return MarkSpeakerAsNonPoliticianUseCase(
            speaker_repository=mock_speaker_repo,
        )

    @pytest.mark.asyncio
    async def test_mark_as_non_politician_success(
        self,
        use_case,
        mock_speaker_repo,
    ):
        """非政治家分類が正常に設定される。"""
        speaker = Speaker(
            id=1,
            name="参考人",
            is_politician=True,
            politician_id=None,
        )
        mock_speaker_repo.get_by_id.return_value = speaker

        input_dto = MarkSpeakerAsNonPoliticianInputDto(
            speaker_id=1,
            skip_reason="reference_person",
        )

        result = await use_case.execute(input_dto)

        assert result.success is True
        assert result.error_message is None
        assert speaker.is_politician is False
        assert speaker.skip_reason == "reference_person"
        assert speaker.politician_id is None
        mock_speaker_repo.upsert.assert_called_once_with(speaker)

    @pytest.mark.asyncio
    async def test_mark_clears_politician_id(
        self,
        use_case,
        mock_speaker_repo,
    ):
        """既存のpolitician_idがクリアされる。"""
        speaker = Speaker(
            id=2,
            name="議長",
            is_politician=True,
            politician_id=100,
        )
        mock_speaker_repo.get_by_id.return_value = speaker

        input_dto = MarkSpeakerAsNonPoliticianInputDto(
            speaker_id=2,
            skip_reason="role_only",
        )

        result = await use_case.execute(input_dto)

        assert result.success is True
        assert speaker.politician_id is None
        assert speaker.is_politician is False
        assert speaker.skip_reason == "role_only"

    @pytest.mark.asyncio
    async def test_mark_speaker_not_found(
        self,
        use_case,
        mock_speaker_repo,
    ):
        """発言者が見つからない場合はエラーを返す。"""
        mock_speaker_repo.get_by_id.return_value = None

        input_dto = MarkSpeakerAsNonPoliticianInputDto(
            speaker_id=999,
            skip_reason="other_non_politician",
        )

        result = await use_case.execute(input_dto)

        assert result.success is False
        assert result.error_message == "発言者が見つかりません"
        mock_speaker_repo.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_mark_with_invalid_skip_reason(
        self,
        use_case,
        mock_speaker_repo,
    ):
        """無効なskip_reasonはエラーを返す。"""
        input_dto = MarkSpeakerAsNonPoliticianInputDto(
            speaker_id=1,
            skip_reason="invalid_reason",
        )

        result = await use_case.execute(input_dto)

        assert result.success is False
        assert "無効なスキップ理由" in result.error_message
        mock_speaker_repo.get_by_id.assert_not_called()
        mock_speaker_repo.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_mark_with_government_official(
        self,
        use_case,
        mock_speaker_repo,
    ):
        """政府参考人として分類できる。"""
        speaker = Speaker(
            id=3,
            name="政府参考人（山田太郎君）",
            is_politician=True,
        )
        mock_speaker_repo.get_by_id.return_value = speaker

        input_dto = MarkSpeakerAsNonPoliticianInputDto(
            speaker_id=3,
            skip_reason="government_official",
        )

        result = await use_case.execute(input_dto)

        assert result.success is True
        assert speaker.skip_reason == "government_official"
        assert speaker.is_politician is False
