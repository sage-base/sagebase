"""proposalsテーブルに議案インポート用の8カラムを追加.

Revision ID: 020
Revises: 019
Create Date: 2026-02-09

smartnews-smriデータインポートに必要な8フィールドを追加:
- proposal_category: 大分類
- proposal_type: 小分類
- governing_body_id: 議会ID (FK)
- session_number: 回次
- proposal_number: 議案番号
- external_id: 外部データソースID/URL
- deliberation_status: 審議状況
- deliberation_result: 最終結果

Issue: #1101
"""

from alembic import op


revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: 議案インポート用カラム・インデックスを追加."""
    op.execute("""
        ALTER TABLE proposals
        ADD COLUMN IF NOT EXISTS proposal_category VARCHAR(255);
    """)
    op.execute("""
        ALTER TABLE proposals
        ADD COLUMN IF NOT EXISTS proposal_type VARCHAR(255);
    """)
    op.execute("""
        ALTER TABLE proposals
        ADD COLUMN IF NOT EXISTS governing_body_id INTEGER;
    """)
    op.execute("""
        ALTER TABLE proposals
        ADD COLUMN IF NOT EXISTS session_number INTEGER;
    """)
    op.execute("""
        ALTER TABLE proposals
        ADD COLUMN IF NOT EXISTS proposal_number INTEGER;
    """)
    op.execute("""
        ALTER TABLE proposals
        ADD COLUMN IF NOT EXISTS external_id VARCHAR(1024);
    """)
    op.execute("""
        ALTER TABLE proposals
        ADD COLUMN IF NOT EXISTS deliberation_status VARCHAR(255);
    """)
    op.execute("""
        ALTER TABLE proposals
        ADD COLUMN IF NOT EXISTS deliberation_result VARCHAR(255);
    """)

    op.execute("""
        ALTER TABLE proposals
        ADD CONSTRAINT proposals_governing_body_id_fkey
        FOREIGN KEY (governing_body_id) REFERENCES governing_bodies(id)
        ON DELETE RESTRICT;
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_proposals_governing_body_id
        ON proposals(governing_body_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_proposals_deliberation_result
        ON proposals(deliberation_result);
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_proposals_unique_identifier
        ON proposals(governing_body_id, session_number, proposal_number, proposal_type)
        WHERE governing_body_id IS NOT NULL
            AND session_number IS NOT NULL
            AND proposal_number IS NOT NULL
            AND proposal_type IS NOT NULL;
    """)


def downgrade() -> None:
    """Rollback migration: 議案インポート用カラム・インデックスを削除."""
    op.execute("""
        DROP INDEX IF EXISTS idx_proposals_unique_identifier;
    """)
    op.execute("""
        DROP INDEX IF EXISTS idx_proposals_deliberation_result;
    """)
    op.execute("""
        DROP INDEX IF EXISTS idx_proposals_governing_body_id;
    """)

    op.execute("""
        ALTER TABLE proposals
        DROP CONSTRAINT IF EXISTS proposals_governing_body_id_fkey;
    """)

    op.execute("""
        ALTER TABLE proposals
        DROP COLUMN IF EXISTS deliberation_result;
    """)
    op.execute("""
        ALTER TABLE proposals
        DROP COLUMN IF EXISTS deliberation_status;
    """)
    op.execute("""
        ALTER TABLE proposals
        DROP COLUMN IF EXISTS external_id;
    """)
    op.execute("""
        ALTER TABLE proposals
        DROP COLUMN IF EXISTS proposal_number;
    """)
    op.execute("""
        ALTER TABLE proposals
        DROP COLUMN IF EXISTS session_number;
    """)
    op.execute("""
        ALTER TABLE proposals
        DROP COLUMN IF EXISTS governing_body_id;
    """)
    op.execute("""
        ALTER TABLE proposals
        DROP COLUMN IF EXISTS proposal_type;
    """)
    op.execute("""
        ALTER TABLE proposals
        DROP COLUMN IF EXISTS proposal_category;
    """)
