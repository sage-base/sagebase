"""ImportGovernmentOfficialsCsvUseCaseのテスト."""

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.government_official_dto import (
    GovernmentOfficialCsvRow,
    ImportGovernmentOfficialsCsvInputDto,
)
from src.application.usecases.import_government_officials_csv_usecase import (
    ImportGovernmentOfficialsCsvUseCase,
)
from src.domain.entities.government_official import GovernmentOfficial
from src.domain.entities.speaker import Speaker


class TestImportGovernmentOfficialsCsvUseCase:
    """ImportGovernmentOfficialsCsvUseCaseのテスト."""

    @pytest.fixture
    def mock_official_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_position_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_speaker_repo(self):
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_official_repo, mock_position_repo, mock_speaker_repo):
        return ImportGovernmentOfficialsCsvUseCase(
            government_official_repository=mock_official_repo,
            government_official_position_repository=mock_position_repo,
            speaker_repository=mock_speaker_repo,
        )

    @pytest.mark.asyncio
    async def test_empty_rows(self, use_case):
        """空の行リスト → 何もせず空の結果を返す."""
        input_dto = ImportGovernmentOfficialsCsvInputDto(rows=[])
        result = await use_case.execute(input_dto)

        assert result.created_officials_count == 0
        assert result.created_positions_count == 0
        assert result.linked_speakers_count == 0
        assert result.skipped_count == 0
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_skip_row_without_org_and_position(
        self, use_case, mock_official_repo
    ):
        """organizationもpositionも空の行はスキップ."""
        row = GovernmentOfficialCsvRow(
            speaker_name="テスト",
            representative_speaker_id=1,
            organization="",
            position="",
        )
        input_dto = ImportGovernmentOfficialsCsvInputDto(rows=[row])
        result = await use_case.execute(input_dto)

        assert result.skipped_count == 1
        assert result.created_officials_count == 0
        mock_official_repo.get_by_name.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_new_official_and_link_speaker(
        self, use_case, mock_official_repo, mock_position_repo, mock_speaker_repo
    ):
        """新規GovernmentOfficialを作成しSpeakerを紐付ける."""
        created_official = GovernmentOfficial(id=10, name="法務省刑事局長")
        mock_official_repo.get_by_name.return_value = None
        mock_official_repo.create.return_value = created_official
        mock_position_repo.bulk_upsert.return_value = []

        speaker = Speaker(id=1, name="法務省刑事局長")
        mock_speaker_repo.search_by_name.return_value = [speaker]

        row = GovernmentOfficialCsvRow(
            speaker_name="法務省刑事局長",
            representative_speaker_id=1,
            organization="法務省",
            position="刑事局長",
            notes="法務省刑事局長",
        )
        input_dto = ImportGovernmentOfficialsCsvInputDto(rows=[row])
        result = await use_case.execute(input_dto)

        assert result.created_officials_count == 1
        assert result.created_positions_count == 1
        assert result.linked_speakers_count == 1
        mock_official_repo.create.assert_called_once()
        mock_position_repo.bulk_upsert.assert_called_once()
        mock_speaker_repo.update.assert_called_once()
        assert speaker.government_official_id == 10
        assert speaker.is_politician is False
        assert speaker.skip_reason == "government_official"

    @pytest.mark.asyncio
    async def test_find_existing_official(
        self, use_case, mock_official_repo, mock_position_repo, mock_speaker_repo
    ):
        """既存GovernmentOfficialを再利用する."""
        existing = GovernmentOfficial(id=5, name="法務省刑事局長")
        mock_official_repo.get_by_name.return_value = existing
        mock_position_repo.bulk_upsert.return_value = []
        mock_speaker_repo.search_by_name.return_value = []

        row = GovernmentOfficialCsvRow(
            speaker_name="法務省刑事局長",
            representative_speaker_id=1,
            organization="法務省",
            position="刑事局長",
        )
        input_dto = ImportGovernmentOfficialsCsvInputDto(rows=[row])
        result = await use_case.execute(input_dto)

        assert result.created_officials_count == 0
        mock_official_repo.create.assert_not_called()
        mock_position_repo.bulk_upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_speaker_with_politician_id(
        self, use_case, mock_official_repo, mock_position_repo, mock_speaker_repo
    ):
        """politician_id設定済みのSpeakerは紐付けをスキップする."""
        existing = GovernmentOfficial(id=5, name="山田太郎")
        mock_official_repo.get_by_name.return_value = existing
        mock_position_repo.bulk_upsert.return_value = []

        speaker = Speaker(id=1, name="山田太郎", politician_id=100)
        mock_speaker_repo.search_by_name.return_value = [speaker]

        row = GovernmentOfficialCsvRow(
            speaker_name="山田太郎",
            representative_speaker_id=1,
            organization="法務省",
            position="局長",
        )
        input_dto = ImportGovernmentOfficialsCsvInputDto(rows=[row])
        result = await use_case.execute(input_dto)

        assert result.linked_speakers_count == 0
        mock_speaker_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_link_multiple_same_name_speakers(
        self, use_case, mock_official_repo, mock_position_repo, mock_speaker_repo
    ):
        """同名のSpeaker全件を紐付ける."""
        existing = GovernmentOfficial(id=5, name="法務省刑事局長")
        mock_official_repo.get_by_name.return_value = existing
        mock_position_repo.bulk_upsert.return_value = []

        speaker1 = Speaker(id=1, name="法務省刑事局長")
        speaker2 = Speaker(id=2, name="法務省刑事局長")
        speaker_different = Speaker(id=3, name="法務省刑事局長補佐")
        mock_speaker_repo.search_by_name.return_value = [
            speaker1,
            speaker2,
            speaker_different,
        ]

        row = GovernmentOfficialCsvRow(
            speaker_name="法務省刑事局長",
            representative_speaker_id=1,
            organization="法務省",
            position="刑事局長",
        )
        input_dto = ImportGovernmentOfficialsCsvInputDto(rows=[row])
        result = await use_case.execute(input_dto)

        assert result.linked_speakers_count == 2
        assert mock_speaker_repo.update.call_count == 2
        assert speaker1.government_official_id == 5
        assert speaker2.government_official_id == 5
        assert speaker_different.government_official_id is None

    @pytest.mark.asyncio
    async def test_dry_run_counts_correctly(
        self, use_case, mock_official_repo, mock_position_repo, mock_speaker_repo
    ):
        """dry_runモードでカウントが正しく集計される."""
        mock_official_repo.get_by_name.return_value = None

        speaker = Speaker(id=1, name="法務省刑事局長")
        mock_speaker_repo.search_by_name.return_value = [speaker]

        row = GovernmentOfficialCsvRow(
            speaker_name="法務省刑事局長",
            representative_speaker_id=1,
            organization="法務省",
            position="刑事局長",
        )
        input_dto = ImportGovernmentOfficialsCsvInputDto(rows=[row], dry_run=True)
        result = await use_case.execute(input_dto)

        assert result.created_officials_count == 1
        assert result.created_positions_count == 1
        assert result.linked_speakers_count == 1
        mock_official_repo.create.assert_not_called()
        mock_position_repo.bulk_upsert.assert_not_called()
        mock_speaker_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_dry_run_skips_speaker_with_politician_id(
        self, use_case, mock_official_repo, mock_speaker_repo
    ):
        """dry_runでもpolitician_id設定済みSpeakerはカウントしない."""
        mock_official_repo.get_by_name.return_value = None

        speaker = Speaker(id=1, name="山田太郎", politician_id=100)
        mock_speaker_repo.search_by_name.return_value = [speaker]

        row = GovernmentOfficialCsvRow(
            speaker_name="山田太郎",
            representative_speaker_id=1,
            organization="法務省",
            position="局長",
        )
        input_dto = ImportGovernmentOfficialsCsvInputDto(rows=[row], dry_run=True)
        result = await use_case.execute(input_dto)

        assert result.linked_speakers_count == 0

    @pytest.mark.asyncio
    async def test_row_exception_captured_as_error(self, use_case, mock_official_repo):
        """行処理中の例外はerrorsに記録される."""
        mock_official_repo.get_by_name.side_effect = RuntimeError("DB接続エラー")

        row = GovernmentOfficialCsvRow(
            speaker_name="テスト",
            representative_speaker_id=1,
            organization="法務省",
            position="局長",
        )
        input_dto = ImportGovernmentOfficialsCsvInputDto(rows=[row])
        result = await use_case.execute(input_dto)

        assert len(result.errors) == 1
        assert "DB接続エラー" in result.errors[0]
