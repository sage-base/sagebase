"""extracted_conference_membersからmatching関連カラムを削除.

Revision ID: 011
Revises: 010
Create Date: 2025-02-03

Bronze LayerからGold Layerへの責務分離のため、
ExtractedConferenceMemberからマッチング関連のカラムを削除します。
政治家との紐付けはConferenceMember（Gold Layer）のみで管理します。
"""

from alembic import op


revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """マッチング関連カラムとインデックスを削除."""
    # インデックスを先に削除
    op.execute("""
        DROP INDEX IF EXISTS idx_extracted_conference_members_status;
    """)
    op.execute("""
        DROP INDEX IF EXISTS idx_extracted_conference_members_politician;
    """)

    # 外部キー制約を削除（存在する場合）
    op.execute("""
        ALTER TABLE extracted_conference_members
        DROP CONSTRAINT IF EXISTS extracted_conference_members_matched_politician_id_fkey;
    """)

    # カラムを削除
    op.execute("""
        ALTER TABLE extracted_conference_members
        DROP COLUMN IF EXISTS matching_status;
    """)
    op.execute("""
        ALTER TABLE extracted_conference_members
        DROP COLUMN IF EXISTS matched_politician_id;
    """)
    op.execute("""
        ALTER TABLE extracted_conference_members
        DROP COLUMN IF EXISTS matching_confidence;
    """)
    op.execute("""
        ALTER TABLE extracted_conference_members
        DROP COLUMN IF EXISTS matched_at;
    """)


def downgrade() -> None:
    """マッチング関連カラムとインデックスを復元."""
    # カラムを追加
    op.execute("""
        ALTER TABLE extracted_conference_members
        ADD COLUMN IF NOT EXISTS matching_status VARCHAR(50) DEFAULT 'pending';
    """)
    op.execute("""
        ALTER TABLE extracted_conference_members
        ADD COLUMN IF NOT EXISTS matched_politician_id INTEGER REFERENCES politicians(id);
    """)
    op.execute("""
        ALTER TABLE extracted_conference_members
        ADD COLUMN IF NOT EXISTS matching_confidence DECIMAL(3,2);
    """)
    op.execute("""
        ALTER TABLE extracted_conference_members
        ADD COLUMN IF NOT EXISTS matched_at TIMESTAMP;
    """)

    # インデックスを作成
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_extracted_conference_members_status
        ON extracted_conference_members(matching_status);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_extracted_conference_members_politician
        ON extracted_conference_members(matched_politician_id);
    """)
