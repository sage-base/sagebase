"""politicians.political_party_idカラムを削除する.

Revision ID: 029
Revises: 028
Create Date: 2026-02-23

Phase 4: party_membership_historyへの移行が完了したため、
politicians.political_party_idカラムを削除する。

関連する外部キー制約とインデックスも合わせて削除する。
"""

import sqlalchemy as sa

from alembic import op


revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: politicians.political_party_idカラムを削除."""
    # 1. インデックスを削除
    op.drop_index("idx_politicians_political_party", table_name="politicians")

    # 2. 外部キー制約を削除
    op.drop_constraint(
        "politicians_political_party_id_fkey", "politicians", type_="foreignkey"
    )

    # 3. カラムを削除
    op.drop_column("politicians", "political_party_id")


def downgrade() -> None:
    """Rollback migration: politicians.political_party_idカラムを復元."""
    # 1. カラムを再追加
    op.add_column(
        "politicians",
        sa.Column("political_party_id", sa.Integer(), nullable=True),
    )

    # 2. 外部キー制約を再追加
    op.create_foreign_key(
        "politicians_political_party_id_fkey",
        "politicians",
        "political_parties",
        ["political_party_id"],
        ["id"],
    )

    # 3. インデックスを再追加
    op.create_index(
        "idx_politicians_political_party",
        "politicians",
        ["political_party_id"],
    )

    # 4. party_membership_historyからデータを復元
    op.execute("""
        UPDATE politicians p
        SET political_party_id = pmh.political_party_id
        FROM (
            SELECT DISTINCT ON (politician_id)
                politician_id, political_party_id
            FROM party_membership_history
            WHERE end_date IS NULL
            ORDER BY politician_id, created_at DESC
        ) pmh
        WHERE p.id = pmh.politician_id
    """)
