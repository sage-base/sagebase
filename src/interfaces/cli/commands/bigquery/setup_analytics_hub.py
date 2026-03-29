"""Analytics Hub 公開設定コマンド."""

import logging
import os

from typing import Any

from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient
from src.infrastructure.bigquery.analytics_hub_config import (
    DEFAULT_EXCHANGE_DESCRIPTION,
    DEFAULT_EXCHANGE_DISPLAY_NAME,
    DEFAULT_EXCHANGE_ID,
    LISTING_CONFIGS,
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
        primary_contact: str = kwargs.get("primary_contact") or os.environ.get(
            "AH_PRIMARY_CONTACT", ""
        )
        dry_run: bool = kwargs.get("dry_run", False)

        if dry_run:
            self._show_dry_run(exchange_id, primary_contact)
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

        # 各データセットのListing作成
        for config in LISTING_CONFIGS:
            self.show_progress(f"Listing作成中: {config.listing_id}...")
            listing = client.create_listing(
                exchange_id=exchange_id,
                listing_id=config.listing_id,
                dataset_id=config.dataset_id,
                display_name=config.display_name,
                description=config.description,
                primary_contact=primary_contact,
                documentation=config.documentation,
                provider_name="Sagebase",
                publisher_name="Sagebase Project",
            )
            self.show_progress(f"  Listing: {listing.name}")
            self.show_progress(f"  状態: {listing.state}")

        self.success(
            f"Analytics Hub セットアップ完了: "
            f"Exchange={exchange_id}, Listings={len(LISTING_CONFIGS)}件"
        )

    def _show_dry_run(
        self,
        exchange_id: str,
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
        for config in LISTING_CONFIGS:
            self.show_progress(f"--- Listing: {config.listing_id} ---")
            self.show_progress(f"  データセット: {config.dataset_id}")
            self.show_progress(f"  表示名: {config.display_name}")
            self.show_progress(f"  説明: {config.description[:80]}...")
            self.show_progress("")
        self.show_progress("ドライランモード: リソースは作成されませんでした")
