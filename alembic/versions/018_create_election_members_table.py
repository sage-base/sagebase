"""election_membersテーブルを作成.

Revision ID: 018
Revises: 017
Create Date: 2026-02-06

選挙結果メンバーを管理するテーブルを作成する。
どの政治家がどの選挙で当選/落選したかを記録する。
"""

from alembic import op


revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: create election_members table."""
    op.execute("""
        -- 1. election_membersテーブルを作成
        CREATE TABLE election_members (
            id SERIAL PRIMARY KEY,
            election_id INTEGER NOT NULL REFERENCES elections(id),
            politician_id INTEGER NOT NULL REFERENCES politicians(id),
            result VARCHAR(50) NOT NULL,
            votes INTEGER,
            rank INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 2. 一意制約: 同じ選挙で同じ政治家は存在しない
        CREATE UNIQUE INDEX idx_election_members_election_politician
        ON election_members(election_id, politician_id);

        -- 3. インデックス
        CREATE INDEX idx_election_members_election_id ON election_members(election_id);
        CREATE INDEX idx_election_members_politician_id ON election_members(politician_id);

        -- 4. テーブル・カラムコメントを追加
        COMMENT ON TABLE election_members IS '選挙結果メンバーテーブル: 選挙ごとの政治家の当落情報を管理';
        COMMENT ON COLUMN election_members.election_id IS '選挙ID';
        COMMENT ON COLUMN election_members.politician_id IS '政治家ID';
        COMMENT ON COLUMN election_members.result IS '選挙結果（当選, 落選, 次点, 繰上当選, 無投票当選など）';
        COMMENT ON COLUMN election_members.votes IS '得票数';
        COMMENT ON COLUMN election_members.rank IS '順位';
    """)


def downgrade() -> None:
    """Rollback migration: drop election_members table."""
    op.execute("""
        DROP TABLE IF EXISTS election_members CASCADE;
    """)
