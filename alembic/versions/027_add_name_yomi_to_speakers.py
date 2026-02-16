"""speakersテーブルにname_yomiカラムを追加.

Revision ID: 027
Revises: 026
Create Date: 2026-02-16

国会会議録APIのspeakerYomiフィールドを保存するためのカラム。
NULLは「よみがな未設定」を意味する。
"""

from alembic import op


revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: Add name_yomi to speakers."""
    op.execute("""
        ALTER TABLE speakers
        ADD COLUMN IF NOT EXISTS name_yomi VARCHAR(255) DEFAULT NULL;
    """)


def downgrade() -> None:
    """Rollback migration: Remove name_yomi from speakers."""
    op.execute("""
        ALTER TABLE speakers DROP COLUMN IF EXISTS name_yomi;
    """)
