"""PostgreSQL Gold Layer → BigQuery エクスポートコマンド."""

import logging
import time

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import inspect, text

from src.infrastructure.bigquery.client import BigQueryClient
from src.infrastructure.bigquery.schema import GOLD_LAYER_TABLES, BQTableDef
from src.infrastructure.config.database import get_db_engine
from src.interfaces.cli.base import BaseCommand, Command


logger = logging.getLogger(__name__)

# 大規模テーブルのバッチサイズ
_BATCH_SIZE = 500_000
# バッチ処理を使用する行数の閾値
_BATCH_THRESHOLD = 1_000_000


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
        pg_tables = set(inspect(engine).get_table_names())

        results: list[tuple[str, int, float]] = []

        for table_def in table_defs:
            if table_def.table_id not in pg_tables:
                self.warning(
                    f"  スキップ: {table_def.table_id}"
                    "（PostgreSQLにテーブルが存在しません）"
                )
                continue

            start = time.monotonic()

            # 行数を事前チェックして大規模テーブルはバッチ処理
            with engine.connect() as conn:
                count_result = conn.execute(
                    text(f'SELECT COUNT(*) FROM "{table_def.table_id}"')  # noqa: S608
                )
                row_count = count_result.scalar() or 0

            if row_count >= _BATCH_THRESHOLD:
                loaded = self._export_table_batched(
                    engine, bq_client, table_def, row_count
                )
            else:
                loaded = self._export_table_simple(engine, bq_client, table_def)

            elapsed = time.monotonic() - start
            results.append((table_def.table_id, loaded, elapsed))
            self.show_progress(f"    {loaded} 行 ({elapsed:.1f}s)")

        self._show_summary(results)

    def _export_table_simple(
        self,
        engine: Any,
        bq_client: BigQueryClient,
        table_def: BQTableDef,
    ) -> int:
        """小規模テーブルを一括エクスポート."""
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

        return len(rows)

    def _export_table_batched(
        self,
        engine: Any,
        bq_client: BigQueryClient,
        table_def: BQTableDef,
        total_rows: int,
    ) -> int:
        """大規模テーブルをバッチ処理でエクスポート."""
        columns = [col.name for col in table_def.columns]
        col_list = ", ".join(f'"{c}"' for c in columns)
        base_query = f'SELECT {col_list} FROM "{table_def.table_id}" ORDER BY id'  # noqa: S608

        total_loaded = 0
        batch_num = 0
        total_batches = (total_rows + _BATCH_SIZE - 1) // _BATCH_SIZE

        self.show_progress(
            f"  エクスポート中: {table_def.table_id}"
            f" ({total_rows:,}行, {total_batches}バッチ)..."
        )

        offset = 0
        while offset < total_rows:
            batch_num += 1
            query = f"{base_query} LIMIT {_BATCH_SIZE} OFFSET {offset}"  # noqa: S608

            with engine.connect() as conn:
                result = conn.execute(text(query))
                col_names = list(result.keys())
                rows = [
                    serialize_row(dict(zip(col_names, row, strict=True)))
                    for row in result.fetchall()
                ]

            if not rows:
                break

            # 最初のバッチはTRUNCATE、以降はAPPEND
            is_first_batch = batch_num == 1
            bq_client.load_table_data(table_def, rows, append=not is_first_batch)
            total_loaded += len(rows)

            self.show_progress(
                f"    バッチ {batch_num}/{total_batches}:"
                f" {total_loaded:,}/{total_rows:,} 行"
            )

            offset += _BATCH_SIZE

        return total_loaded

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
            f"{total_rows:,} 行 ({total_time:.1f}s)"
        )
