"""parliamentary_groupsテーブルにpolitical_party_idカラムを追加.

Revision ID: 023
Revises: 022
Create Date: 2026-02-12

議員団と政党の関連を追跡するため、political_party_idカラムを追加する。
- political_party_id: FK to political_parties(id) ON DELETE SET NULL
"""

from alembic import op


revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: Add political_party_id to parliamentary_groups."""
    op.execute("""
        ALTER TABLE parliamentary_groups
        ADD COLUMN IF NOT EXISTS political_party_id INTEGER
        REFERENCES political_parties(id) ON DELETE SET NULL;

        CREATE INDEX IF NOT EXISTS idx_parliamentary_groups_political_party_id
        ON parliamentary_groups(political_party_id);
    """)


def downgrade() -> None:
    """Rollback migration: Remove political_party_id from parliamentary_groups."""
    op.execute("""
        DROP INDEX IF EXISTS idx_parliamentary_groups_political_party_id;

        ALTER TABLE parliamentary_groups
        DROP COLUMN IF EXISTS political_party_id;
    """)
