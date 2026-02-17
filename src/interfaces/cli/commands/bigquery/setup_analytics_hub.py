"""Analytics Hub 公開設定コマンド."""

import logging

from typing import Any

from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient
from src.interfaces.cli.base import BaseCommand, Command


logger = logging.getLogger(__name__)

# デフォルト設定
DEFAULT_EXCHANGE_ID = "sagebase_exchange"
DEFAULT_LISTING_ID = "sagebase_gold_listing"
DEFAULT_EXCHANGE_DISPLAY_NAME = "Sagebase 政治活動データ"
DEFAULT_EXCHANGE_DESCRIPTION = (
    "日本の政治活動追跡データを提供します。"
    "全1,966地方議会の議事録・発言・議案賛否等のデータを含みます。"
)
DEFAULT_LISTING_DISPLAY_NAME = "Sagebase Gold Layer - 政治活動データ"
DEFAULT_LISTING_DESCRIPTION = (
    "日本の地方議会・国会の政治活動データ（Gold Layer）。\n\n"
    "20テーブル: 政治家、政党、選挙、会議体、議事録、発言、議案、賛否記録等。\n"
    "全1,966地方議会対応。\n\n"
    "データ更新頻度: 随時（新規議事録の処理後にエクスポート）"
)
DEFAULT_LISTING_DOCUMENTATION = (
    "# Sagebase Gold Layer データセット\n\n"
    "## 概要\n"
    "日本の地方議会・国会の政治活動データを提供するデータセットです。\n\n"
    "## データ更新頻度\n"
    "随時（新規議事録の処理・エクスポート後に反映されます）\n\n"
    "## ライセンス\n"
    "本データは公開情報（議会議事録等）を元に構造化したデータです。\n"
    "クエリ実行コストはサブスクライバー側で課金されます。\n"
)


class SetupAnalyticsHubCommand(Command, BaseCommand):
    """Analytics Hub公開設定コマンド."""

    def execute(self, **kwargs: Any) -> None:
        """Analytics Hubのセットアップを実行."""
        import os

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
