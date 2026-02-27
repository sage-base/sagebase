"""総務省参議院比例代表選挙データインポートスクリプト.

総務省が公開するXLS/XLSXファイルから参議院比例代表の当選者データをインポートする。

Usage (Docker経由で実行):
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/import_soumu_sangiin_proportional.py --election 26

    # 全選挙（第21回〜第27回）をインポート
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/import_soumu_sangiin_proportional.py --all

    # ドライラン（DB書き込みなし）
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/import_soumu_sangiin_proportional.py \
        --election 26 --dry-run

データソース:
    総務省 参議院議員通常選挙 選挙結果
    https://www.soumu.go.jp/senkyo/senkyo_s/data/sangiin/ichiran.html

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

from src.application.dtos.proportional_election_import_dto import (
    ImportProportionalElectionInputDto,
)
from src.application.usecases.import_proportional_election_usecase import (
    ImportProportionalElectionUseCase,
)
from src.infrastructure.config.async_database import get_async_session
from src.infrastructure.importers.soumu_sangiin_election_scraper import (
    SANGIIN_SUPPORTED_ELECTIONS,
)
from src.infrastructure.importers.soumu_sangiin_proportional_data_source import (
    SoumuSangiinProportionalDataSource,
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


async def run_import(election_number: int, dry_run: bool) -> bool:
    """1回分の参議院比例代表選挙データをインポートする."""
    logger.info("=== 第%d回参議院比例代表選挙データインポート開始 ===", election_number)

    async with get_async_session() as session:
        election_repo = ElectionRepositoryImpl(session)
        member_repo = ElectionMemberRepositoryImpl(session)
        politician_repo = PoliticianRepositoryImpl(session)
        party_repo = PoliticalPartyRepositoryImpl(session)
        data_source = SoumuSangiinProportionalDataSource()

        use_case = ImportProportionalElectionUseCase(
            election_repository=election_repo,
            election_member_repository=member_repo,
            politician_repository=politician_repo,
            political_party_repository=party_repo,
            proportional_data_source=data_source,
        )

        input_dto = ImportProportionalElectionInputDto(
            election_number=election_number,
            governing_body_id=GOVERNING_BODY_ID,
            dry_run=dry_run,
        )

        result = await use_case.execute(input_dto)

        logger.info("--- インポート結果 (第%d回 参議院比例代表) ---", election_number)
        logger.info("総候補者数: %d", result.total_candidates)
        logger.info("当選者数: %d", result.elected_candidates)
        logger.info("  比例当選: %d", result.proportional_elected)
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


async def main(
    election_numbers: list[int],
    dry_run: bool,
) -> None:
    """メイン処理."""
    success_count = 0
    fail_count = 0

    for election_number in election_numbers:
        try:
            success = await run_import(election_number, dry_run)
            if success:
                success_count += 1
            else:
                fail_count += 1
        except Exception:
            logger.exception("第%d回のインポートに失敗", election_number)
            fail_count += 1

    logger.info("=== 全体結果: 成功=%d, 失敗=%d ===", success_count, fail_count)
    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="総務省参議院比例代表選挙データをインポート",
        epilog=(
            "例: docker compose -f docker/docker-compose.yml exec sagebase "
            "uv run python scripts/import_soumu_sangiin_proportional.py --election 26"
        ),
    )
    parser.add_argument(
        "--election",
        type=int,
        choices=SANGIIN_SUPPORTED_ELECTIONS,
        help=(
            f"選挙回次（{min(SANGIIN_SUPPORTED_ELECTIONS)}"
            f"-{max(SANGIIN_SUPPORTED_ELECTIONS)}）"
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="import_all",
        help=(
            f"全選挙（第{min(SANGIIN_SUPPORTED_ELECTIONS)}回"
            f"〜第{max(SANGIIN_SUPPORTED_ELECTIONS)}回）をインポート"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（DB書き込みなし、抽出結果のみ表示）",
    )
    args = parser.parse_args()

    if not args.election and not args.import_all:
        parser.error("--election または --all を指定してください")

    if args.import_all:
        election_numbers = SANGIIN_SUPPORTED_ELECTIONS
    else:
        election_numbers = [args.election]

    asyncio.run(main(election_numbers, args.dry_run))
