"""proposal_judgesテーブルにis_defectionカラムを追加.

Revision ID: 026
Revises: 025
Create Date: 2026-02-15

記名投票上書き時に会派方針との造反を記録するためのBOOLEANカラム。
NULLは「造反判定未実施/対象外」を意味する。
"""

from alembic import op


revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: Add is_defection to proposal_judges."""
    op.execute("""
        ALTER TABLE proposal_judges
        ADD COLUMN IF NOT EXISTS is_defection BOOLEAN DEFAULT NULL;
    """)


def downgrade() -> None:
    """Rollback migration: Remove is_defection from proposal_judges."""
    op.execute("""
        ALTER TABLE proposal_judges DROP COLUMN IF EXISTS is_defection;
    """)
