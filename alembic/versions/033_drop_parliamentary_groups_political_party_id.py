"""parliamentary_groups.political_party_id カラムを削除.

Revision ID: 033
Revises: 032
Create Date: 2026-02-26

#1244 で parliamentary_group_parties 中間テーブルが導入済みのため、
旧来の political_party_id カラムを削除して二重管理状態を解消する。

関連: Issue #1246
"""

import sqlalchemy as sa

from alembic import op


revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # インデックスを削除（存在する場合）
    op.execute("DROP INDEX IF EXISTS idx_parliamentary_groups_political_party_id")

    # FK制約を削除（存在する場合）
    # 制約名は Alembic/PostgreSQL の自動命名規則に従う
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'parliamentary_groups_political_party_id_fkey'
                AND table_name = 'parliamentary_groups'
            ) THEN
                ALTER TABLE parliamentary_groups
                DROP CONSTRAINT parliamentary_groups_political_party_id_fkey;
            END IF;
        END $$;
    """)

    # カラムを削除
    op.drop_column("parliamentary_groups", "political_party_id")


def downgrade() -> None:
    # カラムを再追加
    op.add_column(
        "parliamentary_groups",
        sa.Column(
            "political_party_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    # FK制約を再作成
    op.create_foreign_key(
        "parliamentary_groups_political_party_id_fkey",
        "parliamentary_groups",
        "political_parties",
        ["political_party_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # インデックスを再作成
    op.create_index(
        "idx_parliamentary_groups_political_party_id",
        "parliamentary_groups",
        ["political_party_id"],
    )

    # 中間テーブルからデータを復元（is_primary=true のもの）
    op.execute("""
        UPDATE parliamentary_groups pg
        SET political_party_id = pgp.political_party_id
        FROM parliamentary_group_parties pgp
        WHERE pgp.parliamentary_group_id = pg.id
        AND pgp.is_primary = true
    """)
