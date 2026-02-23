#!/usr/bin/env python3
"""政党所属履歴マイグレーション（028）の検証スクリプト.

移行後の整合性を確認し、結果をログ出力する。

実行方法:
  docker compose exec sagebase uv run python \
    scripts/verify_party_membership_migration.py
"""

import asyncio
import os
import sys

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


sys.path.insert(0, str(Path(__file__).parent.parent))

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://sagebase_user:sagebase_password@postgres:5432/sagebase_db",
)


async def verify_migration(session: AsyncSession) -> bool:
    """マイグレーション028の整合性を検証する."""
    all_passed = True

    # 1. 移行対象件数の確認
    result = await session.execute(
        text("""
            SELECT COUNT(*)
            FROM politicians
            WHERE political_party_id IS NOT NULL
        """)
    )
    target_count = result.scalar_one()

    result = await session.execute(
        text("""
            SELECT COUNT(*)
            FROM party_membership_history pmh
            WHERE pmh.end_date IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM politicians p
                  WHERE p.id = pmh.politician_id
                    AND p.political_party_id = pmh.political_party_id
              )
        """)
    )
    migrated_count = result.scalar_one()

    print(f"[検証1] 移行対象件数: {target_count}")
    print(f"[検証1] 実際の移行件数: {migrated_count}")
    if target_count == migrated_count:
        print("[検証1] OK: 全件移行済み")
    else:
        print(f"[検証1] NG: {target_count - migrated_count}件の移行漏れ")
        all_passed = False

    # 2. 不整合レコードの検出（politiciansにあるがhistoryにない）
    result = await session.execute(
        text("""
            SELECT p.id, p.name, p.political_party_id
            FROM politicians p
            WHERE p.political_party_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM party_membership_history pmh
                  WHERE pmh.politician_id = p.id
                    AND pmh.political_party_id = p.political_party_id
                    AND pmh.end_date IS NULL
              )
            ORDER BY p.id
            LIMIT 20
        """)
    )
    missing_rows = result.fetchall()

    if not missing_rows:
        print("[検証2] OK: 移行漏れレコードなし")
    else:
        print(f"[検証2] NG: {len(missing_rows)}件の移行漏れを検出（最大20件表示）")
        for row in missing_rows:
            print(f"  - politician_id={row[0]}, name={row[1]}, party_id={row[2]}")
        all_passed = False

    # 3. start_dateの妥当性チェック（NULLがないこと）
    result = await session.execute(
        text("""
            SELECT COUNT(*)
            FROM party_membership_history
            WHERE start_date IS NULL
        """)
    )
    null_start_count = result.scalar_one()

    if null_start_count == 0:
        print("[検証3] OK: start_dateがNULLのレコードなし")
    else:
        print(f"[検証3] NG: start_dateがNULLのレコードが{null_start_count}件")
        all_passed = False

    # 4. 選挙データ由来のstart_date件数
    result = await session.execute(
        text("""
            SELECT COUNT(*)
            FROM party_membership_history pmh
            WHERE pmh.end_date IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM politicians p
                  WHERE p.id = pmh.politician_id
                    AND p.political_party_id = pmh.political_party_id
              )
              AND pmh.start_date = (
                  SELECT MIN(e.election_date)
                  FROM election_members em
                  JOIN elections e ON e.id = em.election_id
                  WHERE em.politician_id = pmh.politician_id
              )
        """)
    )
    election_based_count = result.scalar_one()

    created_at_based_count = migrated_count - election_based_count
    print("[検証4] start_dateの内訳:")
    print(f"  - 選挙データ由来: {election_based_count}件")
    print(f"  - created_at由来: {created_at_based_count}件")

    # 5. party_membership_history全体の件数
    result = await session.execute(
        text("SELECT COUNT(*) FROM party_membership_history")
    )
    total_history_count = result.scalar_one()
    print(f"[検証5] party_membership_historyの総レコード数: {total_history_count}")

    return all_passed


async def main() -> None:
    """メイン実行関数."""
    print("=" * 60)
    print("政党所属履歴マイグレーション（028）検証")
    print("=" * 60)

    db_url = DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        async with conn.begin():
            session = AsyncSession(bind=conn)
            passed = await verify_migration(session)

    await engine.dispose()

    print("=" * 60)
    if passed:
        print("結果: 全検証項目がパスしました")
    else:
        print("結果: 一部の検証項目が失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
