"""conferencesテーブルにelection_idカラムを追加.

Revision ID: 017
Revises: 016
Create Date: 2026-02-05

会議体を選挙（期）に紐付けられるようにする。
既存のtermフィールドは表示用として残す。
"""

from alembic import op


revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: add election_id column to conferences."""
    op.execute("""
        -- 1. election_idカラムを追加
        ALTER TABLE conferences
        ADD COLUMN election_id INTEGER REFERENCES elections(id);

        -- 2. インデックスを追加
        CREATE INDEX idx_conferences_election_id ON conferences(election_id);

        -- 3. カラムコメントを追加
        COMMENT ON COLUMN conferences.election_id IS '選挙ID（どの期に属するか）';
    """)


def downgrade() -> None:
    """Rollback migration: remove election_id column from conferences."""
    op.execute("""
        -- 1. インデックスを削除
        DROP INDEX IF EXISTS idx_conferences_election_id;

        -- 2. election_idカラムを削除
        ALTER TABLE conferences
        DROP COLUMN IF EXISTS election_id;
    """)
