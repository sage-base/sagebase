"""国会発言データ統計コマンド."""

import asyncio
import json

from typing import Any

import click

from src.domain.services.speaker_classifier import SkipReason
from src.interfaces.cli.base import with_error_handling


@click.command()
@click.option("--limit", type=int, default=20, help="未紐付け発言者の表示上限")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="出力フォーマット",
)
@with_error_handling
def stats(limit: int, output_format: str):
    """発言者マッチ率・未紐付け発言者一覧を表示する."""
    asyncio.run(_run_stats(limit, output_format))


async def _run_stats(limit: int, output_format: str) -> None:
    from src.infrastructure.di.container import get_container, init_container

    try:
        container = get_container()
    except RuntimeError:
        container = init_container()

    speaker_repo = container.repositories.speaker_repository()

    stat = await speaker_repo.get_speaker_politician_stats()
    classification = await speaker_repo.get_speaker_classification_stats()

    if output_format == "json":
        _output_json(stat, classification)
        return

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
        for reason, cnt in skip_reason_breakdown.items():
            try:
                label = SkipReason(reason).display_label
            except ValueError:
                label = reason
            click.echo(f"  {label}: {cnt:>8,}件")

    # Speaker分類サマリ
    _output_classification_summary(classification)

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


def _output_classification_summary(classification: dict[str, Any]) -> None:
    """Speaker分類サマリを表示する."""
    total = classification["total_speakers"]
    total_conv = classification["total_conversations"]
    pol = classification["politician_linked"]
    gov = classification["government_official_linked"]
    unc = classification["unclassified"]

    click.echo("\n=== Speaker分類サマリ ===")
    click.echo(f"全Speaker:              {total:,}")

    for label, data in [
        ("politician紐付済", pol),
        ("government_official", gov),
        ("未分類", unc),
    ]:
        sc = data["speaker_count"]
        cc = data["conversation_count"]
        sp_pct = sc / total * 100 if total > 0 else 0.0
        cc_pct = cc / total_conv * 100 if total_conv > 0 else 0.0
        click.echo(
            f"  {label}: {sc:>12,} ({sp_pct:>5.1f}%)"
            f"  → 発言 {cc:>12,}件 ({cc_pct:>5.1f}%)"
        )

    click.echo(f"\n身元特定率（発言ベース）: {classification['identity_rate']:.1f}%")


def _output_json(stat: dict[str, Any], classification: dict[str, Any]) -> None:
    """JSON形式で全データを出力する."""
    output = {
        "speaker_politician_stats": stat,
        "speaker_classification": classification,
    }
    click.echo(json.dumps(output, ensure_ascii=False, default=str))
