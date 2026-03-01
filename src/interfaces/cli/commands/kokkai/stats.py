"""国会発言データ統計コマンド."""

import asyncio

import click

from src.interfaces.cli.base import with_error_handling


@click.command()
@click.option("--limit", type=int, default=20, help="未紐付け発言者の表示上限")
@with_error_handling
def stats(limit: int):
    """発言者マッチ率・未紐付け発言者一覧を表示する."""
    asyncio.run(_run_stats(limit))


async def _run_stats(limit: int) -> None:
    from src.infrastructure.di.container import get_container, init_container

    try:
        container = get_container()
    except RuntimeError:
        container = init_container()

    speaker_repo = container.repositories.speaker_repository()

    stat = await speaker_repo.get_speaker_politician_stats()

    click.echo("=== 発言者-政治家マッチ統計 ===")
    total = stat.get("total_speakers", 0)
    linked = stat.get("linked_speakers", 0)
    unlinked = stat.get("unlinked_speakers", 0)
    match_rate = stat.get("match_rate", 0.0)

    click.echo(f"  発言者総数:     {total:,}")
    click.echo(f"  紐付け済み:     {linked:,}")
    click.echo(f"  未紐付け:       {unlinked:,}")
    click.echo(f"  マッチ率:       {match_rate:.1f}%")

    # skip_reason別内訳
    skip_reason_breakdown = stat.get("skip_reason_breakdown", {})
    if skip_reason_breakdown:
        non_politician = stat.get("non_politician_speakers", 0)
        click.echo(f"\n=== 非政治家 skip_reason 別内訳 (全{non_politician}件) ===")
        reason_labels = {
            "role_only": "ROLE_ONLY（役職のみ）",
            "reference_person": "REFERENCE_PERSON（参考人等）",
            "government_official": "GOVERNMENT_OFFICIAL（政府側）",
            "other_non_politician": "OTHER_NON_POLITICIAN（その他）",
            "homonym": "HOMONYM（同姓同名）",
            "未分類": "未分類",
        }
        for reason, cnt in skip_reason_breakdown.items():
            label = reason_labels.get(reason, reason)
            click.echo(f"  {label}: {cnt:>8,}件")

    unlinked_speakers = await speaker_repo.get_speakers_not_linked_to_politicians()

    if unlinked_speakers:
        display_count = min(limit, len(unlinked_speakers))
        total_unlinked = len(unlinked_speakers)
        click.echo(
            f"\n=== 未紐付け発言者 (上位{display_count}件 / 全{total_unlinked}件) ==="
        )
        for i, sp in enumerate(unlinked_speakers[:limit], 1):
            party = f" [{sp.political_party_name}]" if sp.political_party_name else ""
            click.echo(f"  {i:>4}. {sp.name}{party}")
    else:
        click.echo("\n未紐付け発言者はいません。")
