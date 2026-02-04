"""conferencesテーブルに選挙サイクル情報カラムを追加.

Revision ID: 016
Revises: 015
Create Date: 2026-02-04

統一地方選挙ベースで期番号を自動計算できるようにするため、
選挙サイクル情報（election_cycle_years, base_election_year, term_number_at_base）を追加する。
"""

from alembic import op


revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: add election info columns to conferences."""
    op.execute("""
        -- 1. election_cycle_yearsカラムを追加（NULL許容）
        ALTER TABLE conferences
        ADD COLUMN IF NOT EXISTS election_cycle_years INTEGER;

        -- 2. base_election_yearカラムを追加（NULL許容）
        ALTER TABLE conferences
        ADD COLUMN IF NOT EXISTS base_election_year INTEGER;

        -- 3. term_number_at_baseカラムを追加（NULL許容）
        ALTER TABLE conferences
        ADD COLUMN IF NOT EXISTS term_number_at_base INTEGER;

        -- 4. カラムコメントを追加
        COMMENT ON COLUMN conferences.election_cycle_years
            IS '選挙サイクル（年）。統一地方選挙の場合は4';
        COMMENT ON COLUMN conferences.base_election_year
            IS '基準となる選挙年（例: 2023）';
        COMMENT ON COLUMN conferences.term_number_at_base
            IS '基準年の期番号（例: 21は「第21期」を意味する）';
    """)


def downgrade() -> None:
    """Rollback migration: remove election info columns from conferences."""
    op.execute("""
        -- 選挙サイクル情報カラムを削除
        ALTER TABLE conferences
        DROP COLUMN IF EXISTS election_cycle_years;

        ALTER TABLE conferences
        DROP COLUMN IF EXISTS base_election_year;

        ALTER TABLE conferences
        DROP COLUMN IF EXISTS term_number_at_base;
    """)
