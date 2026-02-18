"""kokkai stats コマンドのテスト."""

from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from src.domain.entities.speaker import Speaker
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.interfaces.cli.commands.kokkai.stats import stats


_DI_PATH = "src.infrastructure.di.container"


def _setup_repo_mock(mock_container: MagicMock) -> AsyncMock:
    mock_repo = AsyncMock(spec=SpeakerRepository)
    mock_container.repositories.speaker_repository.return_value = mock_repo
    return mock_repo


class TestStatsCommand:
    @patch(f"{_DI_PATH}.get_container")
    def test_stats_shows_match_rate(self, mock_get_container: MagicMock) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_repo = _setup_repo_mock(mock_container)
        mock_repo.get_speaker_politician_stats = AsyncMock(
            return_value={
                "total_speakers": 1000,
                "linked_speakers": 800,
                "unlinked_speakers": 200,
                "match_rate": 80.0,
            }
        )
        mock_repo.get_speakers_not_linked_to_politicians = AsyncMock(return_value=[])

        runner = CliRunner()
        result = runner.invoke(stats)

        assert result.exit_code == 0
        assert "1,000" in result.output
        assert "800" in result.output
        assert "80.0%" in result.output

    @patch(f"{_DI_PATH}.get_container")
    def test_stats_shows_unlinked_speakers(self, mock_get_container: MagicMock) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_repo = _setup_repo_mock(mock_container)
        mock_repo.get_speaker_politician_stats = AsyncMock(
            return_value={
                "total_speakers": 100,
                "linked_speakers": 50,
                "unlinked_speakers": 50,
                "match_rate": 50.0,
            }
        )
        speakers = [
            Speaker(name="山田太郎", political_party_name="自民党"),
            Speaker(name="鈴木花子"),
        ]
        mock_repo.get_speakers_not_linked_to_politicians = AsyncMock(
            return_value=speakers
        )

        runner = CliRunner()
        result = runner.invoke(stats)

        assert result.exit_code == 0
        assert "山田太郎" in result.output
        assert "[自民党]" in result.output
        assert "鈴木花子" in result.output

    @patch(f"{_DI_PATH}.get_container")
    def test_stats_respects_limit(self, mock_get_container: MagicMock) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_repo = _setup_repo_mock(mock_container)
        mock_repo.get_speaker_politician_stats = AsyncMock(
            return_value={
                "total_speakers": 10,
                "linked_speakers": 5,
                "unlinked_speakers": 5,
                "match_rate": 50.0,
            }
        )
        speakers = [Speaker(name=f"発言者{i}") for i in range(5)]
        mock_repo.get_speakers_not_linked_to_politicians = AsyncMock(
            return_value=speakers
        )

        runner = CliRunner()
        result = runner.invoke(stats, ["--limit", "2"])

        assert result.exit_code == 0
        assert "発言者0" in result.output
        assert "発言者1" in result.output
        assert "発言者2" not in result.output
        assert "上位2件" in result.output

    @patch(f"{_DI_PATH}.get_container")
    def test_stats_no_unlinked(self, mock_get_container: MagicMock) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_repo = _setup_repo_mock(mock_container)
        mock_repo.get_speaker_politician_stats = AsyncMock(
            return_value={
                "total_speakers": 100,
                "linked_speakers": 100,
                "unlinked_speakers": 0,
                "match_rate": 100.0,
            }
        )
        mock_repo.get_speakers_not_linked_to_politicians = AsyncMock(return_value=[])

        runner = CliRunner()
        result = runner.invoke(stats)

        assert result.exit_code == 0
        assert "未紐付け発言者はいません" in result.output

    @patch(f"{_DI_PATH}.get_container", side_effect=RuntimeError)
    @patch(f"{_DI_PATH}.init_container")
    def test_stats_falls_back_to_init_container(
        self, mock_init: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_container = MagicMock()
        mock_init.return_value = mock_container
        mock_repo = _setup_repo_mock(mock_container)
        mock_repo.get_speaker_politician_stats = AsyncMock(
            return_value={
                "total_speakers": 0,
                "linked_speakers": 0,
                "unlinked_speakers": 0,
                "match_rate": 0.0,
            }
        )
        mock_repo.get_speakers_not_linked_to_politicians = AsyncMock(return_value=[])

        runner = CliRunner()
        result = runner.invoke(stats)

        assert result.exit_code == 0
        mock_init.assert_called_once()
