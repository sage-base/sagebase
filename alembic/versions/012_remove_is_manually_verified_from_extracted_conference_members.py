"""extracted_conference_membersからis_manually_verifiedカラムを削除.

Revision ID: 012
Revises: 011
Create Date: 2025-02-04

Bronze Layer（抽出ログ層）のExtractedConferenceMemberから検証状態を削除します。
検証状態はGold Layer（ConferenceMember）のみで管理します。
"""

from alembic import op


revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """is_manually_verifiedカラムとインデックスを削除."""
    # インデックスを先に削除
    op.execute("""
        DROP INDEX IF EXISTS idx_extracted_conference_members_manually_verified;
    """)

    # カラムを削除
    op.execute("""
        ALTER TABLE extracted_conference_members
        DROP COLUMN IF EXISTS is_manually_verified;
    """)


def downgrade() -> None:
    """is_manually_verifiedカラムとインデックスを復元."""
    # カラムを追加
    op.execute("""
        ALTER TABLE extracted_conference_members
        ADD COLUMN IF NOT EXISTS is_manually_verified BOOLEAN DEFAULT FALSE;
    """)

    # インデックスを作成
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_extracted_conference_members_manually_verified
        ON extracted_conference_members(is_manually_verified);
    """)
