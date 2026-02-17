"""PostgreSQL Gold Layer → BigQuery エクスポートコマンド."""

import logging
import time

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text

from src.infrastructure.bigquery.client import BigQueryClient
from src.infrastructure.bigquery.schema import GOLD_LAYER_TABLES, BQTableDef
from src.infrastructure.config.database import get_db_engine
from src.interfaces.cli.base import BaseCommand, Command


logger = logging.getLogger(__name__)


def serialize_value(value: Any) -> Any:
    """PostgreSQLの値をBigQuery JSON互換の値に変換する."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    """行データの全カラムをシリアライズする."""
    return {key: serialize_value(value) for key, value in row.items()}


class ExportToBigQueryCommand(Command, BaseCommand):
    """PostgreSQL Gold LayerテーブルをBigQueryにエクスポートするコマンド."""

    def execute(self, **kwargs: Any) -> None:
        """エクスポートを実行."""
        import os

        table_name: str | None = kwargs.get("table")
        export_all: bool = kwargs.get("export_all", False)
        dataset: str | None = kwargs.get("dataset")

        if not table_name and not export_all:
            self.error("--table または --all を指定してください")
            return

        table_defs = self._resolve_table_defs(table_name, export_all)
        if not table_defs:
            return

        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        if not project_id:
            self.error("環境変数 GOOGLE_CLOUD_PROJECT が設定されていません")
            return

        dataset_id = dataset or os.environ.get("BQ_DATASET_ID", "sagebase_gold")
        location = os.environ.get("BQ_LOCATION", "asia-northeast1")

        bq_client = BigQueryClient(
            project_id=project_id,
            dataset_id=dataset_id,
            location=location,
        )
        bq_client.ensure_dataset()

        engine = get_db_engine()

        results: list[tuple[str, int, float]] = []

        for table_def in table_defs:
            start = time.monotonic()
            self.show_progress(f"  エクスポート中: {table_def.table_id}...")

            columns = [col.name for col in table_def.columns]
            col_list = ", ".join(f'"{c}"' for c in columns)
            query = f'SELECT {col_list} FROM "{table_def.table_id}"'  # noqa: S608

            with engine.connect() as conn:
                result = conn.execute(text(query))
                col_names = list(result.keys())
                rows = [
                    serialize_row(dict(zip(col_names, row, strict=True)))
                    for row in result.fetchall()
                ]

            if rows:
                bq_client.load_table_data(table_def, rows)
            else:
                bq_client.create_table(table_def)
                logger.info(f"Table {table_def.table_id} has 0 rows, skipping load")

            elapsed = time.monotonic() - start
            results.append((table_def.table_id, len(rows), elapsed))
            self.show_progress(f"    {len(rows)} 行 ({elapsed:.1f}s)")

        self._show_summary(results)

    def _resolve_table_defs(
        self, table_name: str | None, export_all: bool
    ) -> list[BQTableDef]:
        """テーブル定義を解決する."""
        if export_all:
            return GOLD_LAYER_TABLES

        table_map = {t.table_id: t for t in GOLD_LAYER_TABLES}

        if table_name and table_name not in table_map:
            available = ", ".join(sorted(table_map.keys()))
            self.error(
                f"テーブル '{table_name}' はGold Layer定義に存在しません。"
                f"\n利用可能: {available}",
            )
            return []

        if table_name:
            return [table_map[table_name]]

        return []

    def _show_summary(self, results: list[tuple[str, int, float]]) -> None:
        """エクスポート結果のサマリを表示する."""
        total_rows = sum(r[1] for r in results)
        total_time = sum(r[2] for r in results)
        self.success(
            f"エクスポート完了: {len(results)} テーブル, "
            f"{total_rows} 行 ({total_time:.1f}s)"
        )
