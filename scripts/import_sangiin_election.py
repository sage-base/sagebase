"""参議院選挙データインポートスクリプト.

SmartNews SMRI の giin.json から参議院選挙データをインポートする。

Usage (Docker経由で実行):
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/import_sangiin_election.py /tmp/giin.json

    # ドライラン（DB書き込みなし、抽出結果のみ表示）
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/import_sangiin_election.py /tmp/giin.json --dry-run

データソース:
    https://github.com/smartnews-smri/house-of-councillors/blob/main/data/giin.json

前提条件:
    - Docker環境が起動済み（just up-detached）
    - マスターデータ（開催主体「国会」ID=1）がロード済み
    - Alembicマイグレーション適用済み
"""

import argparse
import asyncio
import logging
import sys

from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.application.dtos.sangiin_election_import_dto import (
    ImportSangiinElectionInputDto,
)
from src.application.usecases.import_sangiin_election_usecase import (
    ImportSangiinElectionUseCase,
)
from src.infrastructure.config.async_database import get_async_session
from src.infrastructure.importers.smartnews_smri_sangiin_data_source import (
    SmartNewsSmriSangiinDataSource,
)
from src.infrastructure.persistence.election_member_repository_impl import (
    ElectionMemberRepositoryImpl,
)
from src.infrastructure.persistence.election_repository_impl import (
    ElectionRepositoryImpl,
)
from src.infrastructure.persistence.political_party_repository_impl import (
    PoliticalPartyRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

GOVERNING_BODY_ID = 1  # 国会


async def run_import(file_path: Path, dry_run: bool) -> bool:
    """参議院選挙データをインポートする."""
    logger.info("=== 参議院選挙データインポート開始 ===")
    logger.info("データファイル: %s", file_path)

    async with get_async_session() as session:
        election_repo = ElectionRepositoryImpl(session)
        member_repo = ElectionMemberRepositoryImpl(session)
        politician_repo = PoliticianRepositoryImpl(session)
        party_repo = PoliticalPartyRepositoryImpl(session)
        data_source = SmartNewsSmriSangiinDataSource()

        use_case = ImportSangiinElectionUseCase(
            election_repository=election_repo,
            election_member_repository=member_repo,
            politician_repository=politician_repo,
            political_party_repository=party_repo,
            data_source=data_source,
        )

        input_dto = ImportSangiinElectionInputDto(
            file_path=file_path,
            governing_body_id=GOVERNING_BODY_ID,
            dry_run=dry_run,
        )

        result = await use_case.execute(input_dto)

        logger.info("--- インポート結果 ---")
        logger.info("議員数: %d", result.total_councillors)
        logger.info("選挙作成: %d", result.elections_created)
        logger.info("マッチ政治家: %d", result.matched_politicians)
        logger.info("新規政治家: %d", result.created_politicians)
        logger.info("新規政党: %d", result.created_parties)
        logger.info("同姓同名スキップ: %d", result.skipped_ambiguous)
        logger.info("重複スキップ: %d", result.skipped_duplicate)
        logger.info("ElectionMember作成: %d", result.election_members_created)
        logger.info("エラー: %d", result.errors)

        if result.error_details:
            for detail in result.error_details:
                logger.error("  %s", detail)

        return result.errors == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="参議院選挙データをインポート（SmartNews SMRI giin.json）",
        epilog=(
            "例: docker compose -f docker/docker-compose.yml exec sagebase "
            "uv run python scripts/import_sangiin_election.py /tmp/giin.json"
        ),
    )
    parser.add_argument(
        "file_path",
        type=Path,
        help="giin.jsonファイルのパス",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（DB書き込みなし、抽出結果のみ表示）",
    )
    args = parser.parse_args()

    if not args.file_path.exists():
        logger.error("ファイルが見つかりません: %s", args.file_path)
        sys.exit(1)

    success = asyncio.run(run_import(args.file_path, args.dry_run))
    if not success:
        sys.exit(1)
