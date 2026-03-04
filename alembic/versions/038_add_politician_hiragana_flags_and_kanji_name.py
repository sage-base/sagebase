"""politiciansテーブルにひらがなフラグとkanji_nameカラムを追加.

Revision ID: 038
Revises: 037
Create Date: 2026-03-03

Wikipediaインポーターが選挙公報の届出名（ひらがな表記）をそのまま保存するため、
国会会議録APIのSpeaker名（漢字表記）と完全一致しない問題を解消するための前提変更。

- is_lastname_hiragana: 名前の最初の文字がひらがなならtrue
- is_firstname_hiragana: 名前の最後の文字がひらがならtrue
- kanji_name: 手動入力される漢字表記の正式名
"""

from alembic import op


revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: ひらがなフラグとkanji_nameカラムを追加."""
    # カラム追加
    op.execute("""
        ALTER TABLE politicians
        ADD COLUMN IF NOT EXISTS is_lastname_hiragana BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS is_firstname_hiragana BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS kanji_name TEXT DEFAULT NULL;
    """)

    # kanji_nameにインデックス追加（マッチング完全一致検索用）
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_politicians_kanji_name
        ON politicians(kanji_name)
        WHERE kanji_name IS NOT NULL;
    """)

    # 既存データのひらがなフラグを自動セット
    # 名前の最初の文字が[ぁ-ん]ならis_lastname_hiragana=true
    op.execute("""
        UPDATE politicians
        SET is_lastname_hiragana = TRUE
        WHERE LEFT(name, 1) ~ '[ぁ-ん]';
    """)

    # 名前の最後の文字が[ぁ-ん]ならis_firstname_hiragana=true
    op.execute("""
        UPDATE politicians
        SET is_firstname_hiragana = TRUE
        WHERE RIGHT(name, 1) ~ '[ぁ-ん]';
    """)


def downgrade() -> None:
    """Rollback migration: カラムとインデックスを削除."""
    op.execute("DROP INDEX IF EXISTS idx_politicians_kanji_name;")
    op.execute("""
        ALTER TABLE politicians
        DROP COLUMN IF EXISTS is_lastname_hiragana,
        DROP COLUMN IF EXISTS is_firstname_hiragana,
        DROP COLUMN IF EXISTS kanji_name;
    """)
