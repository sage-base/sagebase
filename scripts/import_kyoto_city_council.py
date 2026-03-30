"""京都市議会（京都市会）データ一括登録スクリプト.

京都市議会の議員（Politician）、会派（ParliamentaryGroup）、
会派所属（ParliamentaryGroupMembership）、会議体（Conference）を一括登録する。

データソース:
    - 議員名簿: https://www2.city.kyoto.lg.jp/shikai/meibo/index.html
    - 会派一覧: https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/index.html
    - 2026年2月時点のデータ（定数67名）

Usage (Docker経由で実行):
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/import_kyoto_city_council.py

    # ドライラン（DB書き込みなし）
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/import_kyoto_city_council.py --dry-run

前提条件:
    - Docker環境が起動済み（just up-detached）
    - GoverningBody「京都府京都市」が登録済み
    - Alembicマイグレーション適用済み
"""

import argparse
import asyncio
import logging
import sys

from dataclasses import dataclass
from datetime import date
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.domain.entities.conference import Conference
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.politician import Politician
from src.infrastructure.config.async_database import get_async_session
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_membership_repository_impl import (  # noqa: E501
    ParliamentaryGroupMembershipRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 京都市議会議員の任期開始日（2023年統一地方選挙）
TERM_START_DATE = date(2023, 5, 1)

BASE_URL = "https://www2.city.kyoto.lg.jp/shikai/meibo"


# --- データ定義 ---
# データソース: https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/ （2026年2月時点）


@dataclass
class PoliticianData:
    """議員データ."""

    name: str
    district: str  # 選挙区（行政区）
    group: str  # 会派名
    role: str | None = None  # 会派内の役職


# 会派URL
GROUP_URLS: dict[str, str] = {
    "自由民主党京都市会議員団": "https://jimin-kyoto.jp/",
    "維新・京都・国民市会議員団": "https://ishin-kyoto-kokumin.com",
    "日本共産党京都市会議員団": "https://cpgkyoto.jp/",
    "公明党京都市会議員団": "https://www.komeito-kyotocity.com/",
    "無所属": f"{BASE_URL}/kaiha/mushozoku.html",
}

# 全67名の議員データ（会派別）
POLITICIANS: list[PoliticianData] = [
    # --- 自由民主党京都市会議員団（19名）---
    PoliticianData("橋村芳和", "伏見区", "自由民主党京都市会議員団", "団長"),
    PoliticianData("さくらい泰広", "左京区", "自由民主党京都市会議員団", "副団長"),
    PoliticianData("井上よしひろ", "右京区", "自由民主党京都市会議員団"),
    PoliticianData("加藤昌洋", "中京区", "自由民主党京都市会議員団"),
    PoliticianData("しまもと京司", "南区", "自由民主党京都市会議員団"),
    PoliticianData("下村あきら", "下京区", "自由民主党京都市会議員団"),
    PoliticianData("田中明秀", "西京区", "自由民主党京都市会議員団"),
    PoliticianData("田中たかのり", "右京区", "自由民主党京都市会議員団"),
    PoliticianData("谷口みゆき", "北区", "自由民主党京都市会議員団"),
    PoliticianData("津田大三", "中京区", "自由民主党京都市会議員団"),
    PoliticianData("寺田一博", "上京区", "自由民主党京都市会議員団"),
    PoliticianData("富きくお", "山科区", "自由民主党京都市会議員団"),
    PoliticianData("西村義直", "西京区", "自由民主党京都市会議員団"),
    PoliticianData("平山たかお", "東山区", "自由民主党京都市会議員団"),
    PoliticianData("みちはた弘之", "伏見区", "自由民主党京都市会議員団"),
    PoliticianData("椋田隆知", "南区", "自由民主党京都市会議員団"),
    PoliticianData("森田守", "右京区", "自由民主党京都市会議員団"),
    PoliticianData("山本恵一", "北区", "自由民主党京都市会議員団"),
    PoliticianData("山本しゅうじ", "山科区", "自由民主党京都市会議員団"),
    # --- 維新・京都・国民市会議員団（16名）---
    PoliticianData("江村理紗", "右京区", "維新・京都・国民市会議員団", "団長"),
    PoliticianData("中野洋一", "東山区", "維新・京都・国民市会議員団", "副団長"),
    PoliticianData("宇佐美賢一", "左京区", "維新・京都・国民市会議員団"),
    PoliticianData("大津裕太", "中京区", "維新・京都・国民市会議員団"),
    PoliticianData("おんづか功", "左京区", "維新・京都・国民市会議員団"),
    PoliticianData("片桐直哉", "北区", "維新・京都・国民市会議員団"),
    PoliticianData("神谷修平", "下京区", "維新・京都・国民市会議員団"),
    PoliticianData("河村諒", "左京区", "維新・京都・国民市会議員団"),
    PoliticianData("北尾ゆか", "下京区", "維新・京都・国民市会議員団"),
    PoliticianData("北川みき", "西京区", "維新・京都・国民市会議員団"),
    PoliticianData("久保田正紀", "伏見区", "維新・京都・国民市会議員団"),
    PoliticianData("こうち大輔", "右京区", "維新・京都・国民市会議員団"),
    PoliticianData("中高しゅうじ", "上京区", "維新・京都・国民市会議員団"),
    PoliticianData("土方莉紗", "南区", "維新・京都・国民市会議員団"),
    PoliticianData("森かれん", "上京区", "維新・京都・国民市会議員団"),
    PoliticianData("もりもと英靖", "伏見区", "維新・京都・国民市会議員団"),
    # --- 日本共産党京都市会議員団（14名）---
    PoliticianData("西野さち子", "伏見区", "日本共産党京都市会議員団", "団長"),
    PoliticianData("北山ただお", "山科区", "日本共産党京都市会議員団", "副団長"),
    PoliticianData("赤阪仁", "伏見区", "日本共産党京都市会議員団"),
    PoliticianData("えもとかよこ", "右京区", "日本共産党京都市会議員団"),
    PoliticianData("加藤あい", "左京区", "日本共産党京都市会議員団"),
    PoliticianData("河合ようこ", "西京区", "日本共産党京都市会議員団"),
    PoliticianData("くらた共子", "上京区", "日本共産党京都市会議員団"),
    PoliticianData("玉本なるみ", "北区", "日本共産党京都市会議員団"),
    PoliticianData("とがし豊", "左京区", "日本共産党京都市会議員団"),
    PoliticianData("平井良人", "中京区", "日本共産党京都市会議員団"),
    PoliticianData("森田ゆみ子", "南区", "日本共産党京都市会議員団"),
    PoliticianData("山田こうじ", "右京区", "日本共産党京都市会議員団"),
    PoliticianData("やまね智史", "伏見区", "日本共産党京都市会議員団"),
    PoliticianData("山本陽子", "山科区", "日本共産党京都市会議員団"),
    # --- 公明党京都市会議員団（11名）---
    PoliticianData("青野仁志", "中京区", "公明党京都市会議員団", "団長"),
    PoliticianData("かわしま優子", "伏見区", "公明党京都市会議員団"),
    PoliticianData("くまざわ真昭", "左京区", "公明党京都市会議員団"),
    PoliticianData("中村まり", "南区", "公明党京都市会議員団"),
    PoliticianData("西山信昌", "下京区", "公明党京都市会議員団"),
    PoliticianData("兵藤しんいち", "北区", "公明党京都市会議員団"),
    PoliticianData("平山よしかず", "西京区", "公明党京都市会議員団"),
    PoliticianData("増成竜治", "伏見区", "公明党京都市会議員団"),
    PoliticianData("松田けい子", "山科区", "公明党京都市会議員団"),
    PoliticianData("湯浅光彦", "右京区", "公明党京都市会議員団"),
    PoliticianData("吉田孝雄", "伏見区", "公明党京都市会議員団"),
    # --- 無所属（7名）---
    PoliticianData("天方ひろゆき", "西京区", "無所属"),
    PoliticianData("井﨑敦子", "左京区", "無所属"),
    PoliticianData("きくち一秀", "右京区", "無所属"),
    PoliticianData("小島信太郎", "山科区", "無所属"),
    PoliticianData("繁隆夫", "伏見区", "無所属"),
    PoliticianData("菅谷浩平", "北区", "無所属"),
    PoliticianData("平田圭", "伏見区", "無所属"),
]

# 会議体データ
CONFERENCES: list[str] = [
    # 本会議
    "京都市会本会議",
    # 常任委員会（5つ）
    "総務消防委員会",
    "環境福祉委員会",
    "文教はぐくみ委員会",
    "まちづくり委員会",
    "産業交通水道委員会",
    # 特別委員会
    "予算特別委員会",
    "決算特別委員会",
    # 市会運営委員会
    "市会運営委員会",
]


async def import_politicians(
    politician_repo: PoliticianRepositoryImpl,
    dry_run: bool,
) -> dict[str, Politician]:
    """議員を登録し、名前→Politicianエンティティのマッピングを返す."""
    logger.info("=== 議員登録 (%d名) ===", len(POLITICIANS))
    name_to_politician: dict[str, Politician] = {}
    created_count = 0
    existing_count = 0

    for p in POLITICIANS:
        existing = await politician_repo.get_by_name(p.name)
        if existing:
            logger.info("  既存: %s（%s）", p.name, p.district)
            name_to_politician[p.name] = existing
            existing_count += 1
            continue

        if dry_run:
            logger.info(
                "  [DRY-RUN] 作成予定: %s（%s / %s）",
                p.name,
                p.district,
                p.group,
            )
            created_count += 1
            continue

        politician = Politician(
            name=p.name,
            prefecture="京都府",
            district=p.district,
        )
        created = await politician_repo.create(politician)
        name_to_politician[p.name] = created
        created_count += 1
        logger.info("  作成: %s（%s）ID=%d", p.name, p.district, created.id)

    logger.info("議員登録完了: 新規=%d, 既存=%d", created_count, existing_count)
    return name_to_politician


async def import_parliamentary_groups(
    pg_repo: ParliamentaryGroupRepositoryImpl,
    governing_body_id: int,
    dry_run: bool,
) -> dict[str, ParliamentaryGroup]:
    """会派を登録し、名前→ParliamentaryGroupエンティティのマッピングを返す."""
    group_names = list(GROUP_URLS.keys())
    logger.info("=== 会派登録 (%d会派) ===", len(group_names))
    name_to_group: dict[str, ParliamentaryGroup] = {}
    created_count = 0
    existing_count = 0

    for group_name in group_names:
        existing = await pg_repo.get_by_name_and_governing_body(
            name=group_name,
            governing_body_id=governing_body_id,
            chamber="",
        )
        if existing:
            logger.info("  既存: %s (ID=%d)", group_name, existing.id)
            name_to_group[group_name] = existing
            existing_count += 1
            continue

        if dry_run:
            logger.info("  [DRY-RUN] 作成予定: %s", group_name)
            created_count += 1
            continue

        pg = ParliamentaryGroup(
            name=group_name,
            governing_body_id=governing_body_id,
            url=GROUP_URLS.get(group_name),
            is_active=True,
            chamber="",
        )
        created = await pg_repo.create(pg)
        name_to_group[group_name] = created
        created_count += 1
        logger.info("  作成: %s (ID=%d)", group_name, created.id)

    logger.info("会派登録完了: 新規=%d, 既存=%d", created_count, existing_count)
    return name_to_group


async def import_memberships(
    membership_repo: ParliamentaryGroupMembershipRepositoryImpl,
    name_to_politician: dict[str, Politician],
    name_to_group: dict[str, ParliamentaryGroup],
    dry_run: bool,
) -> None:
    """会派所属を登録する."""
    logger.info("=== 会派所属登録 ===")
    created_count = 0
    existing_count = 0
    skipped_count = 0

    for p in POLITICIANS:
        politician = name_to_politician.get(p.name)
        group = name_to_group.get(p.group)

        if not politician or not group:
            logger.warning(
                "  スキップ: %s（政治家またはグループが見つからない）",
                p.name,
            )
            skipped_count += 1
            continue

        if dry_run:
            logger.info(
                "  [DRY-RUN] 紐付け予定: %s → %s%s",
                p.name,
                p.group,
                f" ({p.role})" if p.role else "",
            )
            created_count += 1
            continue

        assert politician.id is not None
        assert group.id is not None
        membership = await membership_repo.add_membership(
            politician_id=politician.id,
            parliamentary_group_id=group.id,
            start_date=TERM_START_DATE,
            role=p.role,
        )
        if membership:
            created_count += 1
            logger.info(
                "  紐付け: %s → %s (ID=%d)",
                p.name,
                p.group,
                membership.id,
            )
        else:
            existing_count += 1

    logger.info(
        "会派所属登録完了: 新規=%d, 既存=%d, スキップ=%d",
        created_count,
        existing_count,
        skipped_count,
    )


async def import_conferences(
    conference_repo: ConferenceRepositoryImpl,
    governing_body_id: int,
    dry_run: bool,
) -> None:
    """会議体を登録する."""
    logger.info("=== 会議体登録 (%d件) ===", len(CONFERENCES))
    created_count = 0
    existing_count = 0

    for conf_name in CONFERENCES:
        existing = await conference_repo.get_by_name_and_governing_body(
            name=conf_name,
            governing_body_id=governing_body_id,
        )
        if existing:
            logger.info("  既存: %s (ID=%d)", conf_name, existing.id)
            existing_count += 1
            continue

        if dry_run:
            logger.info("  [DRY-RUN] 作成予定: %s", conf_name)
            created_count += 1
            continue

        conference = Conference(
            name=conf_name,
            governing_body_id=governing_body_id,
        )
        created = await conference_repo.create(conference)
        created_count += 1
        logger.info("  作成: %s (ID=%d)", conf_name, created.id)

    logger.info("会議体登録完了: 新規=%d, 既存=%d", created_count, existing_count)


async def run_import(dry_run: bool) -> bool:
    """京都市議会データの一括登録を実行する."""
    logger.info(
        "=== 京都市議会データ登録開始 %s===",
        "(ドライラン) " if dry_run else "",
    )

    async with get_async_session() as session:
        # GoverningBody（京都府京都市）を取得
        gb_repo = GoverningBodyRepositoryImpl(session)
        kyoto_city = await gb_repo.get_by_name_and_type(
            name="京都府京都市", type="市町村"
        )
        if not kyoto_city:
            logger.error("GoverningBody「京都府京都市」が見つかりません")
            return False

        assert kyoto_city.id is not None
        governing_body_id: int = kyoto_city.id
        logger.info("GoverningBody: %s (ID=%d)", kyoto_city.name, governing_body_id)

        # リポジトリ初期化
        politician_repo = PoliticianRepositoryImpl(session)
        pg_repo = ParliamentaryGroupRepositoryImpl(session)
        membership_repo = ParliamentaryGroupMembershipRepositoryImpl(session)
        conference_repo = ConferenceRepositoryImpl(session)

        # 1. 議員登録
        name_to_politician = await import_politicians(politician_repo, dry_run)

        # 2. 会派登録
        name_to_group = await import_parliamentary_groups(
            pg_repo, governing_body_id, dry_run
        )

        # 3. 会派所属登録
        await import_memberships(
            membership_repo, name_to_politician, name_to_group, dry_run
        )

        # 4. 会議体登録
        await import_conferences(conference_repo, governing_body_id, dry_run)

        if not dry_run:
            await session.commit()
            logger.info("=== コミット完了 ===")

    logger.info("=== 京都市議会データ登録完了 ===")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="京都市議会（京都市会）データ一括登録",
        epilog=(
            "例: docker compose -f docker/docker-compose.yml exec sagebase "
            "uv run python scripts/import_kyoto_city_council.py"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（DB書き込みなし、登録予定データのみ表示）",
    )
    args = parser.parse_args()

    success = asyncio.run(run_import(args.dry_run))
    if not success:
        sys.exit(1)
