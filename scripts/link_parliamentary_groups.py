"""政党所属議員の会派自動紐付けスクリプト.

国会選挙で当選した政党所属議員を、中間テーブル（parliamentary_group_parties）に基づいて
会派（parliamentary_group）に自動紐付けする。

Usage (Docker経由で実行):
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/link_parliamentary_groups.py --election 50

    # 院名を指定して実行
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/link_parliamentary_groups.py \
        --election 50 --chamber 衆議院

    # ドライラン（DB書き込みなし）
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/link_parliamentary_groups.py --election 50 --dry-run

前提条件:
    - Docker環境が起動済み（just up-detached）
    - マスターデータ（開催主体「国会」ID=1）がロード済み
    - Alembicマイグレーション適用済み
    - 選挙データ・当選者データがインポート済み
"""

import argparse
import asyncio
import logging
import sys

from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
from src.infrastructure.persistence.parliamentary_group_party_repository_impl import (
    ParliamentaryGroupPartyRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.party_membership_history_repository_impl import (
    PartyMembershipHistoryRepositoryImpl,
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


async def run_link(term_number: int, dry_run: bool, chamber: str = "") -> bool:
    """会派紐付けを実行する."""
    logger.info(
        "=== 第%d回選挙 会派自動紐付け開始 %s===",
        term_number,
        "(ドライラン) " if dry_run else "",
    )

    async with get_async_session() as session:
        use_case = LinkParliamentaryGroupUseCase(
            election_repository=ElectionRepositoryImpl(session),
            election_member_repository=ElectionMemberRepositoryImpl(session),
            politician_repository=PoliticianRepositoryImpl(session),
            parliamentary_group_repository=ParliamentaryGroupRepositoryImpl(session),
            parliamentary_group_membership_repository=ParliamentaryGroupMembershipRepositoryImpl(
                session
            ),
            party_membership_history_repository=PartyMembershipHistoryRepositoryImpl(
                session
            ),
            parliamentary_group_party_repository=ParliamentaryGroupPartyRepositoryImpl(
                session
            ),
        )

        input_dto = LinkParliamentaryGroupInputDto(
            term_number=term_number,
            governing_body_id=GOVERNING_BODY_ID,
            chamber=chamber,
            dry_run=dry_run,
        )

        result = await use_case.execute(input_dto)

        logger.info("--- 紐付け結果 (第%d回) ---", term_number)
        logger.info("当選者数: %d", result.total_elected)
        logger.info("紐付け成功: %d", result.linked_count)
        logger.info("既存スキップ: %d", result.already_existed_count)
        logger.info("政党未設定スキップ: %d", result.skipped_no_party)
        logger.info("会派なしスキップ: %d", result.skipped_no_group)
        logger.info("複数会派スキップ: %d", result.skipped_multiple_groups)
        logger.info("エラー: %d", result.errors)

        if result.linked_members:
            logger.info("--- 紐付け詳細 ---")
            for m in result.linked_members:
                status = "既存" if m.was_existing else "新規"
                logger.info(
                    "  [%s] %s → %s",
                    status,
                    m.politician_name,
                    m.parliamentary_group_name,
                )

        if result.skipped_members:
            logger.info("--- スキップ詳細 ---")
            for s in result.skipped_members:
                logger.info("  %s: %s", s.politician_name, s.reason)

        if result.error_details:
            for detail in result.error_details:
                logger.error("  %s", detail)

        return result.errors == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="政党所属議員の会派自動紐付け",
        epilog=(
            "例: docker compose -f docker/docker-compose.yml exec sagebase "
            "uv run python scripts/link_parliamentary_groups.py --election 50"
        ),
    )
    parser.add_argument(
        "--election",
        type=int,
        required=True,
        help="選挙回次（例: 50）",
    )
    parser.add_argument(
        "--chamber",
        type=str,
        choices=["衆議院", "参議院"],
        default="",
        help="院名でフィルタ（省略時は全会派を対象）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（DB書き込みなし、紐付け結果のみ表示）",
    )
    args = parser.parse_args()

    success = asyncio.run(run_link(args.election, args.dry_run, args.chamber))
    if not success:
        sys.exit(1)
