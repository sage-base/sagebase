"""Analytics Hub セットアップスクリプト.

BigQuery Analytics Hub に Exchange と Listing を作成し、
sagebase_source / sagebase_vault / sagebase の3データセットを公開する。

使用方法:
    # ドライラン（設定内容の確認のみ、API アクセス不要）
    uv run python scripts/setup_analytics_hub.py --dry-run

    # 実行（要: GOOGLE_CLOUD_PROJECT 環境変数）
    uv run python scripts/setup_analytics_hub.py --project-id my-project

    # Docker環境
    docker compose exec app uv run python \
        scripts/setup_analytics_hub.py --dry-run

外部データ依存:
    - GOOGLE_CLOUD_PROJECT 環境変数（または --project-id 引数）
    - GCP認証（gcloud auth application-default login）
    - analyticshub.googleapis.com API が有効化されていること
"""

import argparse
import os
import sys

from src.infrastructure.bigquery.analytics_hub_config import (
    DEFAULT_EXCHANGE_DESCRIPTION,
    DEFAULT_EXCHANGE_DISPLAY_NAME,
    DEFAULT_EXCHANGE_ID,
    LISTING_CONFIGS,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analytics Hub に Exchange と Listing をセットアップする"
    )
    parser.add_argument(
        "--project-id",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
        help="GCPプロジェクトID（デフォルト: GOOGLE_CLOUD_PROJECT環境変数）",
    )
    parser.add_argument(
        "--location",
        default=os.environ.get("BQ_LOCATION", "asia-northeast1"),
        help="BigQueryロケーション（デフォルト: asia-northeast1）",
    )
    parser.add_argument(
        "--exchange-id",
        default=os.environ.get("AH_EXCHANGE_ID", DEFAULT_EXCHANGE_ID),
        help=f"Exchange ID（デフォルト: {DEFAULT_EXCHANGE_ID}）",
    )
    parser.add_argument(
        "--primary-contact",
        default=os.environ.get("AH_PRIMARY_CONTACT", ""),
        help="連絡先メールアドレス",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="設定内容を表示するだけで実際には作成しない",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("=== Analytics Hub セットアップ設定（ドライラン） ===\n")
        print(f"プロジェクト: {args.project_id or '(未設定)'}")
        print(f"ロケーション: {args.location}")
        print()
        print("--- Exchange ---")
        print(f"  ID: {args.exchange_id}")
        print(f"  表示名: {DEFAULT_EXCHANGE_DISPLAY_NAME}")
        print(f"  説明: {DEFAULT_EXCHANGE_DESCRIPTION}")
        print("  公開設定: PUBLIC")
        print(f"  連絡先: {args.primary_contact or '(未設定)'}")
        print()
        for config in LISTING_CONFIGS:
            print(f"--- Listing: {config.listing_id} ---")
            print(f"  データセット: {config.dataset_id}")
            print(f"  表示名: {config.display_name}")
            print(f"  説明: {config.description[:80]}...")
            print()
        print("ドライランモード: リソースは作成されませんでした")
        return

    if not args.project_id:
        print(
            "エラー: --project-id または"
            " GOOGLE_CLOUD_PROJECT 環境変数を設定してください",
            file=sys.stderr,
        )
        sys.exit(1)

    from src.infrastructure.bigquery.analytics_hub import AnalyticsHubClient

    print(f"プロジェクト: {args.project_id}")
    print(f"ロケーション: {args.location}")
    print()

    client = AnalyticsHubClient(
        project_id=args.project_id,
        location=args.location,
    )

    # Exchange作成
    print(f"Exchange作成中: {args.exchange_id}...")
    exchange = client.create_exchange(
        exchange_id=args.exchange_id,
        display_name=DEFAULT_EXCHANGE_DISPLAY_NAME,
        description=DEFAULT_EXCHANGE_DESCRIPTION,
        primary_contact=args.primary_contact,
        public=True,
    )
    print(f"  Exchange: {exchange.name}")
    print(f"    表示名: {exchange.display_name}")

    # 各データセットのListing作成
    for config in LISTING_CONFIGS:
        print(f"\nListing作成中: {config.listing_id}...")
        listing = client.create_listing(
            exchange_id=args.exchange_id,
            listing_id=config.listing_id,
            dataset_id=config.dataset_id,
            display_name=config.display_name,
            description=config.description,
            primary_contact=args.primary_contact,
            documentation=config.documentation,
            provider_name="Sagebase",
            publisher_name="Sagebase Project",
        )
        print(f"  Listing: {listing.name}")
        print(f"    表示名: {listing.display_name}")
        print(f"    状態: {listing.state}")

    print(f"\nセットアップが完了しました（{len(LISTING_CONFIGS)}件のListing作成）")


if __name__ == "__main__":
    main()
