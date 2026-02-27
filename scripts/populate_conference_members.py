"""衆議院選挙当選者→ConferenceMember一括生成スクリプト.

衆議院第45-50回の選挙当選者（election_members, is_elected=true）を
ConferenceMember（politician_affiliations）に一括変換する。

対象選挙はDBから動的に検出される（ハードコードなし）。

Usage (Docker経由で実行):
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/populate_conference_members.py

    # 特定回次のみ実行
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/populate_conference_members.py --term 45 46

    # ドライラン（DB書き込みなし）
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/populate_conference_members.py --dry-run

    # SEED生成をスキップ
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/populate_conference_members.py --skip-seed

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
from typing import IO, TYPE_CHECKING, Any


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


if TYPE_CHECKING:
    from src.application.dtos.conference_member_population_dto import (
        PopulateConferenceMembersOutputDto,
    )
    from src.domain.entities.election import Election


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class ElectionResult:
    """各選挙の生成結果."""

    term_number: int
    output: PopulateConferenceMembersOutputDto | None = None
    error: str | None = None


@dataclass
class BulkResult:
    """一括実行の全体結果."""

    results: list[ElectionResult] = field(default_factory=list)

    @property
    def total_elected(self) -> int:
        return sum(r.output.total_elected for r in self.results if r.output)

    @property
    def total_created(self) -> int:
        return sum(r.output.created_count for r in self.results if r.output)

    @property
    def total_already_existed(self) -> int:
        return sum(r.output.already_existed_count for r in self.results if r.output)

    @property
    def total_errors(self) -> int:
        usecase_errors = sum(r.output.errors for r in self.results if r.output)
        exception_errors = sum(1 for r in self.results if r.error)
        return usecase_errors + exception_errors


async def detect_house_elections(
    governing_body_id: int = 1,
) -> list[Election]:
    """衆議院選挙をDBから動的に検出する."""
    from src.infrastructure.config.async_database import get_async_session
    from src.infrastructure.persistence.election_repository_impl import (
        ElectionRepositoryImpl,
    )

    async with get_async_session() as session:
        repo = ElectionRepositoryImpl(session)
        all_elections = await repo.get_by_governing_body(governing_body_id)

    house_elections = [e for e in all_elections if e.chamber == "衆議院"]
    house_elections.sort(key=lambda e: e.term_number)
    return house_elections


async def run_bulk(
    elections: list[Election], dry_run: bool, conference_name: str
) -> BulkResult:
    """複数選挙に対してConferenceMember生成を順次実行する."""
    from src.application.dtos.conference_member_population_dto import (
        PopulateConferenceMembersInputDto,
    )
    from src.application.usecases.populate_conference_members_usecase import (
        PopulateConferenceMembersUseCase,
    )
    from src.infrastructure.config.async_database import get_async_session
    from src.infrastructure.persistence.conference_member_repository_impl import (
        ConferenceMemberRepositoryImpl,
    )
    from src.infrastructure.persistence.conference_repository_impl import (
        ConferenceRepositoryImpl,
    )
    from src.infrastructure.persistence.election_member_repository_impl import (
        ElectionMemberRepositoryImpl,
    )
    from src.infrastructure.persistence.election_repository_impl import (
        ElectionRepositoryImpl,
    )
    from src.infrastructure.persistence.politician_repository_impl import (
        PoliticianRepositoryImpl,
    )

    bulk_result = BulkResult()

    for election in elections:
        election_result = ElectionResult(term_number=election.term_number)
        logger.info(
            "=== 第%d回 衆議院 ConferenceMember生成開始 %s===",
            election.term_number,
            "(ドライラン) " if dry_run else "",
        )
        try:
            async with get_async_session() as session:
                use_case = PopulateConferenceMembersUseCase(
                    election_repository=ElectionRepositoryImpl(session),
                    election_member_repository=ElectionMemberRepositoryImpl(session),
                    conference_repository=ConferenceRepositoryImpl(session),
                    conference_member_repository=ConferenceMemberRepositoryImpl(
                        session
                    ),
                    politician_repository=PoliticianRepositoryImpl(session),
                )

                input_dto = PopulateConferenceMembersInputDto(
                    term_number=election.term_number,
                    governing_body_id=election.governing_body_id,
                    conference_name=conference_name,
                    dry_run=dry_run,
                )

                output = await use_case.execute(input_dto)
                election_result.output = output

                logger.info(
                    "--- 第%d回 結果: 当選者=%d, 新規=%d, 既存=%d, エラー=%d",
                    election.term_number,
                    output.total_elected,
                    output.created_count,
                    output.already_existed_count,
                    output.errors,
                )
        except Exception:
            logger.exception("第%d回選挙の処理でエラー発生", election.term_number)
            election_result.error = str(sys.exc_info()[1])

        bulk_result.results.append(election_result)

    return bulk_result


def write_result_report(bulk_result: BulkResult, output_path: str) -> None:
    """結果レポートをファイルに出力する."""
    lines: list[str] = []
    lines.append("=== 衆議院選挙 ConferenceMember一括生成結果 ===")
    lines.append("")

    for er in bulk_result.results:
        lines.append(f"--- 第{er.term_number}回 ---")
        if er.error:
            lines.append(f"  エラー: {er.error}")
        elif er.output:
            o = er.output
            lines.append(
                f"  当選者数: {o.total_elected}, "
                f"新規作成: {o.created_count}, "
                f"既存: {o.already_existed_count}, "
                f"エラー: {o.errors}"
            )
        lines.append("")

    lines.append("=== 全体サマリー ===")
    lines.append(f"総当選者: {bulk_result.total_elected}")
    lines.append(f"総新規作成: {bulk_result.total_created}")
    lines.append(f"総既存: {bulk_result.total_already_existed}")
    lines.append(f"総エラー: {bulk_result.total_errors}")

    report = "\n".join(lines)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)
    logger.info("結果レポートを出力: %s", output_path)


def generate_seed_file() -> None:
    """politician_affiliationsのSEEDファイルを生成する."""
    from datetime import datetime

    from sqlalchemy import create_engine, text

    from src.infrastructure.config.database import get_database_url

    engine = create_engine(get_database_url())
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT
                    pa.politician_id,
                    pa.conference_id,
                    pa.start_date,
                    pa.end_date,
                    pa.role,
                    p.name AS politician_name,
                    c.name AS conference_name,
                    gb.name AS governing_body_name,
                    gb.type AS governing_body_type
                FROM politician_affiliations pa
                JOIN politicians p ON pa.politician_id = p.id
                JOIN conferences c ON pa.conference_id = c.id
                JOIN governing_bodies gb ON c.governing_body_id = gb.id
                ORDER BY
                    pa.start_date,
                    gb.name,
                    c.name,
                    p.name
            """)
        )
        columns = result.keys()
        affiliations = [dict(zip(columns, row, strict=False)) for row in result]

    output_path = "database/seed_politician_affiliations_generated.sql"
    with open(output_path, "w") as f:
        _write_seed_content(f, affiliations, datetime.now())
    engine.dispose()
    logger.info("SEEDファイルを生成: %s", output_path)


def _escape_sql(value: str) -> str:
    """SQLのシングルクォートをエスケープする."""
    return value.replace("'", "''")


def _write_seed_content(
    f: IO[str], affiliations: list[dict[str, Any]], now: Any
) -> None:
    """SEEDファイルの内容を書き出す."""
    f.write(f"-- Generated from database on {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("-- politician_affiliations seed data\n")
    f.write("-- ユニーク制約がないため、個別INSERT + WHERE NOT EXISTSで冪等性を確保\n")
    f.write("\n")

    for aff in affiliations:
        politician_name = _escape_sql(aff["politician_name"])
        conference_name = _escape_sql(aff["conference_name"])
        body_name = _escape_sql(aff["governing_body_name"])
        body_type = _escape_sql(aff["governing_body_type"])
        start_date_str = aff["start_date"].strftime("%Y-%m-%d")

        end_date_val = (
            f"'{aff['end_date'].strftime('%Y-%m-%d')}'"
            if aff.get("end_date")
            else "NULL"
        )
        role_val = f"'{_escape_sql(aff['role'])}'" if aff.get("role") else "NULL"

        politician_sub = (
            f"(SELECT id FROM politicians WHERE name = '{politician_name}')"
        )
        conference_sub = (
            f"(SELECT id FROM conferences "
            f"WHERE name = '{conference_name}' "
            f"AND governing_body_id = "
            f"(SELECT id FROM governing_bodies "
            f"WHERE name = '{body_name}' "
            f"AND type = '{body_type}'))"
        )

        f.write(
            "INSERT INTO politician_affiliations "
            "(politician_id, conference_id, start_date, end_date, role)\n"
        )
        f.write(
            f"SELECT {politician_sub}, {conference_sub}, "
            f"'{start_date_str}', {end_date_val}, {role_val}\n"
        )
        f.write(
            f"WHERE NOT EXISTS ("
            f"SELECT 1 FROM politician_affiliations "
            f"WHERE politician_id = {politician_sub} "
            f"AND conference_id = {conference_sub} "
            f"AND start_date = '{start_date_str}'"
            f");\n"
        )

    f.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="衆議院選挙当選者→ConferenceMember一括生成",
        epilog=(
            "例: docker compose -f docker/docker-compose.yml exec sagebase "
            "uv run python scripts/populate_conference_members.py"
        ),
    )
    parser.add_argument(
        "--term",
        type=int,
        nargs="*",
        help="特定の回次のみ実行（例: --term 45 46）",
    )
    parser.add_argument(
        "--conference-name",
        type=str,
        default="衆議院本会議",
        help="紐付け先会議体名（デフォルト: 衆議院本会議）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（DB書き込みなし）",
    )
    parser.add_argument(
        "--skip-seed",
        action="store_true",
        help="SEED生成をスキップ",
    )
    args = parser.parse_args()

    # 衆議院選挙を動的検出
    elections = asyncio.run(detect_house_elections())

    # 回次フィルタ
    if args.term:
        elections = [e for e in elections if e.term_number in args.term]

    if not elections:
        logger.warning("対象の選挙が見つかりません")
        sys.exit(0)

    logger.info(
        "対象選挙: %s",
        ", ".join(f"第{e.term_number}回" for e in elections),
    )

    bulk_result = asyncio.run(run_bulk(elections, args.dry_run, args.conference_name))

    # 結果レポート出力
    write_result_report(bulk_result, "tmp/populate_conference_members_results.txt")

    # SEED生成
    if not args.dry_run and not args.skip_seed:
        generate_seed_file()

    # エラーがあった場合は非ゼロで終了
    has_errors = any(r.error for r in bulk_result.results)
    if has_errors:
        sys.exit(1)
