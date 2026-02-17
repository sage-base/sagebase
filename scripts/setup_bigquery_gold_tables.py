"""BigQuery Gold Layerテーブルセットアップスクリプト.

BigQueryにGold Layer用のデータセットとテーブルを作成する。

使用方法:
    # ドライラン（テーブル定義の確認のみ、BQアクセス不要）
    uv run python scripts/setup_bigquery_gold_tables.py --dry-run

    # 実行（要: GOOGLE_CLOUD_PROJECT 環境変数）
    uv run python scripts/setup_bigquery_gold_tables.py --project-id my-project

    # Docker環境
    docker compose exec app uv run python \
        scripts/setup_bigquery_gold_tables.py --dry-run
"""

import argparse
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BigQuery Gold Layerテーブルをセットアップする"
    )
    parser.add_argument(
        "--project-id",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
        help="GCPプロジェクトID（デフォルト: GOOGLE_CLOUD_PROJECT環境変数）",
    )
    parser.add_argument(
        "--dataset-id",
        default=os.environ.get("BQ_DATASET_ID", "sagebase_gold"),
        help="BigQueryデータセットID（デフォルト: sagebase_gold）",
    )
    parser.add_argument(
        "--location",
        default=os.environ.get("BQ_LOCATION", "asia-northeast1"),
        help="BigQueryロケーション（デフォルト: asia-northeast1）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="テーブル定義を表示するだけで実際には作成しない",
    )
    args = parser.parse_args()

    from src.infrastructure.bigquery.schema import GOLD_LAYER_TABLES

    if args.dry_run:
        print(f"=== Gold Layer テーブル定義（{len(GOLD_LAYER_TABLES)}テーブル） ===\n")
        print(f"データセット: {args.dataset_id}")
        print(f"ロケーション: {args.location}\n")
        for table_def in GOLD_LAYER_TABLES:
            print(f"--- {table_def.table_id}: {table_def.description} ---")
            for col in table_def.columns:
                mode = f" ({col.mode})" if col.mode == "REQUIRED" else ""
                desc = f"  -- {col.description}" if col.description else ""
                print(f"  {col.name}: {col.bq_type}{mode}{desc}")
            print()
        print("ドライランモード: テーブルは作成されませんでした")
        return

    if not args.project_id:
        print(
            "エラー: --project-id または"
            " GOOGLE_CLOUD_PROJECT 環境変数を設定してください",
            file=sys.stderr,
        )
        sys.exit(1)

    from src.infrastructure.bigquery.client import BigQueryClient

    print(f"プロジェクト: {args.project_id}")
    print(f"データセット: {args.dataset_id}")
    print(f"ロケーション: {args.location}")
    print(f"テーブル数: {len(GOLD_LAYER_TABLES)}")
    print()

    client = BigQueryClient(
        project_id=args.project_id,
        dataset_id=args.dataset_id,
        location=args.location,
    )
    client.create_all_tables(GOLD_LAYER_TABLES)
    print("\nセットアップが完了しました")


if __name__ == "__main__":
    main()
