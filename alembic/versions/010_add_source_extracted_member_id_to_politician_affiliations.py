"""politician_affiliationsテーブルにsource_extracted_member_idカラムを追加.

Revision ID: 010
Revises: 009
Create Date: 2026-02-02

抽出メンバーから所属情報が作成された場合のトレーサビリティを確保するため、
extracted_conference_membersへのFK参照を追加する。
"""

from alembic import op


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: source_extracted_member_idカラムを追加."""
    op.execute("""
        ALTER TABLE politician_affiliations
        ADD COLUMN IF NOT EXISTS source_extracted_member_id INTEGER
        REFERENCES extracted_conference_members(id) ON DELETE SET NULL;

        CREATE INDEX IF NOT EXISTS idx_politician_affiliations_source_extracted_member_id
        ON politician_affiliations(source_extracted_member_id);
    """)


def downgrade() -> None:
    """Rollback migration: source_extracted_member_idカラムを削除."""
    op.execute("""
        DROP INDEX IF EXISTS idx_politician_affiliations_source_extracted_member_id;

        ALTER TABLE politician_affiliations
        DROP COLUMN IF EXISTS source_extracted_member_id;
    """)
