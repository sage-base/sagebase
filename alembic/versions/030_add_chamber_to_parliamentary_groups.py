"""parliamentary_groupsテーブルにchamberカラムを追加.

Revision ID: 030
Revises: 029
Create Date: 2026-02-25

衆議院と参議院で同名会派（公明党、日本共産党等）を登録できるよう、
chamberカラムを追加しUNIQUE制約を(name, governing_body_id, chamber)に変更する。

関連: ADR 0008, Issue #1232
"""

from alembic import op


revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: chamberカラム追加とUNIQUE制約変更."""
    # 1. chamberカラムを追加（デフォルト空文字）
    op.execute("""
        ALTER TABLE parliamentary_groups
        ADD COLUMN IF NOT EXISTS chamber VARCHAR(10) NOT NULL DEFAULT '';
    """)

    # 2. 既存データ更新: descriptionに「参議院」を含むものは参議院
    op.execute("""
        UPDATE parliamentary_groups
        SET chamber = '参議院'
        WHERE governing_body_id = (
            SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'
        )
        AND description LIKE '%参議院%';
    """)

    # 3. 既存データ更新: 国会に属し、まだchamber未設定のものは衆議院
    op.execute("""
        UPDATE parliamentary_groups
        SET chamber = '衆議院'
        WHERE governing_body_id = (
            SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'
        )
        AND chamber = '';
    """)

    # 4. 旧UNIQUE制約を削除
    op.execute("""
        ALTER TABLE parliamentary_groups
        DROP CONSTRAINT IF EXISTS parliamentary_groups_name_governing_body_id_key;
    """)

    # 5. 新UNIQUE制約を追加
    op.execute("""
        ALTER TABLE parliamentary_groups
        ADD CONSTRAINT parliamentary_groups_name_governing_body_id_chamber_key
        UNIQUE (name, governing_body_id, chamber);
    """)

    # 6. chamberインデックスを追加
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_parliamentary_groups_chamber
        ON parliamentary_groups(chamber);
    """)


def downgrade() -> None:
    """Rollback migration: chamberカラム削除とUNIQUE制約復元."""
    # 1. chamberインデックスを削除
    op.execute("""
        DROP INDEX IF EXISTS idx_parliamentary_groups_chamber;
    """)

    # 2. 新UNIQUE制約を削除
    op.execute("""
        ALTER TABLE parliamentary_groups
        DROP CONSTRAINT IF EXISTS parliamentary_groups_name_governing_body_id_chamber_key;
    """)

    # 3. 衆参同名会派の衝突を解消するため、参議院固有のレコードを削除
    #    （衆議院側と同名で同一governing_body_idのレコードが衝突するため）
    op.execute("""
        DELETE FROM parliamentary_groups
        WHERE chamber = '参議院'
        AND (name, governing_body_id) IN (
            SELECT name, governing_body_id
            FROM parliamentary_groups
            WHERE chamber = '衆議院'
        );
    """)

    # 4. chamberカラムを削除
    op.execute("""
        ALTER TABLE parliamentary_groups
        DROP COLUMN IF EXISTS chamber;
    """)

    # 5. 旧UNIQUE制約を復元
    op.execute("""
        ALTER TABLE parliamentary_groups
        ADD CONSTRAINT parliamentary_groups_name_governing_body_id_key
        UNIQUE (name, governing_body_id);
    """)
