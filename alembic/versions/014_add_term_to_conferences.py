"""conferencesテーブルにtermカラムを追加.

Revision ID: 014
Revises: 013
Create Date: 2026-02-04

会議体に「第220回国会」「令和5年度」といった期間情報を持たせるため、
termフィールドを追加する。
UNIQUE制約も(name, governing_body_id)から(name, governing_body_id, term)に変更。
"""

from alembic import op


revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: add term column to conferences."""
    op.execute("""
        -- 1. termカラムを追加（NULL許容）
        ALTER TABLE conferences
        ADD COLUMN IF NOT EXISTS term VARCHAR(100);

        -- 2. 既存のUNIQUE制約を削除
        ALTER TABLE conferences
        DROP CONSTRAINT IF EXISTS conferences_name_governing_body_id_key;

        -- 3. 新しいUNIQUE制約を追加（name, governing_body_id, term）
        -- PostgreSQLではNULLは重複とみなさないため、既存データ（term=NULL）は影響なし
        ALTER TABLE conferences
        ADD CONSTRAINT conferences_name_governing_body_id_term_key
        UNIQUE (name, governing_body_id, term);

        -- 4. termカラムにインデックスを追加（検索性能向上）
        CREATE INDEX IF NOT EXISTS idx_conferences_term ON conferences(term);

        -- 5. カラムコメントを追加
        COMMENT ON COLUMN conferences.term IS '期/会期/年度（例: 第220回, 令和5年度）';
    """)


def downgrade() -> None:
    """Rollback migration: remove term column from conferences."""
    op.execute("""
        -- 1. インデックスを削除
        DROP INDEX IF EXISTS idx_conferences_term;

        -- 2. 新しいUNIQUE制約を削除
        ALTER TABLE conferences
        DROP CONSTRAINT IF EXISTS conferences_name_governing_body_id_term_key;

        -- 3. 元のUNIQUE制約を復元
        -- 注意: termが異なる同名・同開催主体の会議体が存在する場合、この操作は失敗する
        ALTER TABLE conferences
        ADD CONSTRAINT conferences_name_governing_body_id_key
        UNIQUE (name, governing_body_id);

        -- 4. termカラムを削除
        ALTER TABLE conferences
        DROP COLUMN IF EXISTS term;
    """)
