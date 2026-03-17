"""kokkai link-officials コマンドのテスト."""

from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from src.application.usecases.batch_link_speakers_to_government_officials_usecase import (  # noqa: E501
    BatchLinkDetail,
    BatchLinkOutputDto,
    BatchLinkSpeakersToGovernmentOfficialsUseCase,
)
from src.interfaces.cli.commands.kokkai.link_officials import link_officials


_DI_PATH = "src.interfaces.cli.base"


def _make_output(
    linked_count: int = 0,
    skipped_count: int = 0,
    details: list[BatchLinkDetail] | None = None,
) -> BatchLinkOutputDto:
    return BatchLinkOutputDto(
        linked_count=linked_count,
        skipped_count=skipped_count,
        details=details or [],
    )


def _make_detail(
    official_id: int = 1,
    official_name: str = "山田太郎",
    speaker_id: int = 10,
    speaker_name: str = "山田太郞",
    normalized_name: str = "山田太郎",
) -> BatchLinkDetail:
    return BatchLinkDetail(
        government_official_id=official_id,
        government_official_name=official_name,
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        normalized_name=normalized_name,
    )


def _setup_usecase_mock(mock_container: MagicMock) -> AsyncMock:
    mock_usecase = AsyncMock(spec=BatchLinkSpeakersToGovernmentOfficialsUseCase)
    mock_container.use_cases.batch_link_speakers_to_government_officials_usecase.return_value = (  # noqa: E501
        mock_usecase
    )
    return mock_usecase


class TestLinkOfficialsCommand:
    @patch(f"{_DI_PATH}.get_container")
    def test_dry_run_shows_candidates(self, mock_get_container: MagicMock) -> None:
        """dry-runモードで紐付け候補が表示されること."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_usecase = _setup_usecase_mock(mock_container)
        mock_usecase.execute = AsyncMock(
            return_value=_make_output(
                linked_count=2,
                skipped_count=1,
                details=[
                    _make_detail(),
                    _make_detail(
                        official_id=2,
                        official_name="鈴木花子",
                        speaker_id=20,
                        speaker_name="鈴木花子",
                        normalized_name="鈴木花子",
                    ),
                ],
            )
        )

        runner = CliRunner()
        result = runner.invoke(link_officials, ["--dry-run"])

        assert result.exit_code == 0
        assert "ドライラン" in result.output
        assert "紐付け結果" in result.output
        assert "紐付け数:   2" in result.output
        assert "スキップ数: 1" in result.output
        assert "山田太郎" in result.output
        assert "山田太郞" in result.output
        assert "鈴木花子" in result.output
        mock_usecase.execute.assert_called_once_with(dry_run=True)

    @patch(f"{_DI_PATH}.get_container")
    def test_execute_calls_usecase(self, mock_get_container: MagicMock) -> None:
        """本実行でUseCaseが呼ばれること."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_usecase = _setup_usecase_mock(mock_container)
        mock_usecase.execute = AsyncMock(
            return_value=_make_output(linked_count=3, skipped_count=5)
        )

        runner = CliRunner()
        result = runner.invoke(link_officials, [])

        assert result.exit_code == 0
        assert "ドライラン" not in result.output
        mock_usecase.execute.assert_called_once_with(dry_run=False)

    @patch(f"{_DI_PATH}.get_container")
    def test_summary_displayed_correctly(self, mock_get_container: MagicMock) -> None:
        """結果サマリーが正しく表示されること."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_usecase = _setup_usecase_mock(mock_container)
        mock_usecase.execute = AsyncMock(
            return_value=_make_output(
                linked_count=5,
                skipped_count=3,
                details=[_make_detail()],
            )
        )

        runner = CliRunner()
        result = runner.invoke(link_officials, [])

        assert result.exit_code == 0
        assert "紐付け数:   5" in result.output
        assert "スキップ数: 3" in result.output
        assert "紐付け詳細" in result.output
        assert "政府関係者: 山田太郎" in result.output
        assert "発言者: 山田太郞" in result.output
        assert "正規化名: 山田太郎" in result.output

    @patch(f"{_DI_PATH}.get_container")
    def test_no_details_hides_detail_section(
        self, mock_get_container: MagicMock
    ) -> None:
        """紐付け候補がない場合、詳細セクションが表示されないこと."""
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_usecase = _setup_usecase_mock(mock_container)
        mock_usecase.execute = AsyncMock(
            return_value=_make_output(linked_count=0, skipped_count=10)
        )

        runner = CliRunner()
        result = runner.invoke(link_officials, [])

        assert result.exit_code == 0
        assert "紐付け詳細" not in result.output

    @patch(f"{_DI_PATH}.get_container", side_effect=RuntimeError)
    @patch(f"{_DI_PATH}.init_container")
    def test_falls_back_to_init_container(
        self, mock_init: MagicMock, mock_get: MagicMock
    ) -> None:
        """get_container失敗時にinit_containerにフォールバックすること."""
        mock_container = MagicMock()
        mock_init.return_value = mock_container
        mock_usecase = _setup_usecase_mock(mock_container)
        mock_usecase.execute = AsyncMock(
            return_value=_make_output(linked_count=0, skipped_count=0)
        )

        runner = CliRunner()
        result = runner.invoke(link_officials, [])

        assert result.exit_code == 0
        mock_init.assert_called_once()
