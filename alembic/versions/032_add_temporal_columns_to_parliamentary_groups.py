"""parliamentary_groupsテーブルにstart_date/end_dateカラムを追加.

Revision ID: 032
Revises: 031
Create Date: 2026-02-26

会派の時代管理を実現するため、有効期間（start_date/end_date）を追加する。
is_activeフラグとの段階的移行を可能にするため、両カラムともNULL許容。

関連: Issue #1241, ADR 0009
"""

from alembic import op


revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """会派テーブルに有効期間カラムとインデックスを追加."""
    op.execute("""
        ALTER TABLE parliamentary_groups
        ADD COLUMN IF NOT EXISTS start_date DATE;

        ALTER TABLE parliamentary_groups
        ADD COLUMN IF NOT EXISTS end_date DATE;

        COMMENT ON COLUMN parliamentary_groups.start_date
            IS '会派の有効開始日（NULL = 不明/未設定）';
        COMMENT ON COLUMN parliamentary_groups.end_date
            IS '会派の有効終了日（NULL = 現在も有効 or 不明/未設定）';

        CREATE INDEX IF NOT EXISTS idx_parliamentary_groups_start_date
            ON parliamentary_groups(start_date);

        CREATE INDEX IF NOT EXISTS idx_parliamentary_groups_end_date
            ON parliamentary_groups(end_date);
    """)


def downgrade() -> None:
    """有効期間カラムとインデックスを削除."""
    op.execute("""
        DROP INDEX IF EXISTS idx_parliamentary_groups_end_date;
        DROP INDEX IF EXISTS idx_parliamentary_groups_start_date;

        ALTER TABLE parliamentary_groups
        DROP COLUMN IF EXISTS end_date;

        ALTER TABLE parliamentary_groups
        DROP COLUMN IF EXISTS start_date;
    """)
