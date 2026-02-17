"""Analytics Hub クライアント.

BigQuery Analytics Hub の Exchange/Listing を管理する。
BigQueryClientと同様のパターンで実装。
"""

import logging

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any


try:
    from google.api_core.exceptions import (
        AlreadyExists,
        Forbidden,
        NotFound,
    )
    from google.auth.exceptions import RefreshError
    from google.cloud.bigquery_analyticshub_v1 import AnalyticsHubServiceClient
    from google.cloud.bigquery_analyticshub_v1.types import (
        CreateDataExchangeRequest,
        CreateListingRequest,
        DataExchange,
        DataProvider,
        DiscoveryType,
        GetDataExchangeRequest,
        GetListingRequest,
        Listing,
        Publisher,
    )

    HAS_ANALYTICSHUB = True
except ImportError:
    HAS_ANALYTICSHUB = False
    if TYPE_CHECKING:
        from google.api_core.exceptions import (
            AlreadyExists,
            Forbidden,
            NotFound,
        )
        from google.auth.exceptions import RefreshError
        from google.cloud.bigquery_analyticshub_v1 import AnalyticsHubServiceClient
        from google.cloud.bigquery_analyticshub_v1.types import (
            CreateDataExchangeRequest,
            CreateListingRequest,
            DataExchange,
            DataProvider,
            DiscoveryType,
            GetDataExchangeRequest,
            GetListingRequest,
            Listing,
            Publisher,
        )
    else:
        AlreadyExists = Exception
        Forbidden = Exception
        NotFound = Exception
        RefreshError = Exception
        AnalyticsHubServiceClient = None

from src.infrastructure.exceptions import (
    AuthenticationError,
    StorageError,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExchangeInfo:
    """Analytics Hub Exchange情報."""

    name: str
    display_name: str
    description: str
    listing_count: int


@dataclass(frozen=True)
class ListingInfo:
    """Analytics Hub Listing情報."""

    name: str
    display_name: str
    description: str
    state: str


class AnalyticsHubClient:
    """Analytics Hub Exchange/Listing管理クライアント."""

    def __init__(
        self,
        project_id: str,
        location: str = "asia-northeast1",
    ) -> None:
        self.client: Any

        if not HAS_ANALYTICSHUB:
            raise StorageError(
                "Google Cloud BigQuery Analytics Hub library not installed. "
                "Install with: uv add google-cloud-bigquery-analyticshub"
            )

        self.project_id = project_id
        self.location = location

        try:
            self.client = AnalyticsHubServiceClient()
        except RefreshError as e:
            logger.error(f"Analytics Hub authentication failed: {e}")
            raise AuthenticationError(
                service="Analytics Hub",
                reason="認証トークンの有効期限が切れています",
                solution="以下のコマンドを実行して再認証してください:\n"
                "  gcloud auth application-default login",
            ) from e
        except Exception as e:
            logger.error(f"Failed to initialize Analytics Hub client: {e}")
            raise StorageError(
                "Failed to initialize Analytics Hub client",
                {"project_id": project_id, "error": str(e)},
            ) from e

    @property
    def _parent(self) -> str:
        """プロジェクト/ロケーションの親パスを返す."""
        return f"projects/{self.project_id}/locations/{self.location}"

    def _exchange_path(self, exchange_id: str) -> str:
        """Exchange のフルパスを返す."""
        return f"{self._parent}/dataExchanges/{exchange_id}"

    def _listing_path(self, exchange_id: str, listing_id: str) -> str:
        """Listing のフルパスを返す."""
        return f"{self._parent}/dataExchanges/{exchange_id}/listings/{listing_id}"

    def create_exchange(
        self,
        exchange_id: str,
        display_name: str,
        description: str = "",
        primary_contact: str = "",
        documentation: str = "",
        public: bool = True,
    ) -> ExchangeInfo:
        """Exchangeを作成する（存在する場合は既存を返す）.

        Args:
            exchange_id: Exchange ID
            display_name: 表示名
            description: 説明
            primary_contact: 連絡先
            documentation: ドキュメント
            public: 公開設定

        Returns:
            作成されたExchange情報
        """
        discovery_type = (
            DiscoveryType.DISCOVERY_TYPE_PUBLIC
            if public
            else DiscoveryType.DISCOVERY_TYPE_PRIVATE
        )

        data_exchange = DataExchange(
            display_name=display_name,
            description=description,
            primary_contact=primary_contact,
            documentation=documentation,
            discovery_type=discovery_type,
        )

        request = CreateDataExchangeRequest(
            parent=self._parent,
            data_exchange_id=exchange_id,
            data_exchange=data_exchange,
        )

        try:
            result = self.client.create_data_exchange(request=request)
            logger.info(f"Exchange created: {result.name}")
            return self._to_exchange_info(result)
        except AlreadyExists:
            logger.info(f"Exchange already exists: {exchange_id}, fetching existing")
            return self.get_exchange(exchange_id)
        except Forbidden as e:
            logger.error(f"Permission denied creating exchange: {e}")
            raise StorageError(
                f"Permission denied creating exchange '{exchange_id}'",
                {"exchange_id": exchange_id, "error": str(e)},
            ) from e
        except Exception as e:
            logger.error(f"Failed to create exchange: {e}")
            raise StorageError(
                f"Failed to create exchange '{exchange_id}'",
                {"exchange_id": exchange_id, "error": str(e)},
            ) from e

    def get_exchange(self, exchange_id: str) -> ExchangeInfo:
        """Exchangeを取得する.

        Args:
            exchange_id: Exchange ID

        Returns:
            Exchange情報

        Raises:
            StorageError: Exchangeが見つからない場合
        """
        request = GetDataExchangeRequest(
            name=self._exchange_path(exchange_id),
        )

        try:
            result = self.client.get_data_exchange(request=request)
            return self._to_exchange_info(result)
        except NotFound as e:
            raise StorageError(
                f"Exchange '{exchange_id}' not found",
                {"exchange_id": exchange_id},
            ) from e
        except Forbidden as e:
            raise StorageError(
                f"Permission denied accessing exchange '{exchange_id}'",
                {"exchange_id": exchange_id, "error": str(e)},
            ) from e
        except Exception as e:
            raise StorageError(
                f"Failed to get exchange '{exchange_id}'",
                {"exchange_id": exchange_id, "error": str(e)},
            ) from e

    def create_listing(
        self,
        exchange_id: str,
        listing_id: str,
        dataset_id: str,
        display_name: str,
        description: str = "",
        primary_contact: str = "",
        documentation: str = "",
        provider_name: str = "",
        publisher_name: str = "",
    ) -> ListingInfo:
        """Listingを作成する（存在する場合は既存を返す）.

        Args:
            exchange_id: Exchange ID
            listing_id: Listing ID
            dataset_id: BigQueryデータセットID
            display_name: 表示名
            description: 説明
            primary_contact: 連絡先
            documentation: ドキュメント
            provider_name: データプロバイダ名
            publisher_name: パブリッシャー名

        Returns:
            作成されたListing情報
        """
        dataset_ref = f"projects/{self.project_id}/datasets/{dataset_id}"

        listing = Listing(
            display_name=display_name,
            description=description,
            primary_contact=primary_contact,
            documentation=documentation,
            bigquery_dataset=Listing.BigQueryDatasetSource(
                dataset=dataset_ref,
            ),
        )

        if provider_name:
            listing.data_provider = DataProvider(
                name=provider_name,
                primary_contact=primary_contact,
            )

        if publisher_name:
            listing.publisher = Publisher(
                name=publisher_name,
                primary_contact=primary_contact,
            )

        request = CreateListingRequest(
            parent=self._exchange_path(exchange_id),
            listing_id=listing_id,
            listing=listing,
        )

        try:
            result = self.client.create_listing(request=request)
            logger.info(f"Listing created: {result.name}")
            return self._to_listing_info(result)
        except AlreadyExists:
            logger.info(f"Listing already exists: {listing_id}, fetching existing")
            return self.get_listing(exchange_id, listing_id)
        except Forbidden as e:
            logger.error(f"Permission denied creating listing: {e}")
            raise StorageError(
                f"Permission denied creating listing '{listing_id}'",
                {"listing_id": listing_id, "error": str(e)},
            ) from e
        except Exception as e:
            logger.error(f"Failed to create listing: {e}")
            raise StorageError(
                f"Failed to create listing '{listing_id}'",
                {"listing_id": listing_id, "error": str(e)},
            ) from e

    def get_listing(self, exchange_id: str, listing_id: str) -> ListingInfo:
        """Listingを取得する.

        Args:
            exchange_id: Exchange ID
            listing_id: Listing ID

        Returns:
            Listing情報

        Raises:
            StorageError: Listingが見つからない場合
        """
        request = GetListingRequest(
            name=self._listing_path(exchange_id, listing_id),
        )

        try:
            result = self.client.get_listing(request=request)
            return self._to_listing_info(result)
        except NotFound as e:
            raise StorageError(
                f"Listing '{listing_id}' not found",
                {"exchange_id": exchange_id, "listing_id": listing_id},
            ) from e
        except Forbidden as e:
            raise StorageError(
                f"Permission denied accessing listing '{listing_id}'",
                {"listing_id": listing_id, "error": str(e)},
            ) from e
        except Exception as e:
            raise StorageError(
                f"Failed to get listing '{listing_id}'",
                {"listing_id": listing_id, "error": str(e)},
            ) from e

    @staticmethod
    def _to_exchange_info(exchange: Any) -> ExchangeInfo:
        """DataExchangeをExchangeInfoに変換する."""
        return ExchangeInfo(
            name=exchange.name,
            display_name=exchange.display_name,
            description=exchange.description,
            listing_count=exchange.listing_count,
        )

    @staticmethod
    def _to_listing_info(listing: Any) -> ListingInfo:
        """ListingをListingInfoに変換する."""
        return ListingInfo(
            name=listing.name,
            display_name=listing.display_name,
            description=listing.description,
            state=listing.state.name
            if hasattr(listing.state, "name")
            else str(listing.state),
        )
