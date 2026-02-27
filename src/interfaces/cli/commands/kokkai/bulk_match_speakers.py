"""バルクマッチング CLI コマンド."""

from __future__ import annotations

import asyncio
import time

from dataclasses import dataclass, field
from datetime import date

import click

from src.interfaces.cli.base import with_error_handling


# 国会の governing_body_id
_KOKKAI_GOVERNING_BODY_ID = 1


@dataclass
class TermStats:
    """回次別の集計データ."""

    label: str
    matched: int = 0
    total: int = 0
    skipped: int = 0


@dataclass
class BulkMatchSummary:
    """バルクマッチング結果サマリー."""

    total_meetings: int = 0
    total_speakers: int = 0
    total_matched: int = 0
    total_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    term_stats: dict[str, TermStats] = field(default_factory=dict)


@click.command("bulk-match-speakers")
@click.option(
    "--chamber",
    required=True,
    type=click.Choice(["衆議院", "参議院"]),
    help="院名",
)
@click.option(
    "--date-from",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="開始日 (YYYY-MM-DD)",
)
@click.option(
    "--date-to",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="終了日 (YYYY-MM-DD)",
)
@click.option(
    "--confidence-threshold",
    type=float,
    default=0.8,
    help="マッチング閾値",
)
@click.option("--dry-run", is_flag=True, help="対象会議一覧のみ表示")
@with_error_handling
def bulk_match_speakers(
    chamber: str,
    date_from: click.DateTime,
    date_to: click.DateTime,
    confidence_threshold: float,
    dry_run: bool,
) -> None:
    """全会議の発言者を一括マッチングする."""
    asyncio.run(
        _run_bulk_match(
            chamber,
            date_from.date(),  # type: ignore[union-attr]
            date_to.date(),  # type: ignore[union-attr]
            confidence_threshold,
            dry_run,
        )
    )


async def _run_bulk_match(
    chamber: str,
    date_from: date,
    date_to: date,
    confidence_threshold: float,
    dry_run: bool,
) -> None:
    from src.application.dtos.match_meeting_speakers_dto import (
        MatchMeetingSpeakersInputDTO,
    )
    from src.domain.services.election_domain_service import ElectionDomainService
    from src.infrastructure.di.container import get_container, init_container

    try:
        container = get_container()
    except RuntimeError:
        container = init_container()

    meeting_repo = container.repositories.meeting_repository()
    election_repo = container.repositories.election_repository()
    usecase = container.use_cases.match_meeting_speakers_usecase()

    meetings = await meeting_repo.get_by_chamber_and_date_range(
        chamber, date_from, date_to
    )

    if not meetings:
        click.echo("対象会議が見つかりません。")
        return

    if dry_run:
        click.echo("=== ドライラン: 対象会議一覧 ===")
        click.echo(f"  院: {chamber}")
        click.echo(f"  期間: {date_from} 〜 {date_to}")
        click.echo(f"  閾値: {confidence_threshold}")
        click.echo()
        for i, m in enumerate(meetings, 1):
            click.echo(f"  {i:>4}. [{m.date}] {m.name} (id={m.id})")
        click.echo(f"\n合計: {len(meetings)} 件")
        return

    click.echo("=== バルクマッチング開始 ===")
    click.echo(f"  院: {chamber}")
    click.echo(f"  期間: {date_from} 〜 {date_to}")
    click.echo(f"  閾値: {confidence_threshold}")
    click.echo(f"  対象会議数: {len(meetings)}")
    click.echo()

    start_time = time.monotonic()
    summary = BulkMatchSummary()

    # 選挙一覧を取得（回次レポート用）
    elections = await election_repo.get_by_governing_body(_KOKKAI_GOVERNING_BODY_ID)
    election_service = ElectionDomainService()

    for i, meeting in enumerate(meetings, 1):
        if not meeting.id or not meeting.date:
            continue

        input_dto = MatchMeetingSpeakersInputDTO(
            meeting_id=meeting.id,
            confidence_threshold=confidence_threshold,
        )

        try:
            result = await usecase.execute(input_dto)
        except Exception as e:
            summary.errors.append(f"{meeting.name} ({meeting.date}): {e!s}")
            click.echo(
                f"  [{i}/{len(meetings)}] {meeting.name} {meeting.date} → エラー: {e!s}"
            )
            continue

        summary.total_meetings += 1

        matched = result.matched_count
        skipped = result.skipped_count
        total = result.total_speakers
        summary.total_speakers += total
        summary.total_matched += matched
        summary.total_skipped += skipped

        click.echo(
            f"  [{i}/{len(meetings)}] {meeting.name} {meeting.date}"
            f" → {matched}件マッチ / {total}件対象"
        )

        if not result.success:
            summary.errors.append(f"{meeting.name} ({meeting.date}): {result.message}")

        # 回次別集計
        election = election_service.get_active_election_at_date(
            elections, meeting.date, chamber
        )
        term_label = f"第{election.term_number}回" if election else "不明"
        if term_label not in summary.term_stats:
            summary.term_stats[term_label] = TermStats(label=term_label)
        summary.term_stats[term_label].matched += matched
        summary.term_stats[term_label].total += total
        summary.term_stats[term_label].skipped += skipped

    elapsed = time.monotonic() - start_time
    _show_summary(summary, elapsed)


def _show_summary(summary: BulkMatchSummary, elapsed: float) -> None:
    active_speakers = summary.total_speakers - summary.total_skipped
    match_rate = (
        (summary.total_matched / active_speakers * 100) if active_speakers > 0 else 0.0
    )

    click.echo("\n=== 結果サマリー ===")
    click.echo(f"  処理会議数: {summary.total_meetings}")
    click.echo(f"  総Speaker数: {summary.total_speakers}")
    click.echo(f"  マッチ数: {summary.total_matched}")
    click.echo(f"  スキップ数: {summary.total_skipped} (既マッチ)")
    click.echo(f"  マッチ率: {match_rate:.1f}%")
    click.echo(f"  所要時間: {elapsed:.1f}s")

    if summary.term_stats:
        click.echo("\n  --- 回次別マッチ率 ---")
        for term_label in sorted(summary.term_stats):
            stats = summary.term_stats[term_label]
            active = stats.total - stats.skipped
            rate = (stats.matched / active * 100) if active > 0 else 0.0
            click.echo(
                f"    {stats.label}: {stats.matched}マッチ / {active}対象 ({rate:.1f}%)"
            )

    if summary.errors:
        click.echo(f"\n  --- エラー ({len(summary.errors)}件) ---")
        for err in summary.errors[:10]:
            click.echo(f"    - {err}")
        if len(summary.errors) > 10:
            click.echo(f"    ... 他 {len(summary.errors) - 10} 件")
