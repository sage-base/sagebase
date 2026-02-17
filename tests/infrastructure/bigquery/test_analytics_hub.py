"""Analytics Hubクライアントのテスト."""

from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.bigquery.analytics_hub import ExchangeInfo, ListingInfo
from src.infrastructure.exceptions import AuthenticationError, StorageError


@pytest.fixture
def mock_exchange() -> MagicMock:
    """モックExchangeオブジェクトを返す."""
    exchange = MagicMock()
    exchange.name = (
        "projects/test-project/locations/asia-northeast1/dataExchanges/test_exchange"
    )
    exchange.display_name = "Test Exchange"
    exchange.description = "テスト用Exchange"
    exchange.listing_count = 1
    return exchange


@pytest.fixture
def mock_listing() -> MagicMock:
    """モックListingオブジェクトを返す."""
    listing = MagicMock()
    listing.name = (
        "projects/test-project/locations/asia-northeast1"
        "/dataExchanges/test_exchange/listings/test_listing"
    )
    listing.display_name = "Test Listing"
    listing.description = "テスト用Listing"
    listing.state.name = "ACTIVE"
    return listing


class TestAnalyticsHubClientInit:
    """AnalyticsHubClient初期化テスト."""

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_init_success(self, mock_client_class: MagicMock) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        client = AnalyticsHubClient(
            project_id="test-project",
            location="asia-northeast1",
        )
        assert client.project_id == "test-project"
        assert client.location == "asia-northeast1"
        mock_client_class.assert_called_once()

    @patch("src.infrastructure.bigquery.analytics_hub.HAS_ANALYTICSHUB", False)
    def test_init_raises_when_library_not_installed(self) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        with pytest.raises(StorageError, match="not installed"):
            AnalyticsHubClient(project_id="test-project")

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_init_raises_on_auth_error(self, mock_client_class: MagicMock) -> None:
        from google.auth.exceptions import RefreshError

        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.side_effect = RefreshError("token expired")

        with pytest.raises(AuthenticationError):
            AnalyticsHubClient(project_id="test-project")

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_init_raises_on_general_error(self, mock_client_class: MagicMock) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.side_effect = RuntimeError("unexpected")

        with pytest.raises(StorageError, match="Failed to initialize"):
            AnalyticsHubClient(project_id="test-project")


class TestCreateExchange:
    """create_exchange テスト."""

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_create_exchange_success(
        self, mock_client_class: MagicMock, mock_exchange: MagicMock
    ) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.return_value.create_data_exchange.return_value = mock_exchange

        client = AnalyticsHubClient(project_id="test-project")
        result = client.create_exchange(
            exchange_id="test_exchange",
            display_name="Test Exchange",
            description="テスト用Exchange",
        )

        assert isinstance(result, ExchangeInfo)
        assert result.display_name == "Test Exchange"
        assert result.description == "テスト用Exchange"

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_create_exchange_already_exists(
        self, mock_client_class: MagicMock, mock_exchange: MagicMock
    ) -> None:
        from google.api_core.exceptions import AlreadyExists

        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_instance = mock_client_class.return_value
        mock_instance.create_data_exchange.side_effect = AlreadyExists("exists")
        mock_instance.get_data_exchange.return_value = mock_exchange

        client = AnalyticsHubClient(project_id="test-project")
        result = client.create_exchange(
            exchange_id="test_exchange",
            display_name="Test Exchange",
        )

        assert isinstance(result, ExchangeInfo)
        assert result.display_name == "Test Exchange"

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_create_exchange_permission_error(
        self, mock_client_class: MagicMock
    ) -> None:
        from google.api_core.exceptions import Forbidden

        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.return_value.create_data_exchange.side_effect = Forbidden(
            "denied"
        )

        client = AnalyticsHubClient(project_id="test-project")
        with pytest.raises(StorageError, match="Permission denied"):
            client.create_exchange(
                exchange_id="test_exchange",
                display_name="Test Exchange",
            )

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_create_exchange_private(
        self, mock_client_class: MagicMock, mock_exchange: MagicMock
    ) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.return_value.create_data_exchange.return_value = mock_exchange

        client = AnalyticsHubClient(project_id="test-project")
        client.create_exchange(
            exchange_id="test_exchange",
            display_name="Test Exchange",
            public=False,
        )

        call_args = mock_client_class.return_value.create_data_exchange.call_args
        request = call_args.kwargs["request"]
        # DISCOVERY_TYPE_PRIVATE = 1
        assert request.data_exchange.discovery_type == 1

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_create_exchange_general_error(self, mock_client_class: MagicMock) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.return_value.create_data_exchange.side_effect = RuntimeError(
            "unexpected"
        )

        client = AnalyticsHubClient(project_id="test-project")
        with pytest.raises(StorageError, match="Failed to create exchange"):
            client.create_exchange(
                exchange_id="test_exchange",
                display_name="Test Exchange",
            )


class TestGetExchange:
    """get_exchange テスト."""

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_get_exchange_success(
        self, mock_client_class: MagicMock, mock_exchange: MagicMock
    ) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.return_value.get_data_exchange.return_value = mock_exchange

        client = AnalyticsHubClient(project_id="test-project")
        result = client.get_exchange("test_exchange")

        assert isinstance(result, ExchangeInfo)
        assert result.display_name == "Test Exchange"
        assert result.listing_count == 1

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_get_exchange_not_found(self, mock_client_class: MagicMock) -> None:
        from google.api_core.exceptions import NotFound

        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.return_value.get_data_exchange.side_effect = NotFound(
            "not found"
        )

        client = AnalyticsHubClient(project_id="test-project")
        with pytest.raises(StorageError, match="not found"):
            client.get_exchange("test_exchange")

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_get_exchange_permission_error(self, mock_client_class: MagicMock) -> None:
        from google.api_core.exceptions import Forbidden

        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.return_value.get_data_exchange.side_effect = Forbidden(
            "denied"
        )

        client = AnalyticsHubClient(project_id="test-project")
        with pytest.raises(StorageError, match="Permission denied"):
            client.get_exchange("test_exchange")

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_get_exchange_general_error(self, mock_client_class: MagicMock) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.return_value.get_data_exchange.side_effect = RuntimeError(
            "unexpected"
        )

        client = AnalyticsHubClient(project_id="test-project")
        with pytest.raises(StorageError, match="Failed to get exchange"):
            client.get_exchange("test_exchange")


class TestCreateListing:
    """create_listing テスト."""

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_create_listing_success(
        self, mock_client_class: MagicMock, mock_listing: MagicMock
    ) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.return_value.create_listing.return_value = mock_listing

        client = AnalyticsHubClient(project_id="test-project")
        result = client.create_listing(
            exchange_id="test_exchange",
            listing_id="test_listing",
            dataset_id="sagebase_gold",
            display_name="Test Listing",
            description="テスト用Listing",
        )

        assert isinstance(result, ListingInfo)
        assert result.display_name == "Test Listing"
        assert result.state == "ACTIVE"

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_create_listing_with_provider_and_publisher(
        self, mock_client_class: MagicMock, mock_listing: MagicMock
    ) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.return_value.create_listing.return_value = mock_listing

        client = AnalyticsHubClient(project_id="test-project")
        result = client.create_listing(
            exchange_id="test_exchange",
            listing_id="test_listing",
            dataset_id="sagebase_gold",
            display_name="Test Listing",
            provider_name="Sagebase",
            publisher_name="Sagebase Project",
        )

        assert isinstance(result, ListingInfo)

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_create_listing_already_exists(
        self, mock_client_class: MagicMock, mock_listing: MagicMock
    ) -> None:
        from google.api_core.exceptions import AlreadyExists

        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_instance = mock_client_class.return_value
        mock_instance.create_listing.side_effect = AlreadyExists("exists")
        mock_instance.get_listing.return_value = mock_listing

        client = AnalyticsHubClient(project_id="test-project")
        result = client.create_listing(
            exchange_id="test_exchange",
            listing_id="test_listing",
            dataset_id="sagebase_gold",
            display_name="Test Listing",
        )

        assert isinstance(result, ListingInfo)

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_create_listing_permission_error(
        self, mock_client_class: MagicMock
    ) -> None:
        from google.api_core.exceptions import Forbidden

        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.return_value.create_listing.side_effect = Forbidden("denied")

        client = AnalyticsHubClient(project_id="test-project")
        with pytest.raises(StorageError, match="Permission denied"):
            client.create_listing(
                exchange_id="test_exchange",
                listing_id="test_listing",
                dataset_id="sagebase_gold",
                display_name="Test Listing",
            )

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_create_listing_general_error(self, mock_client_class: MagicMock) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.return_value.create_listing.side_effect = RuntimeError(
            "unexpected"
        )

        client = AnalyticsHubClient(project_id="test-project")
        with pytest.raises(StorageError, match="Failed to create listing"):
            client.create_listing(
                exchange_id="test_exchange",
                listing_id="test_listing",
                dataset_id="sagebase_gold",
                display_name="Test Listing",
            )


class TestGetListing:
    """get_listing テスト."""

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_get_listing_success(
        self, mock_client_class: MagicMock, mock_listing: MagicMock
    ) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.return_value.get_listing.return_value = mock_listing

        client = AnalyticsHubClient(project_id="test-project")
        result = client.get_listing("test_exchange", "test_listing")

        assert isinstance(result, ListingInfo)
        assert result.display_name == "Test Listing"

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_get_listing_not_found(self, mock_client_class: MagicMock) -> None:
        from google.api_core.exceptions import NotFound

        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.return_value.get_listing.side_effect = NotFound("not found")

        client = AnalyticsHubClient(project_id="test-project")
        with pytest.raises(StorageError, match="not found"):
            client.get_listing("test_exchange", "test_listing")

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_get_listing_permission_error(self, mock_client_class: MagicMock) -> None:
        from google.api_core.exceptions import Forbidden

        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.return_value.get_listing.side_effect = Forbidden("denied")

        client = AnalyticsHubClient(project_id="test-project")
        with pytest.raises(StorageError, match="Permission denied"):
            client.get_listing("test_exchange", "test_listing")

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_get_listing_general_error(self, mock_client_class: MagicMock) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_client_class.return_value.get_listing.side_effect = RuntimeError(
            "unexpected"
        )

        client = AnalyticsHubClient(project_id="test-project")
        with pytest.raises(StorageError, match="Failed to get listing"):
            client.get_listing("test_exchange", "test_listing")


class TestHelperMethods:
    """ヘルパーメソッドのテスト."""

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_parent_path(self, mock_client_class: MagicMock) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        client = AnalyticsHubClient(
            project_id="test-project", location="asia-northeast1"
        )
        assert client._parent == "projects/test-project/locations/asia-northeast1"

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_exchange_path(self, mock_client_class: MagicMock) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        client = AnalyticsHubClient(project_id="test-project")
        path = client._exchange_path("my_exchange")
        expected = (
            "projects/test-project/locations/asia-northeast1/dataExchanges/my_exchange"
        )
        assert path == expected

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_listing_path(self, mock_client_class: MagicMock) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        client = AnalyticsHubClient(project_id="test-project")
        path = client._listing_path("my_exchange", "my_listing")
        expected = (
            "projects/test-project/locations/asia-northeast1"
            "/dataExchanges/my_exchange/listings/my_listing"
        )
        assert path == expected

    @patch("src.infrastructure.bigquery.analytics_hub.AnalyticsHubServiceClient")
    def test_to_listing_info_state_without_name_attr(
        self, mock_client_class: MagicMock
    ) -> None:
        from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

        mock_listing = MagicMock()
        mock_listing.name = "test"
        mock_listing.display_name = "Test"
        mock_listing.description = "desc"
        mock_listing.state = 1  # int値（name属性なし）

        result = AnalyticsHubClient._to_listing_info(mock_listing)
        assert result.state == "1"
