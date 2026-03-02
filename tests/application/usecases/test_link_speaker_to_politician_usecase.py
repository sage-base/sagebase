"""Tests for LinkSpeakerToPoliticianUseCase."""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from src.application.usecases.link_speaker_to_politician_usecase import (
    LinkSpeakerToPoliticianInputDto,
    LinkSpeakerToPoliticianUseCase,
)
from src.domain.entities.speaker import Speaker


class TestLinkSpeakerToPoliticianUseCase:
    """Test cases for LinkSpeakerToPoliticianUseCase."""

    @pytest.fixture
    def mock_speaker_repo(self):
        """Create mock speaker repository."""
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_speaker_repo):
        """Create LinkSpeakerToPoliticianUseCase instance."""
        return LinkSpeakerToPoliticianUseCase(
            speaker_repository=mock_speaker_repo,
        )

    @pytest.mark.asyncio
    async def test_link_speaker_to_politician_success(
        self,
        use_case,
        mock_speaker_repo,
    ):
        """発言者と政治家の紐付けが成功する。"""
        # Setup
        speaker = Speaker(
            id=1,
            name="山田太郎",
            type="議員",
            political_party_name="〇〇党",
            is_politician=True,
            politician_id=None,
            matched_by_user_id=None,
        )
        mock_speaker_repo.get_by_id.return_value = speaker

        user_id = UUID("12345678-1234-5678-1234-567812345678")
        input_dto = LinkSpeakerToPoliticianInputDto(
            speaker_id=1,
            politician_id=100,
            politician_name="山田太郎（政治家）",
            user_id=user_id,
        )

        # Execute
        result = await use_case.execute(input_dto)

        # Assert
        assert result.success is True
        assert result.error_message is None
        assert result.updated_matching_dto is not None
        assert result.updated_matching_dto.speaker_id == 1
        assert result.updated_matching_dto.matched_politician_id == 100
        assert (
            result.updated_matching_dto.matched_politician_name == "山田太郎（政治家）"
        )
        assert result.updated_matching_dto.matching_method == "manual"
        assert result.updated_matching_dto.confidence_score == 1.0

        # 発言者が更新されたことを確認
        assert speaker.politician_id == 100
        assert speaker.matched_by_user_id == user_id
        assert speaker.is_manually_verified is True
        assert speaker.is_politician is True
        assert speaker.skip_reason is None

        # upsertが呼ばれたことを確認
        mock_speaker_repo.upsert.assert_called_once_with(speaker)

    @pytest.mark.asyncio
    async def test_link_speaker_to_politician_without_user_id(
        self,
        use_case,
        mock_speaker_repo,
    ):
        """ユーザーID無しでも紐付けが成功する。"""
        # Setup
        speaker = Speaker(
            id=2,
            name="鈴木花子",
            type="議員",
            is_politician=True,
        )
        mock_speaker_repo.get_by_id.return_value = speaker

        input_dto = LinkSpeakerToPoliticianInputDto(
            speaker_id=2,
            politician_id=200,
            politician_name="鈴木花子（政治家）",
            user_id=None,
        )

        # Execute
        result = await use_case.execute(input_dto)

        # Assert
        assert result.success is True
        assert speaker.politician_id == 200
        assert speaker.matched_by_user_id is None
        assert speaker.is_manually_verified is True
        assert speaker.is_politician is True

    @pytest.mark.asyncio
    async def test_link_speaker_to_politician_speaker_not_found(
        self,
        use_case,
        mock_speaker_repo,
    ):
        """発言者が見つからない場合はエラーを返す。"""
        # Setup
        mock_speaker_repo.get_by_id.return_value = None

        input_dto = LinkSpeakerToPoliticianInputDto(
            speaker_id=999,
            politician_id=100,
            politician_name="存在しない政治家",
        )

        # Execute
        result = await use_case.execute(input_dto)

        # Assert
        assert result.success is False
        assert result.error_message == "発言者が見つかりません"
        assert result.updated_matching_dto is None

        # upsertが呼ばれていないことを確認
        mock_speaker_repo.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_link_speaker_to_politician_updates_existing_link(
        self,
        use_case,
        mock_speaker_repo,
    ):
        """既存の紐付けを上書きできる。"""
        # Setup - 既に別の政治家に紐付けられている発言者
        speaker = Speaker(
            id=3,
            name="佐藤次郎",
            type="議員",
            is_politician=True,
            politician_id=50,  # 既存の紐付け
            matched_by_user_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        )
        mock_speaker_repo.get_by_id.return_value = speaker

        new_user_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        input_dto = LinkSpeakerToPoliticianInputDto(
            speaker_id=3,
            politician_id=150,  # 新しい政治家ID
            politician_name="佐藤次郎（修正後）",
            user_id=new_user_id,
        )

        # Execute
        result = await use_case.execute(input_dto)

        # Assert
        assert result.success is True
        assert speaker.politician_id == 150
        assert speaker.matched_by_user_id == new_user_id
        assert speaker.is_manually_verified is True

    @pytest.mark.asyncio
    async def test_link_clears_skip_reason(
        self,
        use_case,
        mock_speaker_repo,
    ):
        """紐付け時にskip_reasonがクリアされる。"""
        speaker = Speaker(
            id=4,
            name="政府参考人",
            is_politician=False,
            skip_reason="government_official",
        )
        mock_speaker_repo.get_by_id.return_value = speaker

        input_dto = LinkSpeakerToPoliticianInputDto(
            speaker_id=4,
            politician_id=300,
            politician_name="田中一郎",
        )

        result = await use_case.execute(input_dto)

        assert result.success is True
        assert speaker.is_politician is True
        assert speaker.skip_reason is None
        assert speaker.politician_id == 300
