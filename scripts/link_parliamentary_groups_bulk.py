"""第45-50回衆議院選挙の会派自動紐付け一括実行スクリプト.

政党所属議員の会派自動紐付け（link_parliamentary_groups.py）を
第45〜50回選挙に対して順次実行し、結果サマリーとスキップ議員リストを出力する。
実行後にSEEDファイルを自動生成する。

Usage (Docker経由で実行):
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/link_parliamentary_groups_bulk.py

    # ドライラン（DB書き込みなし）
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/link_parliamentary_groups_bulk.py --dry-run

    # SEED生成をスキップ
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/link_parliamentary_groups_bulk.py --skip-seed

前提条件:
    - Docker環境が起動済み（just up-detached）
    - マスターデータ（開催主体「国会」ID=1）がロード済み
    - Alembicマイグレーション適用済み
    - 第45-50回選挙データ・当選者データがインポート済み
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.seed_generator import SeedGenerator


if TYPE_CHECKING:
    from src.application.dtos.parliamentary_group_linkage_dto import (
        LinkParliamentaryGroupOutputDto,
    )


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 対象選挙回次
TARGET_ELECTIONS = list(range(45, 51))  # 45, 46, 47, 48, 49, 50


@dataclass
class ElectionResult:
    """各選挙の紐付け結果"""

    term_number: int
    output: LinkParliamentaryGroupOutputDto | None = None
    error: str | None = None


@dataclass
class BulkResult:
    """一括実行の全体結果"""

    results: list[ElectionResult] = field(default_factory=list)

    @property
    def total_elected(self) -> int:
        return sum(r.output.total_elected for r in self.results if r.output)

    @property
    def total_linked(self) -> int:
        return sum(r.output.linked_count for r in self.results if r.output)

    @property
    def total_already_existed(self) -> int:
        return sum(r.output.already_existed_count for r in self.results if r.output)

    @property
    def total_skipped(self) -> int:
        return sum(
            (
                r.output.skipped_no_party
                + r.output.skipped_no_group
                + r.output.skipped_multiple_groups
            )
            for r in self.results
            if r.output
        )


async def run_bulk_with_details(elections: list[int], dry_run: bool) -> BulkResult:
    """複数選挙に対して会派紐付けを順次実行し、詳細結果を記録する."""
    from src.application.dtos.parliamentary_group_linkage_dto import (
        LinkParliamentaryGroupInputDto,
    )
    from src.application.usecases.link_parliamentary_group_usecase import (
        LinkParliamentaryGroupUseCase,
    )
    from src.infrastructure.config.async_database import get_async_session
    from src.infrastructure.persistence.election_member_repository_impl import (
        ElectionMemberRepositoryImpl,
    )
    from src.infrastructure.persistence.election_repository_impl import (
        ElectionRepositoryImpl,
    )
    from src.infrastructure.persistence.parliamentary_group_membership_repository_impl import (  # noqa: E501
        ParliamentaryGroupMembershipRepositoryImpl,
    )
    from src.infrastructure.persistence.parliamentary_group_party_repository_impl import (  # noqa: E501
        ParliamentaryGroupPartyRepositoryImpl,
    )
    from src.infrastructure.persistence.parliamentary_group_repository_impl import (
        ParliamentaryGroupRepositoryImpl,
    )
    from src.infrastructure.persistence.party_membership_history_repository_impl import (  # noqa: E501
        PartyMembershipHistoryRepositoryImpl,
    )
    from src.infrastructure.persistence.politician_repository_impl import (
        PoliticianRepositoryImpl,
    )

    bulk_result = BulkResult()
    governing_body_id = 1  # 国会

    for term_number in elections:
        election_result = ElectionResult(term_number=term_number)
        logger.info(
            "=== 第%d回選挙 会派自動紐付け開始 %s===",
            term_number,
            "(ドライラン) " if dry_run else "",
        )
        try:
            async with get_async_session() as session:
                use_case = LinkParliamentaryGroupUseCase(
                    election_repository=ElectionRepositoryImpl(session),
                    election_member_repository=ElectionMemberRepositoryImpl(session),
                    politician_repository=PoliticianRepositoryImpl(session),
                    parliamentary_group_repository=(
                        ParliamentaryGroupRepositoryImpl(session)
                    ),
                    parliamentary_group_membership_repository=(
                        ParliamentaryGroupMembershipRepositoryImpl(session)
                    ),
                    party_membership_history_repository=(
                        PartyMembershipHistoryRepositoryImpl(session)
                    ),
                    parliamentary_group_party_repository=(
                        ParliamentaryGroupPartyRepositoryImpl(session)
                    ),
                )

                input_dto = LinkParliamentaryGroupInputDto(
                    term_number=term_number,
                    governing_body_id=governing_body_id,
                    dry_run=dry_run,
                )

                output = await use_case.execute(input_dto)
                election_result.output = output

                logger.info("--- 第%d回 結果 ---", term_number)
                logger.info(
                    "当選者: %d, 紐付け: %d, 既存: %d, "
                    "政党未設定: %d, 会派なし: %d, 複数会派: %d, エラー: %d",
                    output.total_elected,
                    output.linked_count,
                    output.already_existed_count,
                    output.skipped_no_party,
                    output.skipped_no_group,
                    output.skipped_multiple_groups,
                    output.errors,
                )
        except Exception as e:
            logger.exception("第%d回選挙の処理でエラー発生", term_number)
            election_result.error = str(e)

        bulk_result.results.append(election_result)

    return bulk_result


def write_result_report(bulk_result: BulkResult, output_path: str) -> None:
    """結果レポートをファイルに出力する."""
    lines: list[str] = []
    lines.append("=== 第45-50回 会派自動紐付け一括実行結果 ===")
    lines.append("")

    for er in bulk_result.results:
        lines.append(f"--- 第{er.term_number}回 ---")
        if er.error:
            lines.append(f"  エラー: {er.error}")
        elif er.output:
            o = er.output
            lines.append(
                f"  当選者数: {o.total_elected}, "
                f"紐付け成功: {o.linked_count}, "
                f"既存: {o.already_existed_count}, "
                f"政党未設定: {o.skipped_no_party}, "
                f"会派なし: {o.skipped_no_group}, "
                f"複数会派: {o.skipped_multiple_groups}"
            )
        lines.append("")

    lines.append("=== 全体サマリー ===")
    lines.append(f"総当選者: {bulk_result.total_elected}")
    lines.append(f"総紐付け: {bulk_result.total_linked}")
    lines.append(f"総既存: {bulk_result.total_already_existed}")
    lines.append(f"総スキップ: {bulk_result.total_skipped}")
    lines.append("")

    # スキップ議員一覧
    lines.append("=== スキップ議員一覧 ===")
    for er in bulk_result.results:
        if er.output and er.output.skipped_members:
            lines.append(f"--- 第{er.term_number}回 ---")
            for s in er.output.skipped_members:
                lines.append(f"  {s.politician_name}: {s.reason}")
            lines.append("")

    report = "\n".join(lines)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)
    logger.info("結果レポートを出力: %s", output_path)


def generate_seed_file() -> None:
    """parliamentary_group_memberships のSEEDファイルを生成する."""
    generator = SeedGenerator()
    output_path = "database/seed_parliamentary_group_memberships_generated.sql"
    with open(output_path, "w") as f:
        generator.generate_parliamentary_group_memberships_seed(f)
    logger.info("SEEDファイルを生成: %s", output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="第45-50回衆議院選挙の会派自動紐付け一括実行",
        epilog=(
            "例: docker compose -f docker/docker-compose.yml exec sagebase "
            "uv run python scripts/link_parliamentary_groups_bulk.py"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（DB書き込みなし、紐付け結果のみ表示）",
    )
    parser.add_argument(
        "--skip-seed",
        action="store_true",
        help="SEED生成をスキップ",
    )
    args = parser.parse_args()

    bulk_result = asyncio.run(run_bulk_with_details(TARGET_ELECTIONS, args.dry_run))

    # 結果レポート出力
    write_result_report(bulk_result, "tmp/link_results_45_50.txt")

    # SEED生成
    if not args.dry_run and not args.skip_seed:
        generate_seed_file()

    # エラーがあった場合は非ゼロで終了
    has_errors = any(r.error for r in bulk_result.results)
    if has_errors:
        sys.exit(1)
