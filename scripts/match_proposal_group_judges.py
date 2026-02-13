"""会派賛否マッチングスクリプト.

extracted_proposal_judges（Bronze層）の会派名を
parliamentary_groups（SEED）と突合し、
proposal_parliamentary_group_judges（Gold層）に書き込む。

Usage (Docker経由で実行):
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/match_proposal_group_judges.py

    # dry-runモード（Gold層に書き込まず、マッチング結果のみ確認）
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/match_proposal_group_judges.py --dry-run

前提条件:
    - Docker環境が起動済み（just up-detached）
    - マスターデータ（開催主体「日本国」）がロード済み
    - 議員団シードデータ（seed_parliamentary_groups_generated.sql）がロード済み
    - import_smartnews_smri.py で議案・賛否データがインポート済み
"""

import argparse
import asyncio
import logging
import sys

from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.application.dtos.match_proposal_group_judges_dto import (
    MatchProposalGroupJudgesInputDto,
)
from src.application.usecases.match_proposal_group_judges_usecase import (
    MatchProposalGroupJudgesUseCase,
)
from src.infrastructure.config.async_database import get_async_session
from src.infrastructure.persistence.extracted_proposal_judge_repository_impl import (
    ExtractedProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.proposal_parliamentary_group_judge_repository_impl import (  # noqa: E501
    ProposalParliamentaryGroupJudgeRepositoryImpl,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

GOVERNING_BODY_NAME = "国会"
GOVERNING_BODY_TYPE = "国"


async def main(dry_run: bool) -> None:
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

        logger.info(
            "開催主体: %s (ID=%d)",
            governing_body.name,
            governing_body.id,
        )

        extracted_repo = ExtractedProposalJudgeRepositoryImpl(session)
        group_repo = ParliamentaryGroupRepositoryImpl(session)
        judge_repo = ProposalParliamentaryGroupJudgeRepositoryImpl(session)

        use_case = MatchProposalGroupJudgesUseCase(
            extracted_proposal_judge_repository=extracted_repo,
            parliamentary_group_repository=group_repo,
            proposal_group_judge_repository=judge_repo,
        )

        input_dto = MatchProposalGroupJudgesInputDto(
            governing_body_id=governing_body.id,
            dry_run=dry_run,
        )
        result = await use_case.execute(input_dto)

        logger.info("--- マッチング結果 ---")
        logger.info("対象レコード: %d", result.total_pending)
        logger.info("マッチ成功: %d", result.matched)
        logger.info("マッチ失敗: %d", result.unmatched)
        logger.info("Gold層作成: %d", result.judges_created)

        if result.unmatched_names:
            logger.info("--- マッチングできなかった会派名 ---")
            for name in result.unmatched_names:
                logger.info("  - %s", name)

        if result.unmatched > 0:
            sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="会派賛否マッチング: Bronze層→Gold層への変換",
        epilog=(
            "例: docker compose -f docker/docker-compose.yml exec sagebase "
            "uv run python scripts/match_proposal_group_judges.py --dry-run"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="マッチングのみ実行しGold層への書き込みをスキップ（デフォルト: False）",
    )
    args = parser.parse_args()

    asyncio.run(main(args.dry_run))
