"""Cowork結果CSVから政府関係者をインポートするスクリプト.

Usage (Docker経由で実行):
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/import_government_officials.py \
        /tmp/government_officials.csv

    # ドライランで確認
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/import_government_officials.py \
        /tmp/government_officials.csv --dry-run

データ形式（CSV）:
    speaker_name,representative_speaker_id,category,skip_reason,confidence,notes
    「法務省刑事局長」等のnotes列をorganization + positionにパースする。

前提条件:
    - Docker環境が起動済み（just up-detached）
    - Alembicマイグレーション038適用済み
"""

import argparse
import asyncio
import csv
import logging
import re
import sys

from pathlib import Path


# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.application.dtos.government_official_dto import (
    GovernmentOfficialCsvRow,
    ImportGovernmentOfficialsCsvInputDto,
)
from src.infrastructure.di.providers import (
    DatabaseContainer,
    RepositoryContainer,
    UseCaseContainer,
)


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# 省庁名のパターン（「○○省」「○○庁」「○○院」「○○局」等のサフィックス）
_ORG_PATTERN = re.compile(r"^(.+?(?:省|庁|院|府|局|委員会|本部|機構|会議|センター|室))")


def parse_org_position(notes: str) -> tuple[str, str]:
    """notes列（例: "法務省刑事局長"）をorganization + positionにパース."""
    notes = notes.strip()
    if not notes:
        return ("", "")

    match = _ORG_PATTERN.match(notes)
    if match:
        org = match.group(1)
        pos = notes[len(org) :].strip()
        if pos:
            return (org, pos)
        return (org, "")

    return ("", notes)


def read_csv(file_path: Path) -> list[GovernmentOfficialCsvRow]:
    """CSVを読み込み、government_officialカテゴリの行をDTOに変換."""
    rows: list[GovernmentOfficialCsvRow] = []

    with open(file_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for line in reader:
            category = line.get("category", "").strip()
            if category != "government_official":
                continue

            speaker_name = line.get("speaker_name", "").strip()
            rep_id_str = line.get("representative_speaker_id", "").strip()
            notes = line.get("notes", "").strip()

            if not speaker_name or not rep_id_str:
                logger.warning(f"不完全な行をスキップ: {line}")
                continue

            try:
                rep_id = int(rep_id_str)
            except ValueError:
                logger.warning(f"representative_speaker_idが整数でない: {rep_id_str}")
                continue

            org, pos = parse_org_position(notes)

            rows.append(
                GovernmentOfficialCsvRow(
                    speaker_name=speaker_name,
                    representative_speaker_id=rep_id,
                    organization=org,
                    position=pos,
                    notes=notes,
                )
            )

    return rows


async def main(file_path: Path, dry_run: bool) -> None:
    """メイン処理."""
    rows = read_csv(file_path)
    logger.info(f"CSVから{len(rows)}件のgovernment_official行を読み込み")

    if not rows:
        logger.info("処理対象の行がありません")
        return

    db_container = DatabaseContainer()
    repo_container = RepositoryContainer(database=db_container)
    usecase_container = UseCaseContainer(
        repositories=repo_container,
        database=db_container,
    )

    usecase = usecase_container.import_government_officials_csv_usecase()

    input_dto = ImportGovernmentOfficialsCsvInputDto(
        rows=rows,
        dry_run=dry_run,
    )

    output = await usecase.execute(input_dto)

    prefix = "[DRY RUN] " if dry_run else ""
    logger.info(f"{prefix}作成した政府関係者: {output.created_officials_count}")
    logger.info(f"{prefix}作成した役職履歴: {output.created_positions_count}")
    logger.info(f"{prefix}紐付けたSpeaker: {output.linked_speakers_count}")
    logger.info(f"{prefix}スキップ: {output.skipped_count}")

    if output.errors:
        logger.warning(f"エラー: {len(output.errors)}件")
        for err in output.errors:
            logger.warning(f"  - {err}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cowork結果CSVから政府関係者をインポート",
        epilog=(
            "例: docker compose exec sagebase "
            "uv run python scripts/import_government_officials.py "
            "/tmp/government_officials.csv"
        ),
    )
    parser.add_argument(
        "file_path",
        type=Path,
        help="CSVファイルのパス（コンテナ内のパス）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際にはDBに書き込まず、処理件数のみ表示",
    )

    args = parser.parse_args()

    if not args.file_path.exists():
        logger.error(f"ファイルが見つかりません: {args.file_path}")
        sys.exit(1)

    asyncio.run(main(args.file_path, args.dry_run))
