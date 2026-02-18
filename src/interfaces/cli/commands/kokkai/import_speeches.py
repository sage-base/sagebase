"""国会会議録API バッチインポートコマンド."""

from __future__ import annotations

import asyncio
import time

from typing import TYPE_CHECKING

import click

from src.interfaces.cli.base import with_error_handling


if TYPE_CHECKING:
    from src.application.dtos.kokkai_speech_dto import (
        BatchImportKokkaiSpeechesOutputDTO,
    )


@click.command()
@click.option("--session-from", type=int, default=None, help="開始回次")
@click.option("--session-to", type=int, default=None, help="終了回次")
@click.option(
    "--name-of-house",
    type=str,
    default=None,
    help="院名（衆議院/参議院）",
)
@click.option(
    "--name-of-meeting",
    type=str,
    default=None,
    help="会議名",
)
@click.option(
    "--sleep",
    "sleep_interval",
    type=float,
    default=2.0,
    help="APIコール間のスリープ秒数",
)
@click.option(
    "--dry-run", is_flag=True, help="対象会議一覧のみ表示（インポートしない）"
)
@with_error_handling
def import_speeches(
    session_from: int | None,
    session_to: int | None,
    name_of_house: str | None,
    name_of_meeting: str | None,
    sleep_interval: float,
    dry_run: bool,
):
    """国会発言データをバッチインポートする."""
    asyncio.run(
        _run_import(
            session_from,
            session_to,
            name_of_house,
            name_of_meeting,
            sleep_interval,
            dry_run,
        )
    )


async def _run_import(
    session_from: int | None,
    session_to: int | None,
    name_of_house: str | None,
    name_of_meeting: str | None,
    sleep_interval: float,
    dry_run: bool,
) -> None:
    from src.application.dtos.kokkai_speech_dto import (
        BatchImportKokkaiSpeechesInputDTO,
    )
    from src.infrastructure.di.container import get_container, init_container

    try:
        container = get_container()
    except RuntimeError:
        container = init_container()

    usecase = container.use_cases.batch_import_kokkai_speeches_usecase()

    input_dto = BatchImportKokkaiSpeechesInputDTO(
        name_of_house=name_of_house,
        name_of_meeting=name_of_meeting,
        session_from=session_from,
        session_to=session_to,
        sleep_interval=sleep_interval,
    )

    if dry_run:
        click.echo("=== ドライラン: 対象会議一覧 ===")
        meetings = await usecase.fetch_target_meetings(input_dto)
        if not meetings:
            click.echo("対象会議が見つかりません。")
            return
        for i, m in enumerate(meetings, 1):
            click.echo(
                f"  {i:>4}. [{m.session}] {m.name_of_house} {m.name_of_meeting}"
                f" {m.issue} ({m.date})"
            )
        click.echo(f"\n合計: {len(meetings)} 件")
        return

    click.echo("=== 国会発言バッチインポート開始 ===")
    _show_params(
        session_from, session_to, name_of_house, name_of_meeting, sleep_interval
    )

    start_time = time.monotonic()

    def progress_callback(current: int, total: int, label: str) -> None:
        click.echo(f"  [{current + 1}/{total}] {label}")

    result = await usecase.execute(input_dto, progress_callback=progress_callback)

    elapsed = time.monotonic() - start_time
    _show_summary(result, elapsed)


def _show_params(
    session_from: int | None,
    session_to: int | None,
    name_of_house: str | None,
    name_of_meeting: str | None,
    sleep_interval: float,
) -> None:
    if session_from or session_to:
        s_from = session_from or "?"
        s_to = session_to or "?"
        click.echo(f"  回次: {s_from} 〜 {s_to}")
    if name_of_house:
        click.echo(f"  院名: {name_of_house}")
    if name_of_meeting:
        click.echo(f"  会議名: {name_of_meeting}")
    click.echo(f"  スリープ: {sleep_interval}s")
    click.echo()


def _show_summary(
    result: BatchImportKokkaiSpeechesOutputDTO,
    elapsed: float,
) -> None:
    click.echo("\n=== インポート結果 ===")
    click.echo(f"  検出会議数:     {result.total_meetings_found:,}")
    click.echo(f"  処理会議数:     {result.total_meetings_processed:,}")
    click.echo(f"  スキップ会議数: {result.total_meetings_skipped:,}")
    click.echo(f"  インポート発言数: {result.total_speeches_imported:,}")
    click.echo(f"  スキップ発言数:   {result.total_speeches_skipped:,}")
    click.echo(f"  新規発言者数:   {result.total_speakers_created:,}")
    click.echo(f"  所要時間:       {elapsed:.1f}s")

    if result.session_progress:
        click.echo("\n  --- 回次別進捗 ---")
        for sp in result.session_progress:
            click.echo(
                f"    第{sp.session}回: "
                f"{sp.meetings_processed}処理 / {sp.meetings_skipped}スキップ / "
                f"{sp.speeches_imported}件インポート"
            )

    if result.errors:
        click.echo(f"\n  --- エラー ({len(result.errors)}件) ---")
        for err in result.errors[:10]:
            click.echo(f"    - {err}")
        if len(result.errors) > 10:
            click.echo(f"    ... 他 {len(result.errors) - 10} 件")

    if result.failed_meetings:
        click.echo(f"\n  --- 失敗会議 ({len(result.failed_meetings)}件) ---")
        for fm in result.failed_meetings[:10]:
            click.echo(
                f"    - [{fm.session}] {fm.name_of_house} {fm.name_of_meeting}"
                f" ({fm.date}): {fm.error_message}"
            )
        if len(result.failed_meetings) > 10:
            click.echo(f"    ... 他 {len(result.failed_meetings) - 10} 件")
