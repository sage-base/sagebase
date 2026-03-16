"""政府関係者CSVインポートコマンド."""

from __future__ import annotations

import asyncio
import csv

from pathlib import Path
from typing import TYPE_CHECKING

import click

from src.interfaces.cli.base import with_error_handling


if TYPE_CHECKING:
    from src.application.dtos.government_official_dto import (
        ImportGovernmentOfficialsCsvOutputDto,
    )

# CSVの必須カラム
REQUIRED_COLUMNS = {
    "speaker_name",
    "representative_speaker_id",
    "organization",
    "position",
}


@click.command()
@click.option(
    "--csv",
    "csv_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="インポートするCSVファイルのパス",
)
@click.option("--dry-run", is_flag=True, help="実際にはインポートせず内容を確認する")
@with_error_handling
def import_officials(csv_path: Path, dry_run: bool):
    """政府関係者CSVをインポートする."""
    asyncio.run(_run_import_officials(csv_path, dry_run))


async def _run_import_officials(csv_path: Path, dry_run: bool) -> None:
    from src.application.dtos.government_official_dto import (
        GovernmentOfficialCsvRow,
        ImportGovernmentOfficialsCsvInputDto,
    )
    from src.infrastructure.di.container import get_container, init_container

    # CSV読み込み
    rows = _read_csv(csv_path)
    if not rows:
        click.echo("CSVファイルにデータ行がありません。")
        return

    click.echo(f"=== 政府関係者CSVインポート {'(ドライラン)' if dry_run else ''} ===")
    click.echo(f"  ファイル: {csv_path}")
    click.echo(f"  データ行数: {len(rows)}")
    click.echo()

    # DTO変換
    csv_rows: list[GovernmentOfficialCsvRow] = []
    for i, row in enumerate(rows, start=2):  # ヘッダー行=1なのでデータは2行目から
        try:
            speaker_id = int(row["representative_speaker_id"])
        except ValueError as e:
            raise click.ClickException(
                f"{i}行目: representative_speaker_idが整数ではありません: "
                f"'{row['representative_speaker_id']}'"
            ) from e
        csv_rows.append(
            GovernmentOfficialCsvRow(
                speaker_name=row["speaker_name"],
                representative_speaker_id=speaker_id,
                organization=row["organization"],
                position=row["position"],
                notes=row.get("notes") or None,
            )
        )

    # DIコンテナ取得
    try:
        container = get_container()
    except RuntimeError:
        container = init_container()

    usecase = container.use_cases.import_government_officials_csv_usecase()

    input_dto = ImportGovernmentOfficialsCsvInputDto(rows=csv_rows, dry_run=dry_run)
    result = await usecase.execute(input_dto)

    _show_summary(result)


def _read_csv(csv_path: Path) -> list[dict[str, str]]:
    """CSVファイルを読み込み、必須カラムを検証する."""
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise click.ClickException("CSVファイルのヘッダーを読み取れません。")

        actual_columns = set(reader.fieldnames)
        missing = REQUIRED_COLUMNS - actual_columns
        if missing:
            raise click.ClickException(
                f"CSVに必須カラムがありません: {', '.join(sorted(missing))}"
            )

        return list(reader)


def _show_summary(result: ImportGovernmentOfficialsCsvOutputDto) -> None:
    click.echo("=== インポート結果 ===")
    click.echo(f"  作成した政府関係者数: {result.created_officials_count:,}")
    click.echo(f"  作成した役職数:       {result.created_positions_count:,}")
    click.echo(f"  紐付けた発言者数:     {result.linked_speakers_count:,}")
    click.echo(f"  スキップ数:           {result.skipped_count:,}")

    if result.errors:
        click.echo(f"\n  --- エラー ({len(result.errors)}件) ---")
        for err in result.errors[:10]:
            click.echo(f"    - {err}")
        if len(result.errors) > 10:
            click.echo(f"    ... 他 {len(result.errors) - 10} 件")
