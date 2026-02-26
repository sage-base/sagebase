"""国政選挙の会派自動紐付け一括実行スクリプト.

政党所属議員の会派自動紐付け（link_parliamentary_groups.py）を
DBに登録された国政選挙（衆議院・参議院）に対して順次実行し、
結果サマリーとスキップ議員リストを出力する。
実行後にSEEDファイルを自動生成する。

対象選挙はDBから動的に検出される（ハードコードなし）。

Usage (Docker経由で実行):
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/link_parliamentary_groups_bulk.py

    # 衆議院のみ実行
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/link_parliamentary_groups_bulk.py --chamber 衆議院

    # 特定回次のみ実行
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/link_parliamentary_groups_bulk.py --term 49 50

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
    - 選挙データ・当選者データがインポート済み
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
    from src.domain.entities.election import Election


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class ElectionResult:
    """各選挙の紐付け結果."""

    term_number: int
    election_type: str = ""
    chamber: str = ""
    output: LinkParliamentaryGroupOutputDto | None = None
    error: str | None = None


@dataclass
class BulkResult:
    """一括実行の全体結果."""

    results: list[ElectionResult] = field(default_factory=lambda: [])

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

    def results_by_chamber(self, chamber: str) -> list[ElectionResult]:
        """指定院の結果のみフィルタする."""
        return [r for r in self.results if r.chamber == chamber]


async def detect_national_elections(
    governing_body_id: int = 1,
) -> dict[str, list[Election]]:
    """国政選挙をDBから動的に検出し、衆議院・参議院に分類する."""
    from src.domain.entities.election import Election as ElectionEntity
    from src.infrastructure.config.async_database import get_async_session
    from src.infrastructure.persistence.election_repository_impl import (
        ElectionRepositoryImpl,
    )

    async with get_async_session() as session:
        repo = ElectionRepositoryImpl(session)
        all_elections = await repo.get_by_governing_body(governing_body_id)

    result: dict[str, list[Election]] = {"衆議院": [], "参議院": []}

    for election in all_elections:
        if election.election_type == ElectionEntity.ELECTION_TYPE_GENERAL:
            result["衆議院"].append(election)
        elif election.election_type == ElectionEntity.ELECTION_TYPE_SANGIIN:
            result["参議院"].append(election)

    # term_number 昇順ソート
    for chamber_elections in result.values():
        chamber_elections.sort(key=lambda e: e.term_number)

    return result


async def run_bulk_with_details(elections: list[Election], dry_run: bool) -> BulkResult:
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

    for election in elections:
        election_result = ElectionResult(
            term_number=election.term_number,
            election_type=election.election_type or "",
            chamber=election.chamber,
        )
        logger.info(
            "=== 第%d回 %s 会派自動紐付け開始 %s===",
            election.term_number,
            election.chamber or "（院名不明）",
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
                    term_number=election.term_number,
                    governing_body_id=election.governing_body_id,
                    chamber=election.chamber,
                    dry_run=dry_run,
                )

                output = await use_case.execute(input_dto)
                election_result.output = output

                logger.info("--- 第%d回 結果 ---", election.term_number)
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
            logger.exception("第%d回選挙の処理でエラー発生", election.term_number)
            election_result.error = str(e)

        bulk_result.results.append(election_result)

    return bulk_result


def write_result_report(bulk_result: BulkResult, output_path: str) -> None:
    """結果レポートをファイルに出力する."""
    lines: list[str] = []
    lines.append("=== 国政選挙 会派自動紐付け一括実行結果 ===")
    lines.append("")

    # 院別にセクションを出力
    for chamber in ["衆議院", "参議院"]:
        chamber_results = bulk_result.results_by_chamber(chamber)
        if not chamber_results:
            continue

        lines.append(f"=== {chamber} ===")
        lines.append("")

        for er in chamber_results:
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
            chamber_label = f" ({er.chamber})" if er.chamber else ""
            lines.append(f"--- 第{er.term_number}回{chamber_label} ---")
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
        description="国政選挙の会派自動紐付け一括実行",
        epilog=(
            "例: docker compose -f docker/docker-compose.yml exec sagebase "
            "uv run python scripts/link_parliamentary_groups_bulk.py"
        ),
    )
    parser.add_argument(
        "--chamber",
        type=str,
        choices=["all", "衆議院", "参議院"],
        default="all",
        help="対象の院（デフォルト: all）",
    )
    parser.add_argument(
        "--term",
        type=int,
        nargs="*",
        help="特定の回次のみ実行（例: --term 49 50）",
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

    # 選挙を動的検出
    elections_by_chamber = asyncio.run(detect_national_elections())

    # chamber フィルタ
    target_chambers = ["衆議院", "参議院"] if args.chamber == "all" else [args.chamber]

    # 対象選挙を収集（衆議院→参議院の順）
    from src.domain.entities.election import Election

    target_elections: list[Election] = []
    for chamber in target_chambers:
        chamber_elections = elections_by_chamber.get(chamber, [])
        if args.term:
            chamber_elections = [
                e for e in chamber_elections if e.term_number in args.term
            ]
        target_elections.extend(chamber_elections)

    if not target_elections:
        logger.warning("対象の選挙が見つかりません")
        sys.exit(0)

    logger.info(
        "対象選挙: %s",
        ", ".join(f"第{e.term_number}回({e.chamber})" for e in target_elections),
    )

    bulk_result = asyncio.run(run_bulk_with_details(target_elections, args.dry_run))

    # 結果レポート出力
    write_result_report(bulk_result, "tmp/link_results_national.txt")

    # SEED生成
    if not args.dry_run and not args.skip_seed:
        generate_seed_file()

    # エラーがあった場合は非ゼロで終了
    has_errors = any(r.error for r in bulk_result.results)
    if has_errors:
        sys.exit(1)
