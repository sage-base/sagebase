"""government_officialsおよびgovernment_official_positionsテーブルを追加.

Revision ID: 038
Revises: 037
Create Date: 2026-03-04

政府関係者（政府参考人・官僚）をモデル化するためのテーブルを新規作成し、
speakersテーブルにgovernment_official_idカラムを追加する。
"""

from alembic import op


revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: 政府関係者テーブル追加."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS government_officials (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(200) NOT NULL,
            name_yomi   VARCHAR(200),
            created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_government_officials_name
            ON government_officials(name);

        COMMENT ON TABLE government_officials IS '政府関係者マスタ';
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS government_official_positions (
            id                      SERIAL PRIMARY KEY,
            government_official_id  INTEGER NOT NULL
                REFERENCES government_officials(id) ON DELETE CASCADE,
            organization            VARCHAR(200) NOT NULL,
            position                VARCHAR(200) NOT NULL,
            start_date              DATE,
            end_date                DATE,
            source_note             VARCHAR(500),
            created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_gop_end_date_after_start
                CHECK (end_date IS NULL OR end_date >= start_date)
        );

        CREATE INDEX IF NOT EXISTS idx_gop_official_id
            ON government_official_positions(government_official_id);

        CREATE INDEX IF NOT EXISTS idx_gop_organization
            ON government_official_positions(organization);

        COMMENT ON TABLE government_official_positions IS '政府関係者の役職履歴';
    """)

    op.execute("""
        ALTER TABLE speakers
            ADD COLUMN IF NOT EXISTS government_official_id INTEGER
                REFERENCES government_officials(id) ON DELETE SET NULL;

        CREATE INDEX IF NOT EXISTS idx_speakers_gov_official_id
            ON speakers(government_official_id)
            WHERE government_official_id IS NOT NULL;
    """)


def downgrade() -> None:
    """Rollback migration: 政府関係者テーブル削除."""
    op.execute("""
        DROP INDEX IF EXISTS idx_speakers_gov_official_id;
        ALTER TABLE speakers DROP COLUMN IF EXISTS government_official_id;
    """)

    op.execute("""
        DROP TABLE IF EXISTS government_official_positions;
    """)

    op.execute("""
        DROP TABLE IF EXISTS government_officials;
    """)
