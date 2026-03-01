"""バルクマッチング CLI コマンド."""

from __future__ import annotations

import asyncio
import time

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import click

from src.domain.constants import KOKKAI_GOVERNING_BODY_ID
from src.interfaces.cli.base import with_error_handling


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
    total_baml_matched: int = 0
    total_non_politician: int = 0
    total_review_matched: int = 0
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
@click.option(
    "--enable-baml-fallback",
    is_flag=True,
    default=False,
    help="ルールベース未マッチ時にBAML(LLM)フォールバックを有効にする",
)
@click.option(
    "--wide-match",
    is_flag=True,
    default=False,
    help="ConferenceMember非依存の広域マッチングを使用（1947-2007年対応）",
)
@with_error_handling
def bulk_match_speakers(
    chamber: str,
    date_from: click.DateTime,
    date_to: click.DateTime,
    confidence_threshold: float,
    dry_run: bool,
    enable_baml_fallback: bool,
    wide_match: bool,
) -> None:
    """全会議の発言者を一括マッチングする."""
    asyncio.run(
        _run_bulk_match(
            chamber,
            date_from.date(),  # type: ignore[union-attr]
            date_to.date(),  # type: ignore[union-attr]
            confidence_threshold,
            dry_run,
            enable_baml_fallback,
            wide_match,
        )
    )


async def _run_bulk_match(
    chamber: str,
    date_from: date,
    date_to: date,
    confidence_threshold: float,
    dry_run: bool,
    enable_baml_fallback: bool = False,
    wide_match: bool = False,
) -> None:
    from src.domain.services.election_domain_service import ElectionDomainService
    from src.infrastructure.di.container import get_container, init_container

    try:
        container = get_container()
    except RuntimeError:
        container = init_container()

    meeting_repo = container.repositories.meeting_repository()
    election_repo = container.repositories.election_repository()

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
        click.echo(f"  広域マッチング: {'有効' if wide_match else '無効'}")
        click.echo()
        for i, m in enumerate(meetings, 1):
            click.echo(f"  {i:>4}. [{m.date}] {m.name} (id={m.id})")
        click.echo(f"\n合計: {len(meetings)} 件")
        return

    mode_label = "広域マッチング" if wide_match else "バルクマッチング"
    click.echo(f"=== {mode_label}開始 ===")
    click.echo(f"  院: {chamber}")
    click.echo(f"  期間: {date_from} 〜 {date_to}")
    click.echo(f"  閾値: {confidence_threshold}")
    click.echo(f"  BAMLフォールバック: {'有効' if enable_baml_fallback else '無効'}")
    if wide_match:
        click.echo("  モード: 広域マッチング（ConferenceMember非依存）")
    click.echo(f"  対象会議数: {len(meetings)}")
    click.echo()

    start_time = time.monotonic()
    summary = BulkMatchSummary()

    # 選挙一覧を取得（回次レポート用）
    elections = await election_repo.get_by_governing_body(KOKKAI_GOVERNING_BODY_ID)
    election_service = ElectionDomainService()

    if wide_match:
        await _run_wide_match_loop(
            container,
            meetings,
            confidence_threshold,
            enable_baml_fallback,
            summary,
            elections,
            election_service,
            chamber,
        )
    else:
        await _run_standard_match_loop(
            container,
            meetings,
            confidence_threshold,
            enable_baml_fallback,
            summary,
            elections,
            election_service,
            chamber,
        )

    elapsed = time.monotonic() - start_time
    _show_summary(summary, elapsed, wide_match)


async def _run_standard_match_loop(
    container: Any,
    meetings: list[Any],
    confidence_threshold: float,
    enable_baml_fallback: bool,
    summary: BulkMatchSummary,
    elections: list[Any],
    election_service: Any,
    chamber: str,
) -> None:
    """既存のConferenceMemberベースマッチングループ."""
    from src.application.dtos.match_meeting_speakers_dto import (
        MatchMeetingSpeakersInputDTO,
    )

    usecase = container.use_cases.match_meeting_speakers_usecase()

    for i, meeting in enumerate(meetings, 1):
        if not meeting.id or not meeting.date:
            continue

        input_dto = MatchMeetingSpeakersInputDTO(
            meeting_id=meeting.id,
            confidence_threshold=confidence_threshold,
            enable_baml_fallback=enable_baml_fallback,
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
        summary.total_baml_matched += result.baml_matched_count
        summary.total_non_politician += result.non_politician_count

        click.echo(
            f"  [{i}/{len(meetings)}] {meeting.name} {meeting.date}"
            f" → {matched}件マッチ / {total}件対象"
        )

        if not result.success:
            summary.errors.append(f"{meeting.name} ({meeting.date}): {result.message}")

        _update_term_stats(
            summary,
            elections,
            election_service,
            meeting,
            matched,
            total,
            skipped,
            chamber,
        )


async def _run_wide_match_loop(
    container: Any,
    meetings: list[Any],
    confidence_threshold: float,
    enable_baml_fallback: bool,
    summary: BulkMatchSummary,
    elections: list[Any],
    election_service: Any,
    chamber: str,
) -> None:
    """広域マッチング（ConferenceMember非依存）ループ."""
    from src.application.dtos.wide_match_speakers_dto import WideMatchSpeakersInputDTO

    usecase = container.use_cases.wide_match_speakers_usecase()

    for i, meeting in enumerate(meetings, 1):
        if not meeting.id or not meeting.date:
            continue

        input_dto = WideMatchSpeakersInputDTO(
            meeting_id=meeting.id,
            auto_match_threshold=0.9,
            review_threshold=confidence_threshold,
            enable_baml_fallback=enable_baml_fallback,
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
        auto_matched = result.auto_matched_count
        review_matched = result.review_matched_count
        matched = auto_matched + review_matched
        skipped = result.skipped_count
        total = result.total_speakers
        summary.total_speakers += total
        summary.total_matched += matched
        summary.total_skipped += skipped
        summary.total_baml_matched += result.baml_matched_count
        summary.total_non_politician += result.non_politician_count
        summary.total_review_matched += review_matched

        click.echo(
            f"  [{i}/{len(meetings)}] {meeting.name} {meeting.date}"
            f" → 自動{auto_matched} + 検証{review_matched}"
            f" / {total}件対象"
        )

        if not result.success:
            summary.errors.append(f"{meeting.name} ({meeting.date}): {result.message}")

        _update_term_stats(
            summary,
            elections,
            election_service,
            meeting,
            matched,
            total,
            skipped,
            chamber,
        )


def _update_term_stats(
    summary: BulkMatchSummary,
    elections: list[Any],
    election_service: Any,
    meeting: Any,
    matched: int,
    total: int,
    skipped: int,
    chamber: str,
) -> None:
    """回次別集計を更新する."""
    election = election_service.get_active_election_at_date(
        elections, meeting.date, chamber
    )
    term_label = f"第{election.term_number}回" if election else "不明"
    if term_label not in summary.term_stats:
        summary.term_stats[term_label] = TermStats(label=term_label)
    summary.term_stats[term_label].matched += matched
    summary.term_stats[term_label].total += total
    summary.term_stats[term_label].skipped += skipped


def _show_summary(
    summary: BulkMatchSummary, elapsed: float, wide_match: bool = False
) -> None:
    active_speakers = summary.total_speakers - summary.total_skipped
    match_rate = (
        (summary.total_matched / active_speakers * 100) if active_speakers > 0 else 0.0
    )

    click.echo("\n=== 結果サマリー ===")
    click.echo(f"  処理会議数: {summary.total_meetings}")
    click.echo(f"  総Speaker数: {summary.total_speakers}")
    click.echo(f"  マッチ数: {summary.total_matched}")
    if wide_match and summary.total_review_matched > 0:
        auto = summary.total_matched - summary.total_review_matched
        click.echo(f"    自動マッチ: {auto}")
        click.echo(f"    手動検証待ち: {summary.total_review_matched}")
    if summary.total_baml_matched > 0:
        click.echo(f"    うちBAMLマッチ: {summary.total_baml_matched}")
    click.echo(f"  非政治家数: {summary.total_non_politician}")
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
