"""parliamentary_group_partiesテーブルを作成（会派⇔政党の多対多中間テーブル）.

Revision ID: 031
Revises: 030
Create Date: 2026-02-26

会派と政党の多対多リレーションを実現するための中間テーブルを追加する。
既存のparliamentary_groups.political_party_idからデータを移行する。

関連: Issue #1243
"""

from alembic import op


revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: parliamentary_group_partiesテーブル作成とデータ移行."""
    # 1. 中間テーブルを作成
    op.execute("""
        CREATE TABLE IF NOT EXISTS parliamentary_group_parties (
            id SERIAL PRIMARY KEY,
            parliamentary_group_id INTEGER NOT NULL
                REFERENCES parliamentary_groups(id) ON DELETE CASCADE,
            political_party_id INTEGER NOT NULL
                REFERENCES political_parties(id) ON DELETE RESTRICT,
            is_primary BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. インデックス作成
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pgp_parliamentary_group_id
        ON parliamentary_group_parties(parliamentary_group_id);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pgp_political_party_id
        ON parliamentary_group_parties(political_party_id);
    """)

    # 3. ユニーク制約: 同一会派・同一政党の組み合わせは1件のみ
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_pgp_group_party
        ON parliamentary_group_parties(parliamentary_group_id, political_party_id);
    """)

    # 4. 部分ユニーク制約: 会派ごとにis_primary=trueは最大1件
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_pgp_primary_per_group
        ON parliamentary_group_parties(parliamentary_group_id) WHERE is_primary = true;
    """)

    # 5. 既存データ移行: political_party_idがNULLでないレコードを移行
    op.execute("""
        INSERT INTO parliamentary_group_parties
            (parliamentary_group_id, political_party_id, is_primary)
        SELECT id, political_party_id, true
        FROM parliamentary_groups
        WHERE political_party_id IS NOT NULL
        ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;
    """)


def downgrade() -> None:
    """Rollback migration: parliamentary_group_partiesテーブル削除."""
    op.execute("DROP TABLE IF EXISTS parliamentary_group_parties;")
