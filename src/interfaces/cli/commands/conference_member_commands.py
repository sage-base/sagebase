"""Commands for managing conference member extraction.

政治家との紐付けはGold Layer（ConferenceMember）で管理されるため、
match_members、create_affiliationsコマンドは削除されました。
代わりにStreamlit UIの手動マッチング機能を使用してください。
"""

import asyncio
import logging

from typing import Any

import click

from src.infrastructure.exceptions import DatabaseError, ScrapingError
from src.infrastructure.external.conference_member_extractor.extractor import (
    ConferenceMemberExtractor,
)
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.extracted_conference_member_repository_impl import (
    ExtractedConferenceMemberRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.cli.base import BaseCommand
from src.interfaces.cli.progress import ProgressTracker


logger = logging.getLogger(__name__)


class ConferenceMemberCommands(BaseCommand):
    """Commands for conference member extraction.

    政治家との紐付けはGold Layer（ConferenceMember）で管理されます。
    手動マッチングはStreamlit UIを使用してください。
    """

    @staticmethod
    def echo_info(message: str):
        """Show an info message"""
        click.echo(message)

    @staticmethod
    def echo_success(message: str):
        """Show a success message"""
        click.echo(click.style(f"✓ {message}", fg="green"))

    @staticmethod
    def echo_warning(message: str):
        """Show a warning message"""
        click.echo(click.style(f"⚠️  {message}", fg="yellow"))

    @staticmethod
    def echo_error(message: str):
        """Show an error message"""
        click.echo(click.style(f"✗ {message}", fg="red"), err=True)

    def get_commands(self) -> list[click.Command]:
        """Get list of conference member commands"""
        return [
            ConferenceMemberCommands.extract_conference_members,
            ConferenceMemberCommands.member_status,
        ]

    @staticmethod
    @click.command("extract-conference-members")
    @click.option(
        "--conference-id",
        type=int,
        help="会議体ID（指定しない場合はURLが設定されている全会議体を処理）",
    )
    @click.option(
        "--force",
        is_flag=True,
        help="既存の抽出データを削除して再抽出",
    )
    def extract_conference_members(
        conference_id: int | None = None, force: bool = False
    ):
        """会議体の議員紹介URLから議員情報を抽出

        抽出した議員情報はBronze Layer（extracted_conference_members）に保存されます。
        政治家との紐付けはStreamlit UIの手動マッチング機能を使用してください。
        """

        click.echo("📋 会議体メンバー情報の抽出を開始します")

        # 対象の会議体を取得
        conf_repo = RepositoryAdapter(ConferenceRepositoryImpl)

        if conference_id:
            # 特定の会議体のみ
            conference = conf_repo.get_conference_by_id(conference_id)
            if not conference:
                ConferenceMemberCommands.echo_error(
                    f"会議体ID {conference_id} が見つかりません"
                )
                conf_repo.close()
                return
            conferences = [conference]
        else:
            # URLが設定されている全会議体
            all_conferences = conf_repo.get_all_conferences()
            conferences = [
                conf for conf in all_conferences if conf.get("members_introduction_url")
            ]

            if not conferences:
                ConferenceMemberCommands.echo_warning(
                    "議員紹介URLが設定されている会議体がありません"
                )
                conf_repo.close()
                return

        ConferenceMemberCommands.echo_info(f"処理対象: {len(conferences)}件の会議体")

        # 抽出器を初期化
        extractor = ConferenceMemberExtractor()
        extracted_repo = RepositoryAdapter(ExtractedConferenceMemberRepositoryImpl)

        # 各会議体を処理
        total_extracted = 0
        total_saved = 0

        with ProgressTracker(
            total_steps=len(conferences), description="抽出中"
        ) as progress:
            for conf in conferences:
                progress.set_description(f"抽出中: {conf['name']}")

                # 既存データの処理
                if force:
                    deleted = extracted_repo.delete_extracted_members(conf["id"])
                    if deleted > 0:
                        ConferenceMemberCommands.echo_warning(
                            f"  既存の抽出データ{deleted}件を削除しました"
                        )

                try:
                    # 抽出実行
                    result: dict[str, Any] = asyncio.run(
                        extractor.extract_and_save_members(
                            conference_id=conf["id"],
                            conference_name=conf["name"],
                            url=conf["members_introduction_url"],
                        )
                    )

                    if result.get("error"):
                        ConferenceMemberCommands.echo_error(
                            f"  ❌ エラー: {conf['name']} - {result['error']}"
                        )
                    else:
                        total_extracted += int(result["extracted_count"])
                        total_saved += int(result["saved_count"])

                        ConferenceMemberCommands.echo_success(
                            f"  ✓ {conf['name']}: {result['extracted_count']}人を抽出、"
                            f"{result['saved_count']}人を保存"
                        )

                except (ScrapingError, DatabaseError) as e:
                    ConferenceMemberCommands.echo_error(
                        f"  ❌ エラー: {conf['name']} - {str(e)}"
                    )
                    logger.error(f"Error processing conference {conf['id']}: {e}")
                except Exception as e:
                    ConferenceMemberCommands.echo_error(
                        f"  ❌ 予期しないエラー: {conf['name']} - {str(e)}"
                    )
                    logger.exception(
                        f"Unexpected error processing conference {conf['id']}"
                    )
                    # Wrap in ScrapingError for proper handling
                    raise ScrapingError(
                        f"Failed to extract members from conference {conf['id']}",
                        {"conference_id": conf["id"], "error": str(e)},
                    ) from e

                progress.update(1)

        # 最終結果
        ConferenceMemberCommands.echo_info("\n=== 抽出完了 ===")
        ConferenceMemberCommands.echo_success(f"✅ 抽出総数: {total_extracted}人")
        ConferenceMemberCommands.echo_success(f"✅ 保存総数: {total_saved}人")

        # サマリー表示
        summary = extracted_repo.get_extraction_summary()
        ConferenceMemberCommands.echo_info(f"\n📊 総抽出件数: {summary['total']}件")
        ConferenceMemberCommands.echo_info(
            "💡 政治家との紐付けはStreamlit UIの手動マッチング機能を使用してください"
        )

        conf_repo.close()
        extractor.close()
        extracted_repo.close()

    @staticmethod
    @click.command("member-status")
    @click.option(
        "--conference-id",
        type=int,
        help="会議体ID（指定しない場合は全体のステータスを表示）",
    )
    def member_status(conference_id: int | None = None):
        """抽出状況を表示"""

        ConferenceMemberCommands.echo_info("📊 会議体メンバー抽出状況")

        extracted_repo = RepositoryAdapter(ExtractedConferenceMemberRepositoryImpl)

        # 全体サマリー
        summary = extracted_repo.get_extraction_summary(conference_id)

        ConferenceMemberCommands.echo_info("\n=== 抽出ステータス ===")
        ConferenceMemberCommands.echo_info(f"総件数: {summary['total']}件")

        # 会議体別の詳細
        if conference_id:
            ConferenceMemberCommands.echo_info(
                f"\n=== 会議体ID {conference_id} の抽出メンバー ==="
            )

            members = extracted_repo.get_by_conference(conference_id)
            if members:
                ConferenceMemberCommands.echo_info(f"抽出メンバー数: {len(members)}人")
                for member in members[:10]:
                    role = (
                        f" ({member.extracted_role})" if member.extracted_role else ""
                    )
                    party = (
                        f" - {member.extracted_party_name}"
                        if member.extracted_party_name
                        else ""
                    )
                    ConferenceMemberCommands.echo_info(
                        f"  • {member.extracted_name}{role}{party}"
                    )
                if len(members) > 10:
                    remaining = len(members) - 10
                    ConferenceMemberCommands.echo_info(f"  ... 他 {remaining}人")
            else:
                ConferenceMemberCommands.echo_info("抽出メンバーがありません")

        ConferenceMemberCommands.echo_info(
            "\n💡 政治家との紐付けはStreamlit UIの手動マッチング機能を使用してください"
        )

        extracted_repo.close()


def get_conference_member_commands():
    """Get conference member command group"""
    return ConferenceMemberCommands().get_commands()
