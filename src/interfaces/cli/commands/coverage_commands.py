"""Coverage reporting commands for Polibase"""

import asyncio

import click

from sqlalchemy import text

from src.domain.services.data_coverage_domain_service import DataCoverageDomainService
from src.interfaces.cli.base import ensure_container


def get_coverage_commands() -> list[click.Command]:
    """Get all coverage-related commands

    Returns:
        List of Click commands
    """
    return [coverage, coverage_stats]


@click.command()
def coverage():
    """Show data coverage statistics for governing bodies."""
    container = ensure_container()

    engine = container.database.engine()

    with engine.connect() as conn:
        # Total governing bodies
        result = conn.execute(text("SELECT COUNT(*) FROM governing_bodies"))
        total_governing_bodies = result.scalar()

        # Total governing bodies by type
        type_stats = conn.execute(
            text("""
            SELECT type, organization_type, COUNT(*) as count
            FROM governing_bodies
            GROUP BY type, organization_type
            ORDER BY type, organization_type
        """)
        ).fetchall()

        # Governing bodies with conferences
        result = conn.execute(
            text("""
            SELECT COUNT(DISTINCT governing_body_id)
            FROM conferences
        """)
        )
        bodies_with_conferences = result.scalar()

        # Governing bodies with meetings
        result = conn.execute(
            text("""
            SELECT COUNT(DISTINCT c.governing_body_id)
            FROM meetings m
            JOIN conferences c ON m.conference_id = c.id
        """)
        )
        bodies_with_meetings = result.scalar()

        # Coverage percentage
        if bodies_with_conferences is not None and total_governing_bodies is not None:
            conference_coverage = (
                (bodies_with_conferences / total_governing_bodies * 100)
                if total_governing_bodies > 0
                else 0
            )
        else:
            conference_coverage = 0

        if bodies_with_meetings is not None and total_governing_bodies is not None:
            meeting_coverage = (
                (bodies_with_meetings / total_governing_bodies * 100)
                if total_governing_bodies > 0
                else 0
            )
        else:
            meeting_coverage = 0

        # Display results
        click.echo("=== Governing Bodies Coverage Report ===\n")

        click.echo(f"Total governing bodies: {total_governing_bodies:,}")
        click.echo(
            f"Bodies with conferences: {bodies_with_conferences:,} "
            f"({conference_coverage:.1f}%)"
        )
        click.echo(
            f"Bodies with meetings: {bodies_with_meetings:,} "
            f"({meeting_coverage:.1f}%)\n"
        )

        click.echo("Breakdown by type:")
        click.echo("-" * 50)
        click.echo(f"{'Type':<15} {'Detail':<15} {'Count':>10}")
        click.echo("-" * 50)

        for stat in type_stats:
            org_type = stat.organization_type or "N/A"
            click.echo(f"{stat.type:<15} {org_type:<15} {stat.count:>10,}")

        # Show some uncovered bodies as examples
        uncovered_bodies = conn.execute(
            text("""
            SELECT gb.name, gb.organization_code, gb.organization_type
            FROM governing_bodies gb
            LEFT JOIN conferences c ON gb.id = c.governing_body_id
            WHERE c.id IS NULL
            LIMIT 10
        """)
        ).fetchall()

        if uncovered_bodies:
            click.echo("\nExample governing bodies without conferences:")
            click.echo("-" * 50)
            for body in uncovered_bodies:
                click.echo(
                    f"- {body.name} ({body.organization_type}, "
                    f"code: {body.organization_code})"
                )


@click.command("coverage-stats")
def coverage_stats():
    """Show comprehensive data coverage statistics using DataCoverageDomainService."""
    container = ensure_container()

    # Get repositories from container
    governing_body_repo = container.repositories.governing_body_repository()
    conference_repo = container.repositories.conference_repository()
    meeting_repo = container.repositories.meeting_repository()
    minutes_repo = container.repositories.minutes_repository()
    speaker_repo = container.repositories.speaker_repository()
    politician_repo = container.repositories.politician_repository()
    conversation_repo = container.repositories.conversation_repository()

    # Create domain service
    service = DataCoverageDomainService(
        governing_body_repo=governing_body_repo,
        conference_repo=conference_repo,
        meeting_repo=meeting_repo,
        minutes_repo=minutes_repo,
        speaker_repo=speaker_repo,
        politician_repo=politician_repo,
        conversation_repo=conversation_repo,
    )

    # Execute async operations
    async def run_stats():
        # Calculate all statistics
        gov_body_coverage = await service.calculate_governing_body_coverage()
        meeting_coverage = await service.calculate_meeting_coverage()
        speaker_matching = await service.calculate_speaker_matching_rate()
        activity_stats = await service.aggregate_activity_statistics()

        # Display results
        click.echo("=" * 70)
        click.echo("📊 Polibase Data Coverage Statistics")
        click.echo("=" * 70)

        # Governing Body Coverage
        click.echo("\n🏛️  自治体カバレッジ")
        click.echo("-" * 70)
        click.echo(f"全国自治体数: {gov_body_coverage['total']:,} (全国の市町村数)")
        click.echo(
            f"登録自治体数: {gov_body_coverage['registered']:,} "
            f"({gov_body_coverage['coverage_rate']:.2f}%)"
        )

        # Meeting Coverage
        click.echo("\n📋 会議カバレッジ")
        click.echo("-" * 70)
        click.echo(f"登録自治体数: {meeting_coverage['total_governing_bodies']:,}")
        click.echo(
            f"会議体を持つ自治体: {meeting_coverage['bodies_with_conferences']:,} "
            f"({meeting_coverage['conference_coverage_rate']:.2f}%)"
        )
        click.echo(
            f"会議を持つ自治体: {meeting_coverage['bodies_with_meetings']:,} "
            f"({meeting_coverage['meeting_coverage_rate']:.2f}%)"
        )

        # Speaker Matching
        click.echo("\n🔗 Speaker-Politician 紐付け率")
        click.echo("-" * 70)
        click.echo(f"全Speaker数: {speaker_matching['total_speakers']:,}")
        click.echo(
            f"紐付け済み: {speaker_matching['linked_speakers']:,} "
            f"({speaker_matching['overall_matching_rate']:.2f}%)"
        )
        click.echo(f"未紐付け: {speaker_matching['unlinked_speakers']:,}")
        click.echo(f"\n政治家Speaker数: {speaker_matching['politician_speakers']:,}")
        click.echo(
            f"紐付け済み: {speaker_matching['linked_politician_speakers']:,} "
            f"({speaker_matching['politician_matching_rate']:.2f}%)"
        )

        # Activity Statistics
        click.echo("\n📈 活動統計")
        click.echo("-" * 70)
        click.echo(f"会議体数: {activity_stats['total_conferences']:,}")
        click.echo(f"会議数: {activity_stats['total_meetings']:,}")
        click.echo(
            f"議事録数: {activity_stats['total_minutes']:,} "
            f"(処理済み: {activity_stats['processed_minutes']:,}, "
            f"未処理: {activity_stats['unprocessed_minutes']:,})"
        )
        click.echo(
            f"議事録処理完了率: {activity_stats['minutes_processing_rate']:.2f}%"
        )
        click.echo(f"発言数: {activity_stats['total_conversations']:,}")
        click.echo(f"政治家数: {activity_stats['total_politicians']:,}")

        click.echo("\n" + "=" * 70)

    asyncio.run(run_stats())
