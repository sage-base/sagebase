"""proposal_judgesテーブルからpolitician_party_idカラムを削除.

Revision ID: 009
Revises: 008
Create Date: 2026-01-31

politician_party_idは常にNULLで一度も使用されていない。
議案賛否はpolitician_id（個人）またはproposal_parliamentary_group_judges（議員団）で管理されるため不要。
"""

from alembic import op


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: politician_party_idカラムを削除."""
    op.execute("""
        ALTER TABLE proposal_judges
        DROP COLUMN IF EXISTS politician_party_id;
    """)


def downgrade() -> None:
    """Rollback migration: politician_party_idカラムを復元."""
    op.execute("""
        ALTER TABLE proposal_judges
        ADD COLUMN IF NOT EXISTS politician_party_id INTEGER
        REFERENCES political_parties(id);
    """)
