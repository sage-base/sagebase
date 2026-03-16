"""未分類Speaker（政治家・官僚いずれにも未紐付け）をエクスポートするコマンド."""

import asyncio
import csv
import sys

import click

from src.interfaces.cli.base import with_error_handling


@click.command("export-unclassified-speakers")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "csv"]),
    default="table",
    help="出力形式（table or csv）",
)
@click.option(
    "--limit", type=click.IntRange(min=1), default=None, help="出力件数の上限"
)
@click.option(
    "--min-conversations",
    type=click.IntRange(min=0),
    default=None,
    help="最低発言数フィルタ",
)
@with_error_handling
def export_unclassified_speakers(
    output_format: str,
    limit: int | None,
    min_conversations: int | None,
) -> None:
    """未分類Speaker（政治家・官僚いずれにも未紐付け）を発言数降順でエクスポートする."""
    asyncio.run(_run_export(output_format, limit, min_conversations))


async def _run_export(
    output_format: str,
    limit: int | None,
    min_conversations: int | None,
) -> None:
    from src.infrastructure.di.container import get_container, init_container

    try:
        container = get_container()
    except RuntimeError:
        container = init_container()

    speaker_repo = container.repositories.speaker_repository()

    speakers = await speaker_repo.get_speakers_with_conversation_count(
        has_politician_id=False,
        has_government_official_id=False,
        min_conversation_count=min_conversations,
        limit=limit,
    )

    if not speakers:
        click.echo("対象の未分類Speakerはいません。")
        return

    if output_format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(["speaker_id", "name", "conversation_count"])
        for s in speakers:
            writer.writerow([s.id, s.name, s.conversation_count])
    else:
        click.echo(f"{'ID':>8}  {'名前':<30}  {'発言数':>8}")
        click.echo("-" * 52)
        for s in speakers:
            click.echo(f"{s.id:>8}  {s.name:<30}  {s.conversation_count:>8}")
        click.echo(f"\n合計: {len(speakers)}件")
