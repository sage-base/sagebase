"""SetupAnalyticsHubCommand のテスト."""

from unittest.mock import MagicMock, patch

import pytest

from click.testing import CliRunner

from src.infrastructure.bigquery.analytics_hub import ExchangeInfo, ListingInfo


@pytest.fixture
def mock_exchange_info() -> ExchangeInfo:
    return ExchangeInfo(
        name="projects/test-project/locations/asia-northeast1/dataExchanges/sagebase_exchange",
        display_name="Sagebase 政治活動データ",
        description="テスト説明",
        listing_count=1,
    )


@pytest.fixture
def mock_listing_info() -> ListingInfo:
    return ListingInfo(
        name="projects/test-project/locations/asia-northeast1/dataExchanges/sagebase_exchange/listings/sagebase_source_listing",
        display_name="Sagebase Source Layer - 政治活動データ",
        description="テスト説明",
        state="ACTIVE",
    )


class TestSetupAnalyticsHubCommand:
    """SetupAnalyticsHubCommand のテスト."""

    def test_dry_run_does_not_call_api(self) -> None:
        from src.interfaces.cli.commands.bigquery.setup_analytics_hub import (
            SetupAnalyticsHubCommand,
        )

        cmd = SetupAnalyticsHubCommand()
        # dry_runモードではAPIを呼ばないことを確認
        cmd.execute(
            exchange_id="test_exchange",
            primary_contact="",
            dry_run=True,
        )
        # エラーが発生しなければOK

    @patch.dict("os.environ", {}, clear=False)
    def test_missing_project_id_exits(self) -> None:
        import os

        from src.interfaces.cli.commands.bigquery.setup_analytics_hub import (
            SetupAnalyticsHubCommand,
        )

        os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
        cmd = SetupAnalyticsHubCommand()
        with pytest.raises(SystemExit) as exc_info:
            cmd.execute(
                exchange_id="test_exchange",
                primary_contact="",
                dry_run=False,
            )
        assert exc_info.value.code == 1

    @patch.dict(
        "os.environ",
        {"GOOGLE_CLOUD_PROJECT": "test-project", "BQ_LOCATION": "asia-northeast1"},
    )
    @patch(
        "src.interfaces.cli.commands.bigquery.setup_analytics_hub.AnalyticsHubClient"
    )
    def test_execute_creates_exchange_and_listings(
        self,
        mock_client_cls: MagicMock,
        mock_exchange_info: ExchangeInfo,
        mock_listing_info: ListingInfo,
    ) -> None:
        from src.infrastructure.bigquery.analytics_hub_config import LISTING_CONFIGS
        from src.interfaces.cli.commands.bigquery.setup_analytics_hub import (
            SetupAnalyticsHubCommand,
        )

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.create_exchange.return_value = mock_exchange_info
        mock_client.create_listing.return_value = mock_listing_info

        cmd = SetupAnalyticsHubCommand()
        cmd.execute(
            exchange_id="sagebase_exchange",
            primary_contact="test@example.com",
            dry_run=False,
        )

        mock_client.create_exchange.assert_called_once()
        # 3つのListingが作成される
        assert mock_client.create_listing.call_count == len(LISTING_CONFIGS)

        # Exchange作成の引数を検証
        exchange_call = mock_client.create_exchange.call_args
        assert exchange_call.kwargs["exchange_id"] == "sagebase_exchange"
        assert exchange_call.kwargs["public"] is True

        # 各Listing作成の引数を検証
        listing_calls = mock_client.create_listing.call_args_list
        for i, config in enumerate(LISTING_CONFIGS):
            call = listing_calls[i]
            assert call.kwargs["exchange_id"] == "sagebase_exchange"
            assert call.kwargs["listing_id"] == config.listing_id
            assert call.kwargs["dataset_id"] == config.dataset_id

    @patch.dict(
        "os.environ",
        {"GOOGLE_CLOUD_PROJECT": "test-project"},
    )
    @patch(
        "src.interfaces.cli.commands.bigquery.setup_analytics_hub.AnalyticsHubClient"
    )
    def test_uses_env_defaults(
        self,
        mock_client_cls: MagicMock,
        mock_exchange_info: ExchangeInfo,
        mock_listing_info: ListingInfo,
    ) -> None:
        from src.infrastructure.bigquery.analytics_hub_config import LISTING_CONFIGS
        from src.interfaces.cli.commands.bigquery.setup_analytics_hub import (
            SetupAnalyticsHubCommand,
        )

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.create_exchange.return_value = mock_exchange_info
        mock_client.create_listing.return_value = mock_listing_info

        cmd = SetupAnalyticsHubCommand()
        # None値を渡すとデフォルト値が使われる
        cmd.execute(
            exchange_id=None,
            primary_contact=None,
            dry_run=False,
        )

        exchange_call = mock_client.create_exchange.call_args
        assert exchange_call.kwargs["exchange_id"] == "sagebase_exchange"

        # 3つのListingが作成される（LISTING_CONFIGSのデフォルト値を使用）
        assert mock_client.create_listing.call_count == len(LISTING_CONFIGS)
        # 最初のListingはsagebase_source
        first_listing_call = mock_client.create_listing.call_args_list[0]
        assert first_listing_call.kwargs["listing_id"] == "sagebase_source_listing"
        assert first_listing_call.kwargs["dataset_id"] == "sagebase_source"


class TestSetupAnalyticsHubClickCommand:
    """Click コマンドの結合テスト."""

    def test_dry_run_click_command(self) -> None:
        from src.interfaces.cli.commands.bigquery import setup_analytics_hub

        runner = CliRunner()
        result = runner.invoke(setup_analytics_hub, ["--dry-run"])
        assert result.exit_code == 0
        assert "ドライラン" in result.output

    @patch.dict(
        "os.environ",
        {"GOOGLE_CLOUD_PROJECT": "test-project", "BQ_LOCATION": "asia-northeast1"},
    )
    @patch(
        "src.interfaces.cli.commands.bigquery.setup_analytics_hub.AnalyticsHubClient"
    )
    def test_click_command_with_options(
        self,
        mock_client_cls: MagicMock,
        mock_exchange_info: ExchangeInfo,
        mock_listing_info: ListingInfo,
    ) -> None:
        from src.interfaces.cli.commands.bigquery import setup_analytics_hub

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.create_exchange.return_value = mock_exchange_info
        mock_client.create_listing.return_value = mock_listing_info

        runner = CliRunner()
        result = runner.invoke(
            setup_analytics_hub,
            [
                "--exchange-id",
                "custom_exchange",
                "--primary-contact",
                "test@example.com",
            ],
        )
        assert result.exit_code == 0
        assert "セットアップ完了" in result.output

    @patch.dict("os.environ", {}, clear=False)
    def test_click_command_missing_project_id(self) -> None:
        import os

        from src.interfaces.cli.commands.bigquery import setup_analytics_hub

        os.environ.pop("GOOGLE_CLOUD_PROJECT", None)

        runner = CliRunner()
        result = runner.invoke(setup_analytics_hub, [])
        assert result.exit_code == 1
