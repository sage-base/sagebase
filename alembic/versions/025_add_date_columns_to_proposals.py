"""proposalsテーブルにsubmitted_dateとvoted_dateカラムを追加.

Revision ID: 025
Revises: 024
Create Date: 2026-02-15

議案の提出日・採決日を保持するためのDATEカラム。
smartnews-smri由来の議案など、meetingと紐付かない議案の投票日特定に使用する。
"""

from alembic import op


revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: Add submitted_date and voted_date to proposals."""
    op.execute("""
        ALTER TABLE proposals ADD COLUMN IF NOT EXISTS submitted_date DATE;
        ALTER TABLE proposals ADD COLUMN IF NOT EXISTS voted_date DATE;
    """)


def downgrade() -> None:
    """Rollback migration: Remove submitted_date and voted_date from proposals."""
    op.execute("""
        ALTER TABLE proposals DROP COLUMN IF EXISTS voted_date;
        ALTER TABLE proposals DROP COLUMN IF EXISTS submitted_date;
    """)
