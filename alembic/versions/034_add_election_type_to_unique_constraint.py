"""elections テーブルの UNIQUE 制約に election_type を追加.

Revision ID: 034
Revises: 033
Create Date: 2026-02-28

既存の idx_elections_governing_body_term (governing_body_id, term_number) を削除し、
election_type を含む3カラムの UNIQUE インデックスに再作成する。

衆議院と参議院で同一の term_number を持つ選挙が共存できなかった問題を修正。

関連: Issue #1279
"""

from alembic import op


revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 既存の2カラムUNIQUEインデックスを削除
    op.execute("DROP INDEX IF EXISTS idx_elections_governing_body_term")

    # election_type を含む3カラムUNIQUEインデックスを作成
    # NOTE: election_type は NULL 許可カラム。PostgreSQL では NULL 同士は
    # 重複とみなされないため、同じ (governing_body_id, term_number) で
    # election_type が NULL のレコードは複数存在しうる。
    op.create_index(
        "idx_elections_governing_body_term",
        "elections",
        ["governing_body_id", "term_number", "election_type"],
        unique=True,
    )


def downgrade() -> None:
    # 3カラムUNIQUEインデックスを削除
    op.execute("DROP INDEX IF EXISTS idx_elections_governing_body_term")

    # 元の2カラムUNIQUEインデックスを再作成
    op.create_index(
        "idx_elections_governing_body_term",
        "elections",
        ["governing_body_id", "term_number"],
        unique=True,
    )
