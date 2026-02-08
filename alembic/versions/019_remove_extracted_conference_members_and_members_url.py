"""extracted_conference_membersテーブルとmembers_introduction_urlカラムを除却.

Revision ID: 019
Revises: 018
Create Date: 2026-02-08

議員紹介URLスクレイピング機能の除却に伴い、以下を削除する:
- politician_affiliations.source_extracted_member_id カラムとFK/インデックス
- extracted_conference_members テーブル
- conferences.members_introduction_url カラム

Issue: #1084
"""

from alembic import op


revision = "019"
down_revision = "018"


def upgrade() -> None:
    """Apply migration: スクレイピング関連テーブル・カラムを削除."""
    # 1. politician_affiliations から source_extracted_member_id を削除
    op.execute("""
        DROP INDEX IF EXISTS idx_politician_affiliations_source_extracted_member_id;
    """)
    op.execute("""
        ALTER TABLE politician_affiliations
        DROP CONSTRAINT IF EXISTS politician_affiliations_source_extracted_member_id_fkey;
    """)
    op.execute("""
        ALTER TABLE politician_affiliations
        DROP COLUMN IF EXISTS source_extracted_member_id;
    """)

    # 2. extracted_conference_members テーブルを削除
    op.execute("""
        DROP TABLE IF EXISTS extracted_conference_members CASCADE;
    """)

    # 3. conferences から members_introduction_url を削除
    op.execute("""
        ALTER TABLE conferences
        DROP COLUMN IF EXISTS members_introduction_url;
    """)


def downgrade() -> None:
    """Rollback migration: スクレイピング関連テーブル・カラムを復元."""
    # 3. conferences.members_introduction_url を復元
    op.execute("""
        ALTER TABLE conferences
        ADD COLUMN IF NOT EXISTS members_introduction_url VARCHAR(255);
    """)

    # 2. extracted_conference_members テーブルを復元
    op.execute("""
        CREATE TABLE IF NOT EXISTS extracted_conference_members (
            id SERIAL PRIMARY KEY,
            conference_id INTEGER NOT NULL REFERENCES conferences(id),
            extracted_name VARCHAR(255) NOT NULL,
            source_url TEXT,
            extracted_role VARCHAR(255),
            extracted_party_name VARCHAR(255),
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            additional_data JSONB,
            latest_extraction_log_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_extracted_conference_members_conference
        ON extracted_conference_members(conference_id);
    """)

    # 1. politician_affiliations.source_extracted_member_id を復元
    op.execute("""
        ALTER TABLE politician_affiliations
        ADD COLUMN IF NOT EXISTS source_extracted_member_id INTEGER
        REFERENCES extracted_conference_members(id) ON DELETE SET NULL;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_politician_affiliations_source_extracted_member_id
        ON politician_affiliations(source_extracted_member_id);
    """)
