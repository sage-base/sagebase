"""smartnews-smri gian_summary.json インポートスクリプト."""

import argparse
import asyncio
import logging
import sys

from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.infrastructure.config.async_database import get_async_session
from src.infrastructure.importers.smartnews_smri_importer import (
    SmartNewsSmriImporter,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.proposal_repository_impl import (
    ProposalRepositoryImpl,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

GOVERNING_BODY_NAME = "日本国"
GOVERNING_BODY_TYPE = "国"


async def main(file_path: Path, batch_size: int) -> None:
    async with get_async_session() as session:
        gb_repo = GoverningBodyRepositoryImpl(session)
        governing_body = await gb_repo.get_by_name_and_type(
            GOVERNING_BODY_NAME, GOVERNING_BODY_TYPE
        )
        if governing_body is None or governing_body.id is None:
            logger.error(
                "開催主体 '%s' (type='%s') が見つかりません。"
                "マスターデータを確認してください。",
                GOVERNING_BODY_NAME,
                GOVERNING_BODY_TYPE,
            )
            sys.exit(1)

        logger.info("開催主体: %s (ID=%d)", governing_body.name, governing_body.id)

        proposal_repo = ProposalRepositoryImpl(session)
        importer = SmartNewsSmriImporter(
            proposal_repository=proposal_repo,
            governing_body_id=governing_body.id,
        )

        logger.info("JSONファイル読み込み: %s", file_path)
        records = importer.load_json(file_path)
        logger.info("レコード数: %d", len(records))

        result = await importer.import_data(records, batch_size=batch_size)

        logger.info("--- インポート結果 ---")
        logger.info("合計: %d", result.total)
        logger.info("作成: %d", result.created)
        logger.info("スキップ: %d", result.skipped)
        logger.info("エラー: %d", result.errors)

        if result.errors > 0:
            sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="smartnews-smri gian_summary.json をProposalテーブルにインポート"
    )
    parser.add_argument(
        "file_path",
        type=Path,
        help="gian_summary.json ファイルのパス",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="バッチサイズ (デフォルト: 100)",
    )
    args = parser.parse_args()

    if not args.file_path.exists():
        logger.error("ファイルが見つかりません: %s", args.file_path)
        sys.exit(1)

    asyncio.run(main(args.file_path, args.batch_size))
