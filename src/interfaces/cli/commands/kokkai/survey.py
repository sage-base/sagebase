"""国会会議録API 事前調査コマンド."""

from __future__ import annotations

import asyncio
import time

from typing import TYPE_CHECKING

import click

from src.interfaces.cli.base import with_error_handling


if TYPE_CHECKING:
    from src.infrastructure.external.kokkai_api.client import KokkaiApiClient


@click.command()
@click.option("--session-from", type=int, default=1, help="開始回次（デフォルト: 1）")
@click.option(
    "--session-to", type=int, default=None, help="終了回次（デフォルト: 最新）"
)
@click.option(
    "--name-of-house",
    type=str,
    default=None,
    help="院名（衆議院/参議院）",
)
@click.option(
    "--sleep",
    "sleep_interval",
    type=float,
    default=1.0,
    help="APIコール間のスリープ秒数",
)
@with_error_handling
def survey(
    session_from: int,
    session_to: int | None,
    name_of_house: str | None,
    sleep_interval: float,
):
    """回次ごとの会議数・発言数を事前調査する."""
    asyncio.run(_run_survey(session_from, session_to, name_of_house, sleep_interval))


async def _run_survey(
    session_from: int,
    session_to: int | None,
    name_of_house: str | None,
    sleep_interval: float,
) -> None:
    from src.infrastructure.external.kokkai_api.client import KokkaiApiClient

    client = KokkaiApiClient()

    if session_to is None:
        session_to = await _detect_latest_session(client, sleep_interval)

    click.echo(f"調査範囲: 第{session_from}回 〜 第{session_to}回")
    if name_of_house:
        click.echo(f"院名: {name_of_house}")
    click.echo()

    header = f"{'回次':>6}  {'会議数':>8}  {'発言数':>10}"
    click.echo(header)
    click.echo("-" * len(header))

    total_meetings = 0
    total_speeches = 0
    start_time = time.monotonic()

    for session in range(session_from, session_to + 1):
        meeting_resp = await client.search_meetings(
            session_from=session,
            session_to=session,
            name_of_house=name_of_house,
            maximum_records=1,
        )
        meeting_count = meeting_resp.number_of_records

        if sleep_interval > 0:
            await asyncio.sleep(sleep_interval)

        speech_resp = await client.search_speeches(
            session_from=session,
            session_to=session,
            name_of_house=name_of_house,
            maximum_records=1,
        )
        speech_count = speech_resp.number_of_records

        if meeting_count > 0 or speech_count > 0:
            click.echo(f"{session:>6}  {meeting_count:>8,}  {speech_count:>10,}")

        total_meetings += meeting_count
        total_speeches += speech_count

        if sleep_interval > 0 and session < session_to:
            await asyncio.sleep(sleep_interval)

    elapsed = time.monotonic() - start_time
    click.echo("-" * len(header))
    click.echo(f"{'合計':>6}  {total_meetings:>8,}  {total_speeches:>10,}")
    click.echo(f"\n調査完了 ({elapsed:.1f}s)")


async def _detect_latest_session(
    client: KokkaiApiClient,
    sleep_interval: float,
) -> int:
    """最新の回次を二分探索で検出する."""
    low, high = 1, 220
    latest = low
    while low <= high:
        mid = (low + high) // 2
        resp = await client.search_meetings(
            session_from=mid, session_to=mid, maximum_records=1
        )
        if resp.number_of_records > 0:
            latest = mid
            low = mid + 1
        else:
            high = mid - 1
        if sleep_interval > 0:
            await asyncio.sleep(sleep_interval)
    click.echo(f"最新回次を検出: 第{latest}回")
    return latest
