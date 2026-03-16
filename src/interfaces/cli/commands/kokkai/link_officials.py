"""政府関係者紐付けコマンド."""

from __future__ import annotations

import asyncio

from typing import TYPE_CHECKING

import click

from src.interfaces.cli.base import with_error_handling


if TYPE_CHECKING:
    from src.application.usecases.batch_link_speakers_to_government_officials_usecase import (  # noqa: E501
        BatchLinkOutputDto,
    )


@click.command()
@click.option("--dry-run", is_flag=True, help="実際には紐付けせず候補を確認する")
@with_error_handling
def link_officials(dry_run: bool):
    """未紐付きSpeakerとGovernmentOfficialを名前正規化で一括紐付けする."""
    asyncio.run(_run_link_officials(dry_run))


async def _run_link_officials(dry_run: bool) -> None:
    from src.infrastructure.di.container import get_container, init_container

    label = "政府関係者紐付け (ドライラン)" if dry_run else "政府関係者紐付け"
    click.echo(f"=== {label} ===")
    click.echo()

    # DIコンテナ取得
    try:
        container = get_container()
    except RuntimeError:
        container = init_container()

    usecase = container.use_cases.batch_link_speakers_to_government_officials_usecase()
    result = await usecase.execute(dry_run=dry_run)

    _show_summary(result)


def _show_summary(result: BatchLinkOutputDto) -> None:
    click.echo("=== 紐付け結果 ===")
    click.echo(f"  紐付け数:   {result.linked_count:,}")
    click.echo(f"  スキップ数: {result.skipped_count:,}")

    if result.details:
        click.echo()
        click.echo("  --- 紐付け詳細 ---")
        for d in result.details:
            click.echo(
                f"    政府関係者: {d.government_official_name}"
                f" <-> 発言者: {d.speaker_name}"
                f" (正規化名: {d.normalized_name})"
            )
