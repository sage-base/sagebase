"""kokkai stats コマンドのテスト."""

import json

from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from src.domain.entities.speaker import Speaker
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.value_objects.speaker_classification_stats import (
    ClassificationCount,
    SpeakerClassificationStats,
)
from src.interfaces.cli.commands.kokkai.stats import stats


_DI_PATH = "src.infrastructure.di.container"

_DEFAULT_CLASSIFICATION_STATS = SpeakerClassificationStats(
    politician_linked=ClassificationCount(speaker_count=200, conversation_count=40000),
    government_official_linked=ClassificationCount(
        speaker_count=10, conversation_count=500
    ),
    unclassified=ClassificationCount(speaker_count=790, conversation_count=9500),
)


def _setup_repo_mock(mock_container: MagicMock) -> AsyncMock:
    mock_repo = AsyncMock(spec=SpeakerRepository)
    mock_container.repositories.speaker_repository.return_value = mock_repo
    # デフォルトの分類統計を設定（既存テストの互換性維持）
    mock_repo.get_speaker_classification_stats = AsyncMock(
        return_value=_DEFAULT_CLASSIFICATION_STATS
    )
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

    @patch(f"{_DI_PATH}.get_container")
    def test_stats_shows_classification_summary(
        self, mock_get_container: MagicMock
    ) -> None:
        """分類サマリが正しく表示される."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_repo = _setup_repo_mock(mock_container)
        mock_repo.get_speaker_politician_stats = AsyncMock(
            return_value={
                "total_speakers": 1000,
                "linked_speakers": 200,
                "unlinked_speakers": 800,
                "match_rate": 20.0,
            }
        )
        mock_repo.get_speakers_not_linked_to_politicians = AsyncMock(return_value=[])

        runner = CliRunner()
        result = runner.invoke(stats)

        assert result.exit_code == 0
        assert "Speaker分類サマリ" in result.output
        assert "politician紐付済" in result.output
        assert "government_official" in result.output
        assert "未分類" in result.output
        assert "身元特定率（発言ベース）: 81.0%" in result.output

    @patch(f"{_DI_PATH}.get_container")
    def test_stats_json_format(self, mock_get_container: MagicMock) -> None:
        """--format json で有効なJSONが出力される."""
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

        runner = CliRunner()
        result = runner.invoke(stats, ["--format", "json"])

        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert isinstance(parsed, dict)

    @patch(f"{_DI_PATH}.get_container")
    def test_stats_json_contains_classification(
        self, mock_get_container: MagicMock
    ) -> None:
        """JSON出力に分類データが含まれる."""
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

        runner = CliRunner()
        result = runner.invoke(stats, ["--format", "json"])

        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert "speaker_classification" in parsed
        classification = parsed["speaker_classification"]
        assert classification["total_speakers"] == 1000
        assert classification["identity_rate"] == 81.0
        assert "politician_linked" in classification
        assert "government_official_linked" in classification
        assert "unclassified" in classification

    @patch(f"{_DI_PATH}.get_container")
    def test_stats_classification_zero_conversations(
        self, mock_get_container: MagicMock
    ) -> None:
        """発言0件時に身元特定率0.0%."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_repo = _setup_repo_mock(mock_container)
        mock_repo.get_speaker_classification_stats = AsyncMock(
            return_value=SpeakerClassificationStats(
                politician_linked=ClassificationCount(
                    speaker_count=0, conversation_count=0
                ),
                government_official_linked=ClassificationCount(
                    speaker_count=0, conversation_count=0
                ),
                unclassified=ClassificationCount(
                    speaker_count=10, conversation_count=0
                ),
            )
        )
        mock_repo.get_speaker_politician_stats = AsyncMock(
            return_value={
                "total_speakers": 10,
                "linked_speakers": 0,
                "unlinked_speakers": 10,
                "match_rate": 0.0,
            }
        )
        mock_repo.get_speakers_not_linked_to_politicians = AsyncMock(return_value=[])

        runner = CliRunner()
        result = runner.invoke(stats)

        assert result.exit_code == 0
        assert "身元特定率（発言ベース）: 0.0%" in result.output

    @patch(f"{_DI_PATH}.get_container")
    def test_stats_classification_zero_speakers(
        self, mock_get_container: MagicMock
    ) -> None:
        """Speaker0件時にゼロ除算せず0.0%が表示される."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_repo = _setup_repo_mock(mock_container)
        mock_repo.get_speaker_classification_stats = AsyncMock(
            return_value=SpeakerClassificationStats(
                politician_linked=ClassificationCount(
                    speaker_count=0, conversation_count=0
                ),
                government_official_linked=ClassificationCount(
                    speaker_count=0, conversation_count=0
                ),
                unclassified=ClassificationCount(speaker_count=0, conversation_count=0),
            )
        )
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
        assert "全Speaker:              0" in result.output
        assert "身元特定率（発言ベース）: 0.0%" in result.output
