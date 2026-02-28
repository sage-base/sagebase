"""politician_affiliations テーブルを conference_members にリネーム.

Revision ID: 035
Revises: 034
Create Date: 2026-02-28

ドメインエンティティ ConferenceMember とテーブル名の不一致を解消するため、
テーブル名・インデックス名・外部キー制約名・トリガー名をすべてリネームする。

関連: Issue #1284
"""

from alembic import op


revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """politician_affiliations → conference_members にリネーム."""
    # 1. テーブルリネーム
    op.execute("ALTER TABLE politician_affiliations RENAME TO conference_members;")

    # 2. インデックスリネーム
    op.execute("""
        ALTER INDEX idx_politician_affiliations_politician
            RENAME TO idx_conference_members_politician;
        ALTER INDEX idx_politician_affiliations_conference
            RENAME TO idx_conference_members_conference;
        ALTER INDEX idx_politician_affiliations_role
            RENAME TO idx_conference_members_role;
        ALTER INDEX idx_politician_affiliations_manually_verified
            RENAME TO idx_conference_members_manually_verified;
    """)

    # 3. 主キー・外部キー制約リネーム
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'politician_affiliations_pkey'
            ) THEN
                ALTER TABLE conference_members
                    RENAME CONSTRAINT politician_affiliations_pkey
                    TO conference_members_pkey;
            END IF;

            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'politician_affiliations_politician_id_fkey'
            ) THEN
                ALTER TABLE conference_members
                    RENAME CONSTRAINT politician_affiliations_politician_id_fkey
                    TO conference_members_politician_id_fkey;
            END IF;

            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'politician_affiliations_conference_id_fkey'
            ) THEN
                ALTER TABLE conference_members
                    RENAME CONSTRAINT politician_affiliations_conference_id_fkey
                    TO conference_members_conference_id_fkey;
            END IF;

            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'politician_affiliations_latest_extraction_log_id_fkey'
            ) THEN
                ALTER TABLE conference_members
                    RENAME CONSTRAINT politician_affiliations_latest_extraction_log_id_fkey
                    TO conference_members_latest_extraction_log_id_fkey;
            END IF;
        END $$;
    """)

    # 4. トリガーリネーム（DROP + CREATE）
    op.execute("""
        DROP TRIGGER IF EXISTS update_politician_affiliations_updated_at
            ON conference_members;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'update_conference_members_updated_at'
            ) THEN
                CREATE TRIGGER update_conference_members_updated_at
                    BEFORE UPDATE ON conference_members
                    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            END IF;
        END $$;
    """)

    # 5. テーブルコメント更新
    op.execute(
        "COMMENT ON TABLE conference_members IS '会議体メンバー（議員の議会所属情報）';"
    )


def downgrade() -> None:
    """conference_members → politician_affiliations に戻す."""
    # 1. テーブルリネーム
    op.execute("ALTER TABLE conference_members RENAME TO politician_affiliations;")

    # 2. インデックスリネーム
    op.execute("""
        ALTER INDEX idx_conference_members_politician
            RENAME TO idx_politician_affiliations_politician;
        ALTER INDEX idx_conference_members_conference
            RENAME TO idx_politician_affiliations_conference;
        ALTER INDEX idx_conference_members_role
            RENAME TO idx_politician_affiliations_role;
        ALTER INDEX idx_conference_members_manually_verified
            RENAME TO idx_politician_affiliations_manually_verified;
    """)

    # 3. 主キー・外部キー制約リネーム
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'conference_members_pkey'
            ) THEN
                ALTER TABLE politician_affiliations
                    RENAME CONSTRAINT conference_members_pkey
                    TO politician_affiliations_pkey;
            END IF;

            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'conference_members_politician_id_fkey'
            ) THEN
                ALTER TABLE politician_affiliations
                    RENAME CONSTRAINT conference_members_politician_id_fkey
                    TO politician_affiliations_politician_id_fkey;
            END IF;

            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'conference_members_conference_id_fkey'
            ) THEN
                ALTER TABLE politician_affiliations
                    RENAME CONSTRAINT conference_members_conference_id_fkey
                    TO politician_affiliations_conference_id_fkey;
            END IF;

            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'conference_members_latest_extraction_log_id_fkey'
            ) THEN
                ALTER TABLE politician_affiliations
                    RENAME CONSTRAINT conference_members_latest_extraction_log_id_fkey
                    TO politician_affiliations_latest_extraction_log_id_fkey;
            END IF;
        END $$;
    """)

    # 4. トリガーリネーム（DROP + CREATE）
    op.execute("""
        DROP TRIGGER IF EXISTS update_conference_members_updated_at
            ON politician_affiliations;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'update_politician_affiliations_updated_at'
            ) THEN
                CREATE TRIGGER update_politician_affiliations_updated_at
                    BEFORE UPDATE ON politician_affiliations
                    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            END IF;
        END $$;
    """)

    # 5. テーブルコメント復元
    op.execute("COMMENT ON TABLE politician_affiliations IS '議員の議会所属情報';")
