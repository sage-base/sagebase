"""選挙データインポート用CLIコマンド.

衆議院小選挙区・比例代表・参議院の選挙データを
外部データソースからインポートするコマンドを提供する。
"""

from pathlib import Path

import click

from ..base import (
    BaseCommand,
    ensure_container,
    with_async_execution,
    with_error_handling,
)


class ElectionImportCommands(BaseCommand):
    """選挙データインポート用コマンド."""

    @staticmethod
    @click.command()
    @click.option(
        "--term-number",
        type=int,
        required=True,
        help="回次番号（例: 49）",
    )
    @click.option(
        "--governing-body-id",
        type=int,
        required=True,
        help="開催主体ID（国会=1）",
    )
    @click.option(
        "--dry-run/--no-dry-run",
        default=True,
        help="ドライラン（デフォルト: dry-run）",
    )
    @with_error_handling
    @with_async_execution
    async def import_national_election(
        term_number: int,
        governing_body_id: int,
        dry_run: bool,
    ):
        """衆議院小選挙区データをインポート

        総務省のXLSデータソースから候補者データを取得し、
        Election・ElectionMemberレコードを作成します。

        使用例:

            # dry_run（変更なし）
            sagebase import-national-election --term-number 49 --governing-body-id 1

            # 実際にDBを更新
            sagebase import-national-election \\
                --term-number 49 --governing-body-id 1 --no-dry-run
        """
        from src.application.dtos.national_election_import_dto import (
            ImportNationalElectionInputDto,
        )

        mode = "dry_run" if dry_run else "本番"
        ElectionImportCommands.show_progress(
            f"衆議院小選挙区インポート開始（第{term_number}回, {mode}モード）..."
        )

        container = ensure_container()
        usecase = container.use_cases.import_national_election_usecase()

        result = await usecase.execute(
            ImportNationalElectionInputDto(
                election_number=term_number,
                governing_body_id=governing_body_id,
                dry_run=dry_run,
            )
        )

        ElectionImportCommands.show_progress(
            f"\n処理完了:\n"
            f"  候補者総数: {result.total_candidates}\n"
            f"  マッチ: {result.matched_politicians}\n"
            f"  新規政治家: {result.created_politicians}\n"
            f"  新規政党: {result.created_parties}\n"
            f"  同姓同名スキップ: {result.skipped_ambiguous}\n"
            f"  重複スキップ: {result.skipped_duplicate}\n"
            f"  ElectionMember作成: {result.election_members_created}\n"
            f"  エラー: {result.errors}"
        )

        if result.error_details:
            ElectionImportCommands.warning("エラー詳細:")
            for detail in result.error_details[:10]:
                ElectionImportCommands.warning(f"  - {detail}")

        if result.errors == 0:
            ElectionImportCommands.success("インポート完了")
        else:
            ElectionImportCommands.warning(
                f"インポート完了（{result.errors}件のエラー）"
            )

    @staticmethod
    @click.command()
    @click.option(
        "--term-number",
        type=int,
        required=True,
        help="回次番号（例: 49）",
    )
    @click.option(
        "--governing-body-id",
        type=int,
        required=True,
        help="開催主体ID（国会=1）",
    )
    @click.option(
        "--dry-run/--no-dry-run",
        default=True,
        help="ドライラン（デフォルト: dry-run）",
    )
    @with_error_handling
    @with_async_execution
    async def import_proportional_election(
        term_number: int,
        governing_body_id: int,
        dry_run: bool,
    ):
        """比例代表データをインポート

        総務省のデータソースから比例代表候補者データを取得し、
        Election・ElectionMemberレコードを作成します。
        比例復活当選の判定も行います。

        使用例:

            # dry_run
            sagebase import-proportional-election --term-number 49 --governing-body-id 1

            # 実際にDBを更新
            sagebase import-proportional-election \\
                --term-number 49 --governing-body-id 1 --no-dry-run
        """
        from src.application.dtos.proportional_election_import_dto import (
            ImportProportionalElectionInputDto,
        )

        mode = "dry_run" if dry_run else "本番"
        ElectionImportCommands.show_progress(
            f"比例代表インポート開始（第{term_number}回, {mode}モード）..."
        )

        container = ensure_container()
        usecase = container.use_cases.import_proportional_election_usecase()

        result = await usecase.execute(
            ImportProportionalElectionInputDto(
                election_number=term_number,
                governing_body_id=governing_body_id,
                dry_run=dry_run,
            )
        )

        ElectionImportCommands.show_progress(
            f"\n処理完了:\n"
            f"  候補者総数: {result.total_candidates}\n"
            f"  当選: {result.elected_candidates}\n"
            f"  比例当選: {result.proportional_elected}\n"
            f"  比例復活: {result.proportional_revival}\n"
            f"  マッチ: {result.matched_politicians}\n"
            f"  新規政治家: {result.created_politicians}\n"
            f"  新規政党: {result.created_parties}\n"
            f"  小選挙区当選スキップ: {result.skipped_smd_winner}\n"
            f"  同姓同名スキップ: {result.skipped_ambiguous}\n"
            f"  重複スキップ: {result.skipped_duplicate}\n"
            f"  ElectionMember作成: {result.election_members_created}\n"
            f"  エラー: {result.errors}"
        )

        if result.error_details:
            ElectionImportCommands.warning("エラー詳細:")
            for detail in result.error_details[:10]:
                ElectionImportCommands.warning(f"  - {detail}")

        if result.errors == 0:
            ElectionImportCommands.success("インポート完了")
        else:
            ElectionImportCommands.warning(
                f"インポート完了（{result.errors}件のエラー）"
            )

    @staticmethod
    @click.command()
    @click.option(
        "--governing-body-id",
        type=int,
        required=True,
        help="開催主体ID（国会=1）",
    )
    @click.option(
        "--file-path",
        type=click.Path(exists=True, path_type=Path),
        required=True,
        help="giin.jsonファイルのパス",
    )
    @click.option(
        "--dry-run/--no-dry-run",
        default=True,
        help="ドライラン（デフォルト: dry-run）",
    )
    @with_error_handling
    @with_async_execution
    async def import_sangiin_election(
        governing_body_id: int,
        file_path: Path,
        dry_run: bool,
    ):
        """参議院選挙データをインポート

        SmartNews SMRI の giin.json から参議院議員データを読み込み、
        当選年ごとにElection・ElectionMemberレコードを作成します。

        使用例:

            # dry_run
            sagebase import-sangiin-election \\
                --governing-body-id 1 --file-path tmp/giin.json

            # 実際にDBを更新
            sagebase import-sangiin-election \\
                --governing-body-id 1 --file-path tmp/giin.json --no-dry-run
        """
        from src.application.dtos.sangiin_election_import_dto import (
            ImportSangiinElectionInputDto,
        )

        mode = "dry_run" if dry_run else "本番"
        ElectionImportCommands.show_progress(
            f"参議院選挙インポート開始（{mode}モード, ファイル: {file_path}）..."
        )

        container = ensure_container()
        usecase = container.use_cases.import_sangiin_election_usecase()

        result = await usecase.execute(
            ImportSangiinElectionInputDto(
                file_path=file_path,
                governing_body_id=governing_body_id,
                dry_run=dry_run,
            )
        )

        ElectionImportCommands.show_progress(
            f"\n処理完了:\n"
            f"  議員総数: {result.total_councillors}\n"
            f"  選挙レコード作成: {result.elections_created}\n"
            f"  マッチ: {result.matched_politicians}\n"
            f"  新規政治家: {result.created_politicians}\n"
            f"  新規政党: {result.created_parties}\n"
            f"  同姓同名スキップ: {result.skipped_ambiguous}\n"
            f"  重複スキップ: {result.skipped_duplicate}\n"
            f"  ElectionMember作成: {result.election_members_created}\n"
            f"  エラー: {result.errors}"
        )

        if result.error_details:
            ElectionImportCommands.warning("エラー詳細:")
            for detail in result.error_details[:10]:
                ElectionImportCommands.warning(f"  - {detail}")

        if result.errors == 0:
            ElectionImportCommands.success("インポート完了")
        else:
            ElectionImportCommands.warning(
                f"インポート完了（{result.errors}件のエラー）"
            )


def get_election_import_commands() -> list[click.Command]:
    """選挙インポート関連のコマンドリストを返す."""
    return [
        ElectionImportCommands.import_national_election,
        ElectionImportCommands.import_proportional_election,
        ElectionImportCommands.import_sangiin_election,
    ]
