"""smartnews-smri gian_summary.json インポートスクリプト."""

import argparse
import asyncio
import logging
import sys
import tempfile
import urllib.request

from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.application.dtos.smartnews_smri_import_dto import (
    ImportSmartNewsSmriInputDto,
)
from src.application.usecases.import_smartnews_smri_usecase import (
    ImportSmartNewsSmriUseCase,
)
from src.infrastructure.config.async_database import get_async_session
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.extracted_proposal_judge_repository_impl import (
    ExtractedProposalJudgeRepositoryImpl,
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

GOVERNING_BODY_NAME = "国会"
GOVERNING_BODY_TYPE = "国"
CONFERENCE_NAME = "衆議院"
SMRI_RAW_URL = (
    "https://raw.githubusercontent.com/"
    "smartnews-smri/house-of-representatives/main/data/gian_summary.json"
)


def fetch_gian_summary() -> Path:
    """GitHubからgian_summary.jsonをダウンロードして一時ファイルパスを返す."""
    logger.info("GitHubからダウンロード中: %s", SMRI_RAW_URL)
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    urllib.request.urlretrieve(SMRI_RAW_URL, tmp.name)  # noqa: S310
    logger.info(
        "ダウンロード完了: %s (%.1f MB)",
        tmp.name,
        Path(tmp.name).stat().st_size / 1_000_000,
    )
    return Path(tmp.name)


async def main(file_path: Path | None, batch_size: int, conference_name: str) -> None:
    auto_fetched = False
    if file_path is None:
        file_path = fetch_gian_summary()
        auto_fetched = True
    try:
        await _run_import(file_path, batch_size, conference_name)
    finally:
        if auto_fetched:
            file_path.unlink(missing_ok=True)


async def _run_import(file_path: Path, batch_size: int, conference_name: str) -> None:
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

        conf_repo = ConferenceRepositoryImpl(session)
        conference = await conf_repo.get_by_name_and_governing_body(
            conference_name, governing_body.id
        )
        if conference is None or conference.id is None:
            logger.error(
                "会議体 '%s' (開催主体ID=%d) が見つかりません。"
                "マスターデータを確認してください。",
                conference_name,
                governing_body.id,
            )
            sys.exit(1)

        logger.info(
            "会議体: %s (ID=%d)",
            conference.name,
            conference.id,
        )

        proposal_repo = ProposalRepositoryImpl(session)
        judge_repo = ExtractedProposalJudgeRepositoryImpl(session)
        use_case = ImportSmartNewsSmriUseCase(
            proposal_repository=proposal_repo,
            extracted_proposal_judge_repository=judge_repo,
        )

        input_dto = ImportSmartNewsSmriInputDto(
            file_path=file_path,
            governing_body_id=governing_body.id,
            conference_id=conference.id,
            batch_size=batch_size,
        )
        result = await use_case.execute(input_dto)

        logger.info("--- インポート結果 ---")
        logger.info("合計: %d", result.total)
        logger.info("作成: %d", result.created)
        logger.info("スキップ: %d", result.skipped)
        logger.info("更新(日付バックフィル): %d", result.updated)
        logger.info("エラー: %d", result.errors)
        logger.info("賛否データ: %d", result.judges_created)

        if result.errors > 0:
            sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="smartnews-smri gian_summary.json をインポート"
    )
    parser.add_argument(
        "file_path",
        type=Path,
        nargs="?",
        default=None,
        help="gian_summary.json のパス（省略時はGitHubから自動取得）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="バッチサイズ (デフォルト: 100)",
    )
    parser.add_argument(
        "--conference-name",
        type=str,
        default=CONFERENCE_NAME,
        help=f"会議体名 (デフォルト: {CONFERENCE_NAME})",
    )
    args = parser.parse_args()

    if args.file_path is not None and not args.file_path.exists():
        logger.error("ファイルが見つかりません: %s", args.file_path)
        sys.exit(1)

    asyncio.run(main(args.file_path, args.batch_size, args.conference_name))
