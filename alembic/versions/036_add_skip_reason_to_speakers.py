"""speakersテーブルにskip_reasonカラムを追加.

Revision ID: 036
Revises: 035
Create Date: 2026-03-01

非政治家分類（SkipReason）の結果をDB永続化するためのカラム。
NULLは「未分類 or 政治家」を意味する。
値は SkipReason Enum の value（role_only, reference_person, government_official,
other_non_politician, homonym）。
"""

from alembic import op


revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: Add skip_reason to speakers and backfill existing data."""
    # カラム追加
    op.execute("""
        ALTER TABLE speakers
        ADD COLUMN IF NOT EXISTS skip_reason VARCHAR DEFAULT NULL;
    """)

    # 既存データのバックフィル: is_politician=FALSE のspeakerに名前パターンから skip_reason を設定
    # ROLE_ONLY: 議会役職名のみ
    op.execute("""
        UPDATE speakers SET skip_reason = 'role_only'
        WHERE is_politician = FALSE AND skip_reason IS NULL
          AND name IN ('委員長', '副委員長', '議長', '副議長', '仮議長');
    """)

    # REFERENCE_PERSON: 参考人・証人等（完全一致 + プレフィックスマッチ）
    op.execute("""
        UPDATE speakers SET skip_reason = 'reference_person'
        WHERE is_politician = FALSE AND skip_reason IS NULL
          AND (name IN ('参考人', '証人', '公述人')
               OR name LIKE '参考人（%'
               OR name LIKE '証人（%'
               OR name LIKE '公述人（%');
    """)

    # GOVERNMENT_OFFICIAL: 政府側出席者
    op.execute("""
        UPDATE speakers SET skip_reason = 'government_official'
        WHERE is_politician = FALSE AND skip_reason IS NULL
          AND (name IN ('説明員', '政府委員', '政府参考人')
               OR name LIKE '説明員（%'
               OR name LIKE '政府委員（%'
               OR name LIKE '政府参考人（%');
    """)

    # OTHER_NON_POLITICIAN: 事務局スタッフ・メタ情報等
    op.execute("""
        UPDATE speakers SET skip_reason = 'other_non_politician'
        WHERE is_politician = FALSE AND skip_reason IS NULL
          AND (name IN ('事務局長', '事務局次長', '事務総長', '法制局長',
                        '書記官長', '書記', '速記者', '幹事', '会議録情報')
               OR name LIKE '事務総長（%'
               OR name LIKE '事務局長（%'
               OR name LIKE '事務局次長（%'
               OR name LIKE '法制局長（%'
               OR name LIKE '書記官長（%');
    """)


def downgrade() -> None:
    """Rollback migration: Remove skip_reason from speakers."""
    op.execute("""
        ALTER TABLE speakers DROP COLUMN IF EXISTS skip_reason;
    """)
