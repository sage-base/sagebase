"""時代整合性バリデーションテスト

同一政治家の所属期間重複、会派存続期間との整合性、
同一政党の並行会派など、時間軸に関するデータ整合性をチェックする。

Issue #1392
"""

from collections.abc import Generator

import pytest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.infrastructure.config.database import DATABASE_URL


@pytest.fixture(scope="function")
def db_session() -> Generator[Session]:
    """読み取り専用のDBセッションを作成する"""
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    transaction = connection.begin()

    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


def test_no_overlapping_party_memberships(db_session: Session) -> None:
    """同一政治家の政党所属期間が重複していないことを検証する。

    同じ政治家が同時に複数の政党に所属することはできない。
    start_dateが同日の場合は重複とみなさない（前日終了→翌日開始の切り替え）。
    """
    result = db_session.execute(
        text("""
            SELECT
                pmh1.id AS id1,
                pmh1.politician_id,
                pmh1.political_party_id AS party1,
                pmh1.start_date AS start1,
                pmh1.end_date AS end1,
                pmh2.id AS id2,
                pmh2.political_party_id AS party2,
                pmh2.start_date AS start2,
                pmh2.end_date AS end2
            FROM party_membership_history pmh1
            JOIN party_membership_history pmh2
                ON pmh1.politician_id = pmh2.politician_id
                AND pmh1.id < pmh2.id
            WHERE pmh1.start_date IS NOT NULL
                AND pmh2.start_date IS NOT NULL
                AND pmh1.start_date < COALESCE(pmh2.end_date, '9999-12-31')
                AND pmh2.start_date < COALESCE(pmh1.end_date, '9999-12-31')
            ORDER BY pmh1.politician_id, pmh1.start_date
        """)
    )
    rows = result.fetchall()

    if rows:
        details = "\n".join(
            f"  politician_id={r.politician_id}, "
            f"party {r.party1}({r.start1}~{r.end1}) ↔ "
            f"party {r.party2}({r.start2}~{r.end2})"
            for r in rows[:20]
        )
        pytest.fail(f"政党所属期間の重複が{len(rows)}件見つかりました:\n{details}")


@pytest.mark.xfail(
    reason="既知のデータ不整合あり（#1391 memberships再紐付け完了後に解消予定）"
)
def test_membership_within_parliamentary_group_period(
    db_session: Session,
) -> None:
    """会派メンバーシップ期間が会派の存続期間内に収まっていることを検証する。

    メンバーシップのstart_dateは会派のstart_date以降、
    メンバーシップのend_dateは会派のend_date以前であること。
    会派のstart_date/end_dateがNULLの場合はチェック対象外。
    """
    result = db_session.execute(
        text("""
            SELECT
                pgm.id AS membership_id,
                pgm.politician_id,
                pgm.parliamentary_group_id,
                pgm.start_date AS mem_start,
                pgm.end_date AS mem_end,
                pg.name AS group_name,
                pg.start_date AS group_start,
                pg.end_date AS group_end
            FROM parliamentary_group_memberships pgm
            JOIN parliamentary_groups pg
                ON pg.id = pgm.parliamentary_group_id
            WHERE pg.start_date IS NOT NULL
                AND pgm.start_date IS NOT NULL
                AND (
                    pgm.start_date < pg.start_date
                    OR (
                        pg.end_date IS NOT NULL
                        AND COALESCE(pgm.end_date, '9999-12-31') > pg.end_date
                    )
                )
            ORDER BY pgm.parliamentary_group_id, pgm.politician_id
        """)
    )
    rows = result.fetchall()

    if rows:
        details = "\n".join(
            f"  membership_id={r.membership_id}, politician_id={r.politician_id}, "
            f"group={r.group_name}({r.group_start}~{r.group_end}), "
            f"membership=({r.mem_start}~{r.mem_end})"
            for r in rows[:20]
        )
        pytest.fail(
            f"会派存続期間外のメンバーシップが{len(rows)}件見つかりました:\n{details}"
        )


@pytest.mark.xfail(reason="既知のデータ不整合あり（会派の時代区分設定が未完了）")
def test_no_parallel_parliamentary_groups_for_same_party(
    db_session: Session,
) -> None:
    """同一政党が同一governing_body・同一chamberで並行する会派を持たないことを検証する。

    同じ政党が同じ議会・同じ院で同時期に複数の会派に所属することはない。
    start_dateがNULLの会派はチェック対象外。
    """
    result = db_session.execute(
        text("""
            SELECT
                pg1.id AS group1_id,
                pg1.name AS group1_name,
                pg1.start_date AS group1_start,
                pg1.end_date AS group1_end,
                pg2.id AS group2_id,
                pg2.name AS group2_name,
                pg2.start_date AS group2_start,
                pg2.end_date AS group2_end,
                pgp1.political_party_id,
                pg1.governing_body_id,
                pg1.chamber
            FROM parliamentary_group_parties pgp1
            JOIN parliamentary_group_parties pgp2
                ON pgp1.political_party_id = pgp2.political_party_id
                AND pgp1.parliamentary_group_id < pgp2.parliamentary_group_id
            JOIN parliamentary_groups pg1
                ON pg1.id = pgp1.parliamentary_group_id
            JOIN parliamentary_groups pg2
                ON pg2.id = pgp2.parliamentary_group_id
            WHERE pg1.governing_body_id = pg2.governing_body_id
                AND pg1.chamber = pg2.chamber
                AND pg1.start_date IS NOT NULL
                AND pg2.start_date IS NOT NULL
                AND pg1.start_date < COALESCE(pg2.end_date, '9999-12-31')
                AND pg2.start_date < COALESCE(pg1.end_date, '9999-12-31')
            ORDER BY pgp1.political_party_id, pg1.start_date
        """)
    )
    rows = result.fetchall()

    if rows:
        details = "\n".join(
            f"  party_id={r.political_party_id}, "
            f"governing_body={r.governing_body_id}, chamber={r.chamber}, "
            f"{r.group1_name}({r.group1_start}~{r.group1_end}) ↔ "
            f"{r.group2_name}({r.group2_start}~{r.group2_end})"
            for r in rows[:20]
        )
        pytest.fail(f"同一政党の並行会派が{len(rows)}件見つかりました:\n{details}")


@pytest.mark.xfail(
    reason="既知のデータ不整合あり（#1391 memberships再紐付け完了後に解消予定）"
)
def test_no_overlapping_parliamentary_group_memberships(
    db_session: Session,
) -> None:
    """同一政治家が同一governing_body・同一chamberで会派メンバーシップが重複しないことを検証する。

    同じ政治家が同じ議会・同じ院で同時期に複数の会派に所属することはない。
    """
    result = db_session.execute(
        text("""
            SELECT
                pgm1.id AS id1,
                pgm1.politician_id,
                pgm1.parliamentary_group_id AS group1_id,
                pg1.name AS group1_name,
                pgm1.start_date AS start1,
                pgm1.end_date AS end1,
                pgm2.id AS id2,
                pgm2.parliamentary_group_id AS group2_id,
                pg2.name AS group2_name,
                pgm2.start_date AS start2,
                pgm2.end_date AS end2
            FROM parliamentary_group_memberships pgm1
            JOIN parliamentary_group_memberships pgm2
                ON pgm1.politician_id = pgm2.politician_id
                AND pgm1.id < pgm2.id
            JOIN parliamentary_groups pg1
                ON pg1.id = pgm1.parliamentary_group_id
            JOIN parliamentary_groups pg2
                ON pg2.id = pgm2.parliamentary_group_id
            WHERE pg1.governing_body_id = pg2.governing_body_id
                AND pg1.chamber = pg2.chamber
                AND pgm1.start_date IS NOT NULL
                AND pgm2.start_date IS NOT NULL
                AND pgm1.start_date < COALESCE(pgm2.end_date, '9999-12-31')
                AND pgm2.start_date < COALESCE(pgm1.end_date, '9999-12-31')
            ORDER BY pgm1.politician_id, pgm1.start_date
        """)
    )
    rows = result.fetchall()

    if rows:
        details = "\n".join(
            f"  politician_id={r.politician_id}, "
            f"{r.group1_name}({r.start1}~{r.end1}) ↔ "
            f"{r.group2_name}({r.start2}~{r.end2})"
            for r in rows[:20]
        )
        pytest.fail(
            f"会派メンバーシップの重複が{len(rows)}件見つかりました:\n{details}"
        )
