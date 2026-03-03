"""politiciansテーブルの名前から全角スペースを除去.

Revision ID: 037
Revises: 036
Create Date: 2026-03-03

選挙データ経由で全角スペース（U+3000）が混入した政治家名を修正する。
例: '伊藤　孝江' → '伊藤孝江'
"""

from alembic import op


revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: 全角スペースを除去."""
    op.execute("""
        UPDATE politicians
        SET name = REPLACE(name, '　', '')
        WHERE name LIKE '%　%';
    """)


def downgrade() -> None:
    """Rollback migration: データ変換のため厳密な復元は不可."""
    pass
