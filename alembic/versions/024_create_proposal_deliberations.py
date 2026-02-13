"""proposal_deliberationsテーブルを新規作成.

Revision ID: 024
Revises: 023
Create Date: 2026-02-13

議案と会議の多対多関係を表現するジャンクションテーブル。
1つの議案が複数の会議で審議されるケースに対応する。
- proposal_id: FK to proposals(id) ON DELETE CASCADE
- conference_id: FK to conferences(id) ON DELETE RESTRICT
- meeting_id: FK to meetings(id) ON DELETE SET NULL（任意）
- stage: 審議段階（任意、例: "付託", "採決"）
"""

from alembic import op


revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: Create proposal_deliberations table."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS proposal_deliberations (
            id SERIAL PRIMARY KEY,
            proposal_id INTEGER NOT NULL
                REFERENCES proposals(id) ON DELETE CASCADE,
            conference_id INTEGER NOT NULL
                REFERENCES conferences(id) ON DELETE RESTRICT,
            meeting_id INTEGER
                REFERENCES meetings(id) ON DELETE SET NULL,
            stage VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_proposal_deliberations_proposal_id
            ON proposal_deliberations(proposal_id);
        CREATE INDEX IF NOT EXISTS idx_proposal_deliberations_conference_id
            ON proposal_deliberations(conference_id);
        CREATE INDEX IF NOT EXISTS idx_proposal_deliberations_meeting_id
            ON proposal_deliberations(meeting_id);

        CREATE UNIQUE INDEX IF NOT EXISTS uq_proposal_deliberations_composite
            ON proposal_deliberations(
                proposal_id,
                conference_id,
                COALESCE(meeting_id, -1),
                COALESCE(stage, '')
            );
    """)


def downgrade() -> None:
    """Rollback migration: Drop proposal_deliberations table."""
    op.execute("""
        DROP INDEX IF EXISTS uq_proposal_deliberations_composite;
        DROP TABLE IF EXISTS proposal_deliberations;
    """)
