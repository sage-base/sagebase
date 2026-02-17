"""BigQuery CLI commands."""

import click

from src.interfaces.cli.base import with_error_handling
from src.interfaces.cli.commands.bigquery.export import ExportToBigQueryCommand


@click.command("export-to-bq")
@click.option("--table", default=None, help="エクスポートするテーブル名")
@click.option(
    "--all", "export_all", is_flag=True, help="全Gold Layerテーブルをエクスポート"
)
@click.option("--dataset", default=None, help="BigQueryデータセットID")
@with_error_handling
def export_to_bq(table: str | None, export_all: bool, dataset: str | None):
    """PostgreSQL Gold Layer → BigQuery エクスポート (全件洗い替え)."""
    command = ExportToBigQueryCommand()
    command.execute(table=table, export_all=export_all, dataset=dataset)
