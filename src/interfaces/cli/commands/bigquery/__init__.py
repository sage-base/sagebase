"""BigQuery CLI commands."""

import click

from src.interfaces.cli.base import with_error_handling
from src.interfaces.cli.commands.bigquery.export import ExportToBigQueryCommand
from src.interfaces.cli.commands.bigquery.setup_analytics_hub import (
    SetupAnalyticsHubCommand,
)


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


@click.command("setup-analytics-hub")
@click.option("--exchange-id", default=None, help="Exchange ID")
@click.option("--listing-id", default=None, help="Listing ID")
@click.option("--dataset", default=None, help="BigQueryデータセットID")
@click.option("--primary-contact", default=None, help="連絡先メールアドレス")
@click.option("--dry-run", is_flag=True, help="設定内容を表示するだけで作成しない")
@with_error_handling
def setup_analytics_hub(
    exchange_id: str | None,
    listing_id: str | None,
    dataset: str | None,
    primary_contact: str | None,
    dry_run: bool,
):
    """Analytics Hub の Exchange と Listing をセットアップする."""
    command = SetupAnalyticsHubCommand()
    command.execute(
        exchange_id=exchange_id,
        listing_id=listing_id,
        dataset=dataset,
        primary_contact=primary_contact,
        dry_run=dry_run,
    )
