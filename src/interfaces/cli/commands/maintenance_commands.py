"""メンテナンス用CLIコマンド

Issue #947: 既存議事録への役職-人名マッピングのバックフィル

このモジュールは、メンテナンス用のCLIコマンドを提供します。
"""

import click

from ..base import (
    BaseCommand,
    ensure_container,
    with_async_execution,
    with_error_handling,
)


class MaintenanceCommands(BaseCommand):
    """メンテナンス用コマンド"""

    @staticmethod
    @click.command()
    @click.option(
        "--meeting-id",
        type=int,
        default=None,
        help="特定の会議IDのみ処理（未指定時は全対象）",
    )
    @click.option(
        "--force-reprocess",
        is_flag=True,
        help="既に抽出済みのマッピングを上書き",
    )
    @click.option(
        "--limit",
        type=int,
        default=None,
        help="処理する議事録の最大数",
    )
    @click.option(
        "--skip-existing/--no-skip-existing",
        default=True,
        help="既にマッピングがある議事録をスキップ（デフォルト: スキップ）",
    )
    @with_error_handling
    @with_async_execution
    async def backfill_role_name_mappings(
        meeting_id: int | None,
        force_reprocess: bool,
        limit: int | None,
        skip_existing: bool,
    ):
        """既存議事録の役職-人名マッピングをバックフィル

        既存の議事録データに対して役職-人名マッピングを抽出・保存します。
        発言者マッチング精度向上のための前処理として使用します。

        使用例:

            # 全対象（既存マッピングをスキップ）
            sagebase backfill-role-name-mappings

            # 処理件数を制限
            sagebase backfill-role-name-mappings --limit 10

            # 特定会議のみ
            sagebase backfill-role-name-mappings --meeting-id 123

            # 強制再処理（既存マッピングを上書き）
            sagebase backfill-role-name-mappings --force-reprocess
        """
        MaintenanceCommands.show_progress("役職-人名マッピングのバックフィルを開始...")

        container = ensure_container()

        usecase = container.use_cases.backfill_role_name_mappings_usecase()

        # 処理設定をログ出力
        if meeting_id:
            MaintenanceCommands.show_progress(f"対象会議ID: {meeting_id}")
        if limit:
            MaintenanceCommands.show_progress(f"処理上限: {limit}件")
        if force_reprocess:
            MaintenanceCommands.show_progress("強制再処理モード: ON")
        if not skip_existing:
            MaintenanceCommands.show_progress("既存マッピングもスキップせず処理")

        # バックフィル実行
        result = await usecase.execute(
            meeting_id=meeting_id,
            force_reprocess=force_reprocess,
            limit=limit,
            skip_existing=skip_existing,
        )

        # 結果を表示
        MaintenanceCommands.show_progress(
            f"\n処理完了:\n"
            f"  処理件数: {result.total_processed}\n"
            f"  成功: {result.success_count}\n"
            f"  スキップ: {result.skip_count}\n"
            f"  エラー: {result.error_count}"
        )

        if result.errors:
            MaintenanceCommands.warning("エラー詳細:")
            for error in result.errors[:10]:  # 最初の10件のみ表示
                MaintenanceCommands.warning(f"  - {error}")
            if len(result.errors) > 10:
                MaintenanceCommands.warning(f"  ... 他 {len(result.errors) - 10}件")

        if result.error_count == 0:
            MaintenanceCommands.success("バックフィル処理が正常に完了しました")
        else:
            MaintenanceCommands.warning(
                f"バックフィル処理が完了しましたが、"
                f"{result.error_count}件のエラーがありました"
            )

    @staticmethod
    @click.command()
    @click.option(
        "--no-dry-run",
        is_flag=True,
        help="実際にDBを更新する（デフォルトはdry_run）",
    )
    @with_error_handling
    @with_async_execution
    async def rebuild_party_history(no_dry_run: bool):
        """選挙データから政党所属履歴を再構築

        election_membersのpolitical_party_idを基に、
        政党移動を検出してparty_membership_historyを再構築します。

        使用例:

            # dry_run（変更なし、結果のみ表示）
            sagebase rebuild-party-history

            # 実際にDBを更新
            sagebase rebuild-party-history --no-dry-run
        """
        from src.application.dtos.rebuild_party_membership_dto import (
            RebuildPartyMembershipInputDto,
        )

        dry_run = not no_dry_run

        if dry_run:
            MaintenanceCommands.show_progress(
                "政党所属履歴の再構築を開始（dry_runモード）..."
            )
        else:
            MaintenanceCommands.show_progress(
                "政党所属履歴の再構築を開始（本番モード）..."
            )

        container = ensure_container()
        usecase = container.use_cases.rebuild_party_membership_history_usecase()

        result = await usecase.execute(RebuildPartyMembershipInputDto(dry_run=dry_run))

        MaintenanceCommands.show_progress(
            f"\n処理完了:\n"
            f"  対象政治家数: {result.total_politicians}\n"
            f"  政党変更あり: {result.politicians_with_party_change}\n"
            f"  政党情報なし（スキップ）: {result.skipped_no_party}\n"
            f"  削除レコード: {result.deleted_old_records}\n"
            f"  作成レコード: {result.created_new_records}"
        )

        if dry_run:
            MaintenanceCommands.warning(
                "dry_runモードです。--no-dry-run で実際にDBを更新できます"
            )
        else:
            MaintenanceCommands.success("政党所属履歴の再構築が完了しました")


def get_maintenance_commands() -> list[click.Command]:
    """メンテナンス関連のコマンドリストを返す"""
    return [
        MaintenanceCommands.backfill_role_name_mappings,
        MaintenanceCommands.rebuild_party_history,
    ]
