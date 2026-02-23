"""politicians.political_party_idの既存データをparty_membership_historyに移行.

Revision ID: 028
Revises: 027
Create Date: 2026-02-23

Phase 2: 既存の政党所属データを履歴テーブルに移行する。
political_party_idカラムは過渡期にはそのまま残し、後続Phaseで段階的に廃止する。

start_date推定ロジック:
  - 第1優先: election_members + electionsテーブルから最古の選挙日を取得
  - フォールバック: politicians.created_at::dateを使用
"""

from alembic import op


revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: politiciansの政党所属データをparty_membership_historyに移行."""
    op.execute("""
        DO $$
        DECLARE
            migrated_count INTEGER;
        BEGIN
            INSERT INTO party_membership_history (
                politician_id,
                political_party_id,
                start_date,
                created_at,
                updated_at
            )
            SELECT
                p.id,
                p.political_party_id,
                COALESCE(
                    (
                        SELECT MIN(e.election_date)
                        FROM election_members em
                        JOIN elections e ON e.id = em.election_id
                        WHERE em.politician_id = p.id
                    ),
                    p.created_at::date
                ),
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            FROM politicians p
            WHERE p.political_party_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM party_membership_history pmh
                  WHERE pmh.politician_id = p.id
                    AND pmh.political_party_id = p.political_party_id
                    AND pmh.end_date IS NULL
              );

            GET DIAGNOSTICS migrated_count = ROW_COUNT;
            RAISE NOTICE '[028] party_membership_historyに%件のレコードを移行しました', migrated_count;
        END$$;
    """)


def downgrade() -> None:
    """Rollback migration: 移行したレコードのみを削除."""
    op.execute("""
        DO $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            DELETE FROM party_membership_history pmh
            WHERE pmh.end_date IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM politicians p
                  WHERE p.id = pmh.politician_id
                    AND p.political_party_id = pmh.political_party_id
              );

            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RAISE NOTICE '[028] party_membership_historyから%件のレコードを削除しました', deleted_count;
        END$$;
    """)
