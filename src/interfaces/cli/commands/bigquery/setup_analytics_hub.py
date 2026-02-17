"""Analytics Hub 公開設定コマンド."""

import logging
import os

from typing import Any

from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient
from src.infrastructure.bigquery.analytics_hub_config import (
    DEFAULT_EXCHANGE_DESCRIPTION,
    DEFAULT_EXCHANGE_DISPLAY_NAME,
    DEFAULT_EXCHANGE_ID,
    DEFAULT_LISTING_DESCRIPTION,
    DEFAULT_LISTING_DISPLAY_NAME,
    DEFAULT_LISTING_DOCUMENTATION,
    DEFAULT_LISTING_ID,
)
from src.interfaces.cli.base import BaseCommand, Command


logger = logging.getLogger(__name__)


class SetupAnalyticsHubCommand(Command, BaseCommand):
    """Analytics Hub公開設定コマンド."""

    def execute(self, **kwargs: Any) -> None:
        """Analytics Hubのセットアップを実行."""
        exchange_id: str = kwargs.get("exchange_id") or os.environ.get(
            "AH_EXCHANGE_ID", DEFAULT_EXCHANGE_ID
        )
        listing_id: str = kwargs.get("listing_id") or os.environ.get(
            "AH_LISTING_ID", DEFAULT_LISTING_ID
        )
        dataset_id: str = kwargs.get("dataset") or os.environ.get(
            "BQ_DATASET_ID", "sagebase_gold"
        )
        primary_contact: str = kwargs.get("primary_contact") or os.environ.get(
            "AH_PRIMARY_CONTACT", ""
        )
        dry_run: bool = kwargs.get("dry_run", False)

        if dry_run:
            self._show_dry_run(exchange_id, listing_id, dataset_id, primary_contact)
            return

        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        if not project_id:
            self.error("環境変数 GOOGLE_CLOUD_PROJECT が設定されていません")
            return

        location = os.environ.get("BQ_LOCATION", "asia-northeast1")

        self.show_progress(f"プロジェクト: {project_id}")
        self.show_progress(f"ロケーション: {location}")
        self.show_progress("")

        client = AnalyticsHubClient(
            project_id=project_id,
            location=location,
        )

        # Exchange作成
        self.show_progress(f"Exchange作成中: {exchange_id}...")
        exchange = client.create_exchange(
            exchange_id=exchange_id,
            display_name=DEFAULT_EXCHANGE_DISPLAY_NAME,
            description=DEFAULT_EXCHANGE_DESCRIPTION,
            primary_contact=primary_contact,
            public=True,
        )
        self.show_progress(f"  Exchange: {exchange.name}")

        # Listing作成
        self.show_progress(f"Listing作成中: {listing_id}...")
        listing = client.create_listing(
            exchange_id=exchange_id,
            listing_id=listing_id,
            dataset_id=dataset_id,
            display_name=DEFAULT_LISTING_DISPLAY_NAME,
            description=DEFAULT_LISTING_DESCRIPTION,
            primary_contact=primary_contact,
            documentation=DEFAULT_LISTING_DOCUMENTATION,
            provider_name="Sagebase",
            publisher_name="Sagebase Project",
        )
        self.show_progress(f"  Listing: {listing.name}")
        self.show_progress(f"  状態: {listing.state}")

        self.success(
            f"Analytics Hub セットアップ完了: "
            f"Exchange={exchange_id}, Listing={listing_id}"
        )

    def _show_dry_run(
        self,
        exchange_id: str,
        listing_id: str,
        dataset_id: str,
        primary_contact: str,
    ) -> None:
        """ドライラン時の設定内容を表示."""
        self.show_progress("=== Analytics Hub セットアップ設定（ドライラン） ===")
        self.show_progress("")
        self.show_progress("--- Exchange ---")
        self.show_progress(f"  ID: {exchange_id}")
        self.show_progress(f"  表示名: {DEFAULT_EXCHANGE_DISPLAY_NAME}")
        self.show_progress(f"  説明: {DEFAULT_EXCHANGE_DESCRIPTION}")
        self.show_progress("  公開設定: PUBLIC")
        self.show_progress(f"  連絡先: {primary_contact or '(未設定)'}")
        self.show_progress("")
        self.show_progress("--- Listing ---")
        self.show_progress(f"  ID: {listing_id}")
        self.show_progress(f"  表示名: {DEFAULT_LISTING_DISPLAY_NAME}")
        self.show_progress(f"  データセット: {dataset_id}")
        self.show_progress(f"  説明: {DEFAULT_LISTING_DESCRIPTION[:80]}...")
        self.show_progress("")
        self.show_progress("ドライランモード: リソースは作成されませんでした")
