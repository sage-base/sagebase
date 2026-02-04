"""conferencesテーブルからtypeカラムを削除.

Revision ID: 015
Revises: 014
Create Date: 2026-02-04

会議体の種別(type)は不要になったため削除する。
"""

from alembic import op


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: remove type column from conferences."""
    op.execute("""
        -- typeカラムを削除
        ALTER TABLE conferences
        DROP COLUMN IF EXISTS type;
    """)


def downgrade() -> None:
    """Rollback migration: add type column back to conferences."""
    op.execute("""
        -- typeカラムを追加（NULL許容）
        ALTER TABLE conferences
        ADD COLUMN IF NOT EXISTS type VARCHAR(100);

        -- カラムコメントを追加
        COMMENT ON COLUMN conferences.type IS '会議体の種別（例: 本会議, 委員会）';
    """)
