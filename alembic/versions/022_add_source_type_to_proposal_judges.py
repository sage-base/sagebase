"""proposal_judgesテーブルにsource_type, source_group_judge_idカラムを追加.

Revision ID: 022
Revises: 021
Create Date: 2026-02-12

会派賛否データから個人投票データへ展開する際に、
生成元の追跡を可能にするためのカラムを追加する。
- source_type: 生成元種別（GROUP_EXPANSION, MANUAL, EXTRACTED等）
- source_group_judge_id: FK to proposal_parliamentary_group_judges(id)
"""

from alembic import op


revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: Add source_type and source_group_judge_id to proposal_judges."""
    op.execute("""
        ALTER TABLE proposal_judges
        ADD COLUMN IF NOT EXISTS source_type VARCHAR(50);

        ALTER TABLE proposal_judges
        ADD COLUMN IF NOT EXISTS source_group_judge_id INTEGER
        REFERENCES proposal_parliamentary_group_judges(id) ON DELETE SET NULL;

        CREATE INDEX IF NOT EXISTS idx_proposal_judges_source_type
        ON proposal_judges(source_type);

        CREATE INDEX IF NOT EXISTS idx_proposal_judges_source_group_judge_id
        ON proposal_judges(source_group_judge_id);
    """)


def downgrade() -> None:
    """Rollback migration: Remove source_type and source_group_judge_id."""
    op.execute("""
        DROP INDEX IF EXISTS idx_proposal_judges_source_group_judge_id;

        DROP INDEX IF EXISTS idx_proposal_judges_source_type;

        ALTER TABLE proposal_judges
        DROP COLUMN IF EXISTS source_group_judge_id;

        ALTER TABLE proposal_judges
        DROP COLUMN IF EXISTS source_type;
    """)
