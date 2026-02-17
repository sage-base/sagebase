"""Database management CLI commands."""

import click

from src.interfaces.cli.base import with_error_handling
from src.interfaces.cli.commands.database.backup import BackupCommand
from src.interfaces.cli.commands.database.connection import TestConnectionCommand
from src.interfaces.cli.commands.database.dump_restore import (
    DumpCommand,
    ListDumpsCommand,
    RestoreDumpCommand,
)
from src.interfaces.cli.commands.database.reset import ResetDatabaseCommand
from src.interfaces.cli.commands.database.restore import RestoreCommand


@click.group()
def database():
    """Database management commands (データベース管理)."""
    pass


@database.command()
@with_error_handling
def test_connection():
    """Test database connection (データベース接続テスト)."""
    command = TestConnectionCommand()
    command.execute()


@database.command()
@click.option("--gcs/--no-gcs", default=True, help="GCSを使用する/しない")
@with_error_handling
def backup(gcs: bool):
    """Create database backup (データベースバックアップ)."""
    command = BackupCommand()
    command.execute(gcs=gcs)


@database.command()
@click.argument("filename")
@with_error_handling
def restore(filename: str):
    """Restore database from backup (データベースリストア)."""
    command = RestoreCommand()
    command.execute(filename=filename)


@database.command()
@click.option("--gcs/--no-gcs", default=True, help="GCSを使用する/しない")
@with_error_handling
def list_backups(gcs: bool):
    """List available backups (バックアップ一覧)."""
    from src.interfaces.cli.commands.database.list_backups import ListBackupsCommand

    command = ListBackupsCommand()
    command.execute(gcs=gcs)


@database.command()
@with_error_handling
def reset():
    """Reset database to initial state (データベースリセット)."""
    command = ResetDatabaseCommand()
    command.execute()


@database.command()
@click.option("--tables", default=None, help="ダンプするテーブル名（カンマ区切り）")
@with_error_handling
def dump(tables: str | None):
    """JSON形式でデータベースをダンプ (DBダンプ)."""
    command = DumpCommand()
    command.execute(tables=tables)


@database.command("restore-dump")
@click.argument("dump_dir")
@click.option(
    "--truncate", is_flag=True, default=False, help="既存データを削除してからリストア"
)
@with_error_handling
def restore_dump(dump_dir: str, truncate: bool):
    """JSONダンプからデータベースをリストア (DBリストア)."""
    command = RestoreDumpCommand()
    command.execute(dump_dir=dump_dir, truncate=truncate)


@database.command("list-dumps")
@with_error_handling
def list_dumps():
    """過去のダンプ一覧を表示."""
    command = ListDumpsCommand()
    command.execute()
