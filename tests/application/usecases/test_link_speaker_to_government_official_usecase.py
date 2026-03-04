"""LinkSpeakerToGovernmentOfficialUseCaseのテスト."""

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.government_official_dto import (
    LinkSpeakerToGovernmentOfficialInputDto,
)
from src.application.usecases.link_speaker_to_government_official_usecase import (
    LinkSpeakerToGovernmentOfficialUseCase,
)
from src.domain.entities.government_official import GovernmentOfficial
from src.domain.entities.speaker import Speaker


class TestLinkSpeakerToGovernmentOfficialUseCase:
    """LinkSpeakerToGovernmentOfficialUseCaseのテスト."""

    @pytest.fixture
    def mock_speaker_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_official_repo(self):
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_speaker_repo, mock_official_repo):
        return LinkSpeakerToGovernmentOfficialUseCase(
            speaker_repository=mock_speaker_repo,
            government_official_repository=mock_official_repo,
        )

    @pytest.mark.asyncio
    async def test_success(self, use_case, mock_speaker_repo, mock_official_repo):
        """正常系: 発言者と政府関係者の紐付けが成功する."""
        speaker = Speaker(id=1, name="法務省刑事局長")
        mock_speaker_repo.get_by_id.return_value = speaker

        official = GovernmentOfficial(id=10, name="法務省刑事局長")
        mock_official_repo.get_by_id.return_value = official

        input_dto = LinkSpeakerToGovernmentOfficialInputDto(
            speaker_id=1, government_official_id=10
        )
        result = await use_case.execute(input_dto)

        assert result.success is True
        assert result.error_message is None
        assert speaker.government_official_id == 10
        assert speaker.is_politician is False
        assert speaker.skip_reason == "government_official"
        mock_speaker_repo.update.assert_called_once_with(speaker)

    @pytest.mark.asyncio
    async def test_speaker_not_found(self, use_case, mock_speaker_repo):
        """発言者が見つからない場合はエラーを返す."""
        mock_speaker_repo.get_by_id.return_value = None

        input_dto = LinkSpeakerToGovernmentOfficialInputDto(
            speaker_id=999, government_official_id=10
        )
        result = await use_case.execute(input_dto)

        assert result.success is False
        assert result.error_message == "発言者が見つかりません"
        mock_speaker_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_speaker_already_linked_to_politician(
        self, use_case, mock_speaker_repo
    ):
        """politician_id設定済みの発言者にはエラーを返す（優先度ルール）."""
        speaker = Speaker(id=1, name="山田太郎", politician_id=100)
        mock_speaker_repo.get_by_id.return_value = speaker

        input_dto = LinkSpeakerToGovernmentOfficialInputDto(
            speaker_id=1, government_official_id=10
        )
        result = await use_case.execute(input_dto)

        assert result.success is False
        assert "政治家に紐付けられています" in (result.error_message or "")
        mock_speaker_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_speaker_already_linked_to_government_official(
        self, use_case, mock_speaker_repo
    ):
        """government_official_id設定済みの発言者にはエラーを返す."""
        speaker = Speaker(id=1, name="法務省刑事局長", government_official_id=5)
        mock_speaker_repo.get_by_id.return_value = speaker

        input_dto = LinkSpeakerToGovernmentOfficialInputDto(
            speaker_id=1, government_official_id=10
        )
        result = await use_case.execute(input_dto)

        assert result.success is False
        assert "政府関係者に紐付けられています" in (result.error_message or "")
        mock_speaker_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_official_not_found(
        self, use_case, mock_speaker_repo, mock_official_repo
    ):
        """政府関係者が見つからない場合はエラーを返す."""
        speaker = Speaker(id=1, name="法務省刑事局長")
        mock_speaker_repo.get_by_id.return_value = speaker
        mock_official_repo.get_by_id.return_value = None

        input_dto = LinkSpeakerToGovernmentOfficialInputDto(
            speaker_id=1, government_official_id=999
        )
        result = await use_case.execute(input_dto)

        assert result.success is False
        assert "政府関係者が見つかりません" in (result.error_message or "")
        mock_speaker_repo.update.assert_not_called()
