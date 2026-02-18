"""kokkai import コマンドのテスト."""

from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from src.application.dtos.kokkai_speech_dto import (
    BatchImportKokkaiSpeechesInputDTO,
    BatchImportKokkaiSpeechesOutputDTO,
    KokkaiMeetingDTO,
    SessionProgress,
)
from src.application.usecases.batch_import_kokkai_speeches_usecase import (
    BatchImportKokkaiSpeechesUseCase,
)
from src.interfaces.cli.commands.kokkai.import_speeches import import_speeches


_DI_PATH = "src.infrastructure.di.container"


def _make_meeting(session: int = 1, issue: str = "第1号") -> KokkaiMeetingDTO:
    return KokkaiMeetingDTO(
        issue_id=f"issue_{session}_{issue}",
        session=session,
        name_of_house="衆議院",
        name_of_meeting="本会議",
        issue=issue,
        date="2024-01-15",
        meeting_url="https://example.com",
    )


def _make_output(
    meetings_found: int = 5,
    meetings_processed: int = 5,
    speeches_imported: int = 100,
) -> BatchImportKokkaiSpeechesOutputDTO:
    return BatchImportKokkaiSpeechesOutputDTO(
        total_meetings_found=meetings_found,
        total_meetings_processed=meetings_processed,
        total_speeches_imported=speeches_imported,
        total_speeches_skipped=10,
        total_speakers_created=3,
        session_progress=[
            SessionProgress(
                session=1,
                meetings_processed=meetings_processed,
                speeches_imported=speeches_imported,
            )
        ],
    )


def _setup_usecase_mock(
    mock_container: MagicMock,
) -> AsyncMock:
    mock_usecase = AsyncMock(spec=BatchImportKokkaiSpeechesUseCase)
    mock_container.use_cases.batch_import_kokkai_speeches_usecase.return_value = (
        mock_usecase
    )
    return mock_usecase


class TestImportSpeechesCommand:
    @patch(f"{_DI_PATH}.get_container")
    def test_dry_run_shows_meetings(self, mock_get_container: MagicMock) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_usecase = _setup_usecase_mock(mock_container)
        mock_usecase.fetch_target_meetings = AsyncMock(
            return_value=[_make_meeting(1), _make_meeting(2)]
        )

        runner = CliRunner()
        result = runner.invoke(import_speeches, ["--dry-run"])

        assert result.exit_code == 0
        assert "ドライラン" in result.output
        assert "合計: 2 件" in result.output
        mock_usecase.execute.assert_not_called()

    @patch(f"{_DI_PATH}.get_container")
    def test_dry_run_no_meetings(self, mock_get_container: MagicMock) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_usecase = _setup_usecase_mock(mock_container)
        mock_usecase.fetch_target_meetings = AsyncMock(return_value=[])

        runner = CliRunner()
        result = runner.invoke(import_speeches, ["--dry-run"])

        assert result.exit_code == 0
        assert "対象会議が見つかりません" in result.output

    @patch(f"{_DI_PATH}.get_container")
    def test_import_executes_and_shows_summary(
        self, mock_get_container: MagicMock
    ) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_usecase = _setup_usecase_mock(mock_container)
        mock_usecase.execute = AsyncMock(return_value=_make_output())

        runner = CliRunner()
        result = runner.invoke(
            import_speeches,
            ["--session-from", "1", "--session-to", "1"],
        )

        assert result.exit_code == 0
        assert "インポート結果" in result.output
        assert "100" in result.output
        mock_usecase.execute.assert_called_once()
        input_dto = mock_usecase.execute.call_args[0][0]
        assert isinstance(input_dto, BatchImportKokkaiSpeechesInputDTO)
        assert input_dto.session_from == 1
        assert input_dto.session_to == 1

    @patch(f"{_DI_PATH}.get_container")
    def test_import_with_options_maps_to_dto(
        self, mock_get_container: MagicMock
    ) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_usecase = _setup_usecase_mock(mock_container)
        mock_usecase.execute = AsyncMock(return_value=_make_output())

        runner = CliRunner()
        result = runner.invoke(
            import_speeches,
            [
                "--session-from",
                "1",
                "--session-to",
                "3",
                "--name-of-house",
                "衆議院",
                "--name-of-meeting",
                "本会議",
                "--sleep",
                "0.5",
            ],
        )

        assert result.exit_code == 0
        input_dto = mock_usecase.execute.call_args[0][0]
        assert isinstance(input_dto, BatchImportKokkaiSpeechesInputDTO)
        assert input_dto.session_from == 1
        assert input_dto.session_to == 3
        assert input_dto.name_of_house == "衆議院"
        assert input_dto.name_of_meeting == "本会議"
        assert input_dto.sleep_interval == 0.5

    @patch(f"{_DI_PATH}.get_container")
    def test_import_passes_progress_callback(
        self, mock_get_container: MagicMock
    ) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_usecase = _setup_usecase_mock(mock_container)
        mock_usecase.execute = AsyncMock(return_value=_make_output())

        runner = CliRunner()
        runner.invoke(import_speeches, [])

        call_kwargs = mock_usecase.execute.call_args[1]
        assert "progress_callback" in call_kwargs
        assert callable(call_kwargs["progress_callback"])

    @patch(f"{_DI_PATH}.get_container")
    def test_import_shows_errors(self, mock_get_container: MagicMock) -> None:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_usecase = _setup_usecase_mock(mock_container)
        output = _make_output()
        output.errors = ["テストエラー1", "テストエラー2"]
        mock_usecase.execute = AsyncMock(return_value=output)

        runner = CliRunner()
        result = runner.invoke(import_speeches, [])

        assert result.exit_code == 0
        assert "エラー" in result.output
        assert "テストエラー1" in result.output

    @patch(f"{_DI_PATH}.get_container", side_effect=RuntimeError)
    @patch(f"{_DI_PATH}.init_container")
    def test_import_falls_back_to_init_container(
        self, mock_init: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_container = MagicMock()
        mock_init.return_value = mock_container
        mock_usecase = _setup_usecase_mock(mock_container)
        mock_usecase.fetch_target_meetings = AsyncMock(return_value=[])

        runner = CliRunner()
        result = runner.invoke(import_speeches, ["--dry-run"])

        assert result.exit_code == 0
        mock_init.assert_called_once()
