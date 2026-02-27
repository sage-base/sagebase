"""国会会議録API CLI コマンドグループ."""

import click

from src.interfaces.cli.commands.kokkai.bulk_match_speakers import bulk_match_speakers
from src.interfaces.cli.commands.kokkai.import_speeches import import_speeches
from src.interfaces.cli.commands.kokkai.stats import stats
from src.interfaces.cli.commands.kokkai.survey import survey


@click.group()
def kokkai():
    """国会会議録API関連コマンド."""
    pass


kokkai.add_command(survey)
kokkai.add_command(import_speeches, "import")
kokkai.add_command(stats)
kokkai.add_command(bulk_match_speakers, "bulk-match-speakers")
