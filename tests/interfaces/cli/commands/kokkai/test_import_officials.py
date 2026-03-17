"""kokkai import-officials コマンドのテスト."""

from unittest.mock import AsyncMock, MagicMock

from click.testing import CliRunner

from src.application.dtos.government_official_dto import (
    ImportGovernmentOfficialsCsvInputDto,
    ImportGovernmentOfficialsCsvOutputDto,
)
from src.application.usecases.import_government_officials_csv_usecase import (
    ImportGovernmentOfficialsCsvUseCase,
)
from src.interfaces.cli.commands.kokkai.import_officials import import_officials


_VALID_CSV = (
    "speaker_name,representative_speaker_id,organization,position,notes\n"
    "山田太郎,1,内閣府,大臣,テスト備考\n"
    "鈴木花子,2,総務省,副大臣,\n"
)

_VALID_CSV_NO_NOTES = (
    "speaker_name,representative_speaker_id,organization,position\n"
    "山田太郎,1,内閣府,大臣\n"
)


def _make_output(
    created_officials: int = 2,
    created_positions: int = 2,
    linked_speakers: int = 2,
) -> ImportGovernmentOfficialsCsvOutputDto:
    return ImportGovernmentOfficialsCsvOutputDto(
        created_officials_count=created_officials,
        created_positions_count=created_positions,
        linked_speakers_count=linked_speakers,
    )


def _setup_usecase_mock(mock_container: MagicMock) -> AsyncMock:
    mock_usecase = AsyncMock(spec=ImportGovernmentOfficialsCsvUseCase)
    mock_container.use_cases.import_government_officials_csv_usecase.return_value = (
        mock_usecase
    )
    return mock_usecase


class TestImportOfficialsCommand:
    def test_import_csv_executes_and_shows_summary(
        self, mock_container: MagicMock
    ) -> None:
        mock_usecase = _setup_usecase_mock(mock_container)
        mock_usecase.execute = AsyncMock(return_value=_make_output())

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("officials.csv", "w") as f:
                f.write(_VALID_CSV)
            result = runner.invoke(import_officials, ["--csv", "officials.csv"])

        assert result.exit_code == 0
        assert "インポート結果" in result.output
        assert "2" in result.output
        mock_usecase.execute.assert_called_once()
        input_dto = mock_usecase.execute.call_args[0][0]
        assert isinstance(input_dto, ImportGovernmentOfficialsCsvInputDto)
        assert len(input_dto.rows) == 2
        assert input_dto.rows[0].speaker_name == "山田太郎"
        assert input_dto.rows[0].representative_speaker_id == 1
        assert input_dto.rows[0].notes == "テスト備考"
        assert input_dto.rows[1].notes is None
        assert input_dto.dry_run is False

    def test_dry_run_flag_passed_to_usecase(self, mock_container: MagicMock) -> None:
        mock_usecase = _setup_usecase_mock(mock_container)
        mock_usecase.execute = AsyncMock(return_value=_make_output())

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("officials.csv", "w") as f:
                f.write(_VALID_CSV)
            result = runner.invoke(
                import_officials, ["--csv", "officials.csv", "--dry-run"]
            )

        assert result.exit_code == 0
        assert "ドライラン" in result.output
        input_dto = mock_usecase.execute.call_args[0][0]
        assert input_dto.dry_run is True

    def test_file_not_found(self) -> None:
        runner = CliRunner()
        result = runner.invoke(import_officials, ["--csv", "nonexistent.csv"])

        assert result.exit_code != 0

    def test_missing_required_columns(self, mock_container: MagicMock) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("bad.csv", "w") as f:
                f.write("speaker_name,organization\n山田太郎,内閣府\n")
            result = runner.invoke(import_officials, ["--csv", "bad.csv"])

        assert result.exit_code != 0
        assert "必須カラム" in result.output

    def test_empty_csv_no_data_rows(self, mock_container: MagicMock) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("empty.csv", "w") as f:
                f.write(
                    "speaker_name,representative_speaker_id,organization,position\n"
                )
            result = runner.invoke(import_officials, ["--csv", "empty.csv"])

        assert result.exit_code == 0
        assert "データ行がありません" in result.output

    def test_csv_without_notes_column(self, mock_container: MagicMock) -> None:
        mock_usecase = _setup_usecase_mock(mock_container)
        mock_usecase.execute = AsyncMock(return_value=_make_output(1, 1, 1))

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("officials.csv", "w") as f:
                f.write(_VALID_CSV_NO_NOTES)
            result = runner.invoke(import_officials, ["--csv", "officials.csv"])

        assert result.exit_code == 0
        input_dto = mock_usecase.execute.call_args[0][0]
        assert input_dto.rows[0].notes is None

    def test_shows_errors_from_usecase(self, mock_container: MagicMock) -> None:
        mock_usecase = _setup_usecase_mock(mock_container)
        output = _make_output()
        output.errors = ["テストエラー1", "テストエラー2"]
        mock_usecase.execute = AsyncMock(return_value=output)

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("officials.csv", "w") as f:
                f.write(_VALID_CSV)
            result = runner.invoke(import_officials, ["--csv", "officials.csv"])

        assert result.exit_code == 0
        assert "エラー" in result.output
        assert "テストエラー1" in result.output

    def test_invalid_representative_speaker_id(self) -> None:
        csv_data = (
            "speaker_name,representative_speaker_id,organization,position\n"
            "山田太郎,abc,内閣府,大臣\n"
        )
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("bad_id.csv", "w") as f:
                f.write(csv_data)
            result = runner.invoke(import_officials, ["--csv", "bad_id.csv"])

        assert result.exit_code != 0
        assert "整数ではありません" in result.output
        assert "abc" in result.output
