"""electionsテーブルを作成.

Revision ID: 016
Revises: 015
Create Date: 2026-02-05

選挙をファーストクラスのエンティティとして扱い、
会議体がどの選挙（＝何期）に属するかを管理できるようにする。
"""

from alembic import op


revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: create elections table."""
    op.execute("""
        -- 1. electionsテーブルを作成
        CREATE TABLE elections (
            id SERIAL PRIMARY KEY,
            governing_body_id INTEGER NOT NULL REFERENCES governing_bodies(id),
            term_number INTEGER NOT NULL,
            election_date DATE NOT NULL,
            election_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 2. 一意制約: 同じ開催主体で同じ期番号は存在しない
        CREATE UNIQUE INDEX idx_elections_governing_body_term
        ON elections(governing_body_id, term_number);

        -- 3. インデックス
        CREATE INDEX idx_elections_governing_body_id ON elections(governing_body_id);
        CREATE INDEX idx_elections_election_date ON elections(election_date);

        -- 4. カラムコメントを追加
        COMMENT ON TABLE elections IS '選挙テーブル: 開催主体ごとの選挙情報を管理';
        COMMENT ON COLUMN elections.governing_body_id IS '開催主体ID';
        COMMENT ON COLUMN elections.term_number IS '期番号（例: 21）';
        COMMENT ON COLUMN elections.election_date IS '選挙実施日';
        COMMENT ON COLUMN elections.election_type IS '選挙種別（統一地方選挙, 通常選挙, 補欠選挙など）';
    """)


def downgrade() -> None:
    """Rollback migration: drop elections table."""
    op.execute("""
        DROP TABLE IF EXISTS elections CASCADE;
    """)
