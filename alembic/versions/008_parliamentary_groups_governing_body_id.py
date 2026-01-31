"""parliamentary_groupsのconference_idをgoverning_body_idに移行.

Revision ID: 008
Revises: 007
Create Date: 2026-01-31

会派（議員団）は開催主体レベルで存在するため、
conference_id（会議体）ではなくgoverning_body_id（開催主体）に紐付けるべき。
既存データはconferences.governing_body_idを経由して自動変換する。
"""

from alembic import op


revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: conference_id → governing_body_id."""
    op.execute("""
        -- 1. governing_body_idカラムを追加
        ALTER TABLE parliamentary_groups
        ADD COLUMN IF NOT EXISTS governing_body_id INTEGER;

        -- 2. 既存データをconferencesテーブル経由で変換
        UPDATE parliamentary_groups
        SET governing_body_id = c.governing_body_id
        FROM conferences c
        WHERE parliamentary_groups.conference_id = c.id;

        -- 3. NOT NULL制約を追加
        ALTER TABLE parliamentary_groups
        ALTER COLUMN governing_body_id SET NOT NULL;

        -- 4. 外部キー制約を追加
        ALTER TABLE parliamentary_groups
        ADD CONSTRAINT fk_parliamentary_groups_governing_body
        FOREIGN KEY (governing_body_id) REFERENCES governing_bodies(id);

        -- 5. 旧ユニーク制約を削除
        ALTER TABLE parliamentary_groups
        DROP CONSTRAINT IF EXISTS parliamentary_groups_name_conference_id_key;

        -- 6. 新しいユニーク制約を追加
        ALTER TABLE parliamentary_groups
        ADD CONSTRAINT parliamentary_groups_name_governing_body_id_key
        UNIQUE (name, governing_body_id);

        -- 7. conference_idカラムを削除
        ALTER TABLE parliamentary_groups
        DROP COLUMN IF EXISTS conference_id;
    """)


def downgrade() -> None:
    """Rollback migration: governing_body_id → conference_id."""
    op.execute("""
        -- 1. conference_idカラムを追加
        ALTER TABLE parliamentary_groups
        ADD COLUMN IF NOT EXISTS conference_id INTEGER;

        -- 2. governing_body_idからconference_idを逆変換
        -- 同一governing_bodyに複数conferenceがある場合、最初のものを使用
        UPDATE parliamentary_groups pg
        SET conference_id = (
            SELECT c.id FROM conferences c
            WHERE c.governing_body_id = pg.governing_body_id
            ORDER BY c.id
            LIMIT 1
        );

        -- 3. NOT NULL制約を追加
        ALTER TABLE parliamentary_groups
        ALTER COLUMN conference_id SET NOT NULL;

        -- 4. 新ユニーク制約を削除
        ALTER TABLE parliamentary_groups
        DROP CONSTRAINT IF EXISTS parliamentary_groups_name_governing_body_id_key;

        -- 5. 旧ユニーク制約を復元
        ALTER TABLE parliamentary_groups
        ADD CONSTRAINT parliamentary_groups_name_conference_id_key
        UNIQUE (name, conference_id);

        -- 6. 外部キー制約を削除
        ALTER TABLE parliamentary_groups
        DROP CONSTRAINT IF EXISTS fk_parliamentary_groups_governing_body;

        -- 7. governing_body_idカラムを削除
        ALTER TABLE parliamentary_groups
        DROP COLUMN IF EXISTS governing_body_id;
    """)
