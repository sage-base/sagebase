"""kokkai bulk-match-speakers コマンドのテスト."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from src.application.dtos.match_meeting_speakers_dto import (
    MatchMeetingSpeakersOutputDTO,
)
from src.domain.entities.election import Election
from src.domain.entities.meeting import Meeting
from src.interfaces.cli.commands.kokkai.bulk_match_speakers import bulk_match_speakers


_DI_PATH = "src.infrastructure.di.container"


def _make_meetings(count: int = 3) -> list[Meeting]:
    return [
        Meeting(
            id=i,
            conference_id=10,
            date=date(2024, 1, i),
            name=f"衆議院本会議 第{i}号",
        )
        for i in range(1, count + 1)
    ]


def _make_output(
    matched: int = 2, total: int = 5, skipped: int = 1
) -> MatchMeetingSpeakersOutputDTO:
    return MatchMeetingSpeakersOutputDTO(
        success=True,
        message=f"{total}件の発言者を分析し、{matched}件をマッチングしました",
        total_speakers=total,
        matched_count=matched,
        skipped_count=skipped,
    )


def _make_elections() -> list[Election]:
    return [
        Election(
            governing_body_id=1,
            term_number=49,
            election_date=date(2021, 10, 31),
            election_type="衆議院議員総選挙",
            id=1,
        ),
    ]


def _setup_mocks(
    mock_container: MagicMock,
    meetings: list[Meeting] | None = None,
    output: MatchMeetingSpeakersOutputDTO | None = None,
) -> tuple[AsyncMock, AsyncMock]:
    mock_meeting_repo = AsyncMock()
    mock_meeting_repo.get_by_chamber_and_date_range = AsyncMock(
        return_value=meetings or []
    )
    mock_container.repositories.meeting_repository.return_value = mock_meeting_repo

    mock_election_repo = AsyncMock()
    mock_election_repo.get_by_governing_body = AsyncMock(return_value=_make_elections())
    mock_container.repositories.election_repository.return_value = mock_election_repo

    mock_usecase = AsyncMock()
    mock_usecase.execute = AsyncMock(return_value=output or _make_output())
    mock_container.use_cases.match_meeting_speakers_usecase.return_value = mock_usecase

    return mock_meeting_repo, mock_usecase


class TestBulkMatchSpeakersCommand:
    @patch(f"{_DI_PATH}.get_container")
    def test_dry_run_shows_meetings(self, mock_get_container: MagicMock) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        meetings = _make_meetings(3)
        mock_meeting_repo, mock_usecase = _setup_mocks(
            mock_container, meetings=meetings
        )

        runner = CliRunner()
        result = runner.invoke(
            bulk_match_speakers,
            [
                "--chamber",
                "衆議院",
                "--date-from",
                "2024-01-01",
                "--date-to",
                "2024-12-31",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "ドライラン" in result.output
        assert "合計: 3 件" in result.output
        mock_usecase.execute.assert_not_called()

    @patch(f"{_DI_PATH}.get_container")
    def test_dry_run_no_meetings(self, mock_get_container: MagicMock) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        _setup_mocks(mock_container, meetings=[])

        runner = CliRunner()
        result = runner.invoke(
            bulk_match_speakers,
            [
                "--chamber",
                "衆議院",
                "--date-from",
                "2024-01-01",
                "--date-to",
                "2024-12-31",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "対象会議が見つかりません" in result.output

    @patch(f"{_DI_PATH}.get_container")
    def test_normal_execution(self, mock_get_container: MagicMock) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        meetings = _make_meetings(2)
        _, mock_usecase = _setup_mocks(
            mock_container, meetings=meetings, output=_make_output(matched=3, total=5)
        )

        runner = CliRunner()
        result = runner.invoke(
            bulk_match_speakers,
            [
                "--chamber",
                "衆議院",
                "--date-from",
                "2024-01-01",
                "--date-to",
                "2024-12-31",
            ],
        )

        assert result.exit_code == 0
        assert "バルクマッチング開始" in result.output
        assert "結果サマリー" in result.output
        assert "回次別マッチ率" in result.output
        assert "第49回" in result.output
        assert mock_usecase.execute.call_count == 2

    @patch(f"{_DI_PATH}.get_container")
    def test_empty_result(self, mock_get_container: MagicMock) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        meetings = _make_meetings(1)
        _, mock_usecase = _setup_mocks(
            mock_container,
            meetings=meetings,
            output=MatchMeetingSpeakersOutputDTO(
                success=True,
                message="マッチング対象の発言者がありません",
                total_speakers=0,
                matched_count=0,
                skipped_count=0,
            ),
        )

        runner = CliRunner()
        result = runner.invoke(
            bulk_match_speakers,
            [
                "--chamber",
                "参議院",
                "--date-from",
                "2024-01-01",
                "--date-to",
                "2024-12-31",
            ],
        )

        assert result.exit_code == 0
        assert "結果サマリー" in result.output

    @patch(f"{_DI_PATH}.get_container", side_effect=RuntimeError)
    @patch(f"{_DI_PATH}.init_container")
    def test_falls_back_to_init_container(
        self, mock_init: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_container = MagicMock()
        mock_init.return_value = mock_container
        _setup_mocks(mock_container, meetings=[])

        runner = CliRunner()
        result = runner.invoke(
            bulk_match_speakers,
            [
                "--chamber",
                "衆議院",
                "--date-from",
                "2024-01-01",
                "--date-to",
                "2024-12-31",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        mock_init.assert_called_once()

    @patch(f"{_DI_PATH}.get_container")
    def test_confidence_threshold_option(self, mock_get_container: MagicMock) -> None:
        """--confidence-threshold が DTO に渡される."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        meetings = _make_meetings(1)
        _, mock_usecase = _setup_mocks(
            mock_container, meetings=meetings, output=_make_output()
        )

        runner = CliRunner()
        result = runner.invoke(
            bulk_match_speakers,
            [
                "--chamber",
                "衆議院",
                "--date-from",
                "2024-01-01",
                "--date-to",
                "2024-12-31",
                "--confidence-threshold",
                "0.95",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_usecase.execute.call_args
        assert call_args[0][0].confidence_threshold == 0.95

    @patch(f"{_DI_PATH}.get_container")
    def test_usecase_exception_continues_processing(
        self, mock_get_container: MagicMock
    ) -> None:
        """1会議で例外が発生しても処理が継続される."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        meetings = _make_meetings(2)
        _, mock_usecase = _setup_mocks(mock_container, meetings=meetings)
        # 1回目は例外、2回目は正常
        mock_usecase.execute = AsyncMock(
            side_effect=[RuntimeError("DB接続エラー"), _make_output()]
        )

        runner = CliRunner()
        result = runner.invoke(
            bulk_match_speakers,
            [
                "--chamber",
                "衆議院",
                "--date-from",
                "2024-01-01",
                "--date-to",
                "2024-12-31",
            ],
        )

        assert result.exit_code == 0
        assert "エラー" in result.output
        assert "結果サマリー" in result.output
        assert mock_usecase.execute.call_count == 2
