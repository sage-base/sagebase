"""export-unclassified-speakers コマンドのテスト."""

from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.value_objects.speaker_with_conversation_count import (
    SpeakerWithConversationCount,
)
from src.interfaces.cli.commands.kokkai.export_unclassified_speakers import (
    export_unclassified_speakers,
)


_DI_PATH = "src.infrastructure.di.container"


def _make_speaker(
    id: int, name: str, conversation_count: int
) -> SpeakerWithConversationCount:
    return SpeakerWithConversationCount(
        id=id,
        name=name,
        type=None,
        political_party_name=None,
        position=None,
        is_politician=False,
        conversation_count=conversation_count,
    )


def _setup_repo_mock(mock_container: MagicMock) -> AsyncMock:
    mock_repo = AsyncMock(spec=SpeakerRepository)
    mock_container.repositories.speaker_repository.return_value = mock_repo
    return mock_repo


class TestExportUnclassifiedSpeakers:
    @patch(f"{_DI_PATH}.get_container")
    def test_default_table_output(self, mock_get_container: MagicMock) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_repo = _setup_repo_mock(mock_container)
        mock_repo.get_speakers_with_conversation_count = AsyncMock(
            return_value=[
                _make_speaker(1, "山田太郎", 50),
                _make_speaker(2, "鈴木花子", 30),
            ]
        )

        runner = CliRunner()
        result = runner.invoke(export_unclassified_speakers)

        assert result.exit_code == 0
        assert "山田太郎" in result.output
        assert "鈴木花子" in result.output
        assert "合計: 2件" in result.output
        mock_repo.get_speakers_with_conversation_count.assert_called_once_with(
            has_politician_id=False,
            has_government_official_id=False,
            min_conversation_count=None,
            limit=None,
        )

    @patch(f"{_DI_PATH}.get_container")
    def test_csv_output(self, mock_get_container: MagicMock) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_repo = _setup_repo_mock(mock_container)
        mock_repo.get_speakers_with_conversation_count = AsyncMock(
            return_value=[
                _make_speaker(1, "山田太郎", 50),
                _make_speaker(2, "鈴木花子", 30),
            ]
        )

        runner = CliRunner()
        result = runner.invoke(export_unclassified_speakers, ["--format", "csv"])

        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert lines[0] == "speaker_id,name,conversation_count"
        assert lines[1] == "1,山田太郎,50"
        assert lines[2] == "2,鈴木花子,30"

    @patch(f"{_DI_PATH}.get_container")
    def test_limit_passed_to_repository(self, mock_get_container: MagicMock) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_repo = _setup_repo_mock(mock_container)
        mock_repo.get_speakers_with_conversation_count = AsyncMock(
            return_value=[
                _make_speaker(1, "発言者A", 100),
                _make_speaker(2, "発言者B", 50),
            ]
        )

        runner = CliRunner()
        result = runner.invoke(export_unclassified_speakers, ["--limit", "2"])

        assert result.exit_code == 0
        mock_repo.get_speakers_with_conversation_count.assert_called_once_with(
            has_politician_id=False,
            has_government_official_id=False,
            min_conversation_count=None,
            limit=2,
        )

    @patch(f"{_DI_PATH}.get_container")
    def test_min_conversations_passed_to_repository(
        self, mock_get_container: MagicMock
    ) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_repo = _setup_repo_mock(mock_container)
        mock_repo.get_speakers_with_conversation_count = AsyncMock(
            return_value=[_make_speaker(1, "発言者A", 100)]
        )

        runner = CliRunner()
        result = runner.invoke(
            export_unclassified_speakers, ["--min-conversations", "10"]
        )

        assert result.exit_code == 0
        mock_repo.get_speakers_with_conversation_count.assert_called_once_with(
            has_politician_id=False,
            has_government_official_id=False,
            min_conversation_count=10,
            limit=None,
        )

    @patch(f"{_DI_PATH}.get_container")
    def test_limit_and_min_conversations_combined(
        self, mock_get_container: MagicMock
    ) -> None:
        """--limit と --min-conversations を同時に指定した場合、
        両方がリポジトリに渡されることを検証する."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_repo = _setup_repo_mock(mock_container)
        mock_repo.get_speakers_with_conversation_count = AsyncMock(
            return_value=[
                _make_speaker(1, "発言者A", 100),
                _make_speaker(2, "発言者B", 50),
            ]
        )

        runner = CliRunner()
        result = runner.invoke(
            export_unclassified_speakers,
            ["--min-conversations", "10", "--limit", "5"],
        )

        assert result.exit_code == 0
        mock_repo.get_speakers_with_conversation_count.assert_called_once_with(
            has_politician_id=False,
            has_government_official_id=False,
            min_conversation_count=10,
            limit=5,
        )
        assert "発言者A" in result.output
        assert "発言者B" in result.output

    @patch(f"{_DI_PATH}.get_container")
    def test_no_data(self, mock_get_container: MagicMock) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_repo = _setup_repo_mock(mock_container)
        mock_repo.get_speakers_with_conversation_count = AsyncMock(return_value=[])

        runner = CliRunner()
        result = runner.invoke(export_unclassified_speakers)

        assert result.exit_code == 0
        assert "対象の未分類Speakerはいません" in result.output

    @patch(f"{_DI_PATH}.get_container", side_effect=RuntimeError)
    @patch(f"{_DI_PATH}.init_container")
    def test_falls_back_to_init_container(
        self, mock_init: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_container = MagicMock()
        mock_init.return_value = mock_container
        mock_repo = _setup_repo_mock(mock_container)
        mock_repo.get_speakers_with_conversation_count = AsyncMock(return_value=[])

        runner = CliRunner()
        result = runner.invoke(export_unclassified_speakers)

        assert result.exit_code == 0
        mock_init.assert_called_once()
