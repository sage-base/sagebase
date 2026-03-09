"""politician_operation_logsのoperation_type CHECK制約にmergeを追加.

Revision ID: 040
Revises: 039
Create Date: 2026-03-10

政治家統合（マージ）機能の追加に伴い、operation_typeに'merge'を許容する。
"""

from alembic import op


revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """CHECK制約を更新してmergeを追加."""
    op.execute("""
        ALTER TABLE politician_operation_logs
        DROP CONSTRAINT IF EXISTS check_operation_type;
    """)
    op.execute("""
        ALTER TABLE politician_operation_logs
        ADD CONSTRAINT check_operation_type
        CHECK (operation_type IN ('create', 'update', 'delete', 'merge'));
    """)


def downgrade() -> None:
    """CHECK制約を元に戻す."""
    op.execute("""
        ALTER TABLE politician_operation_logs
        DROP CONSTRAINT IF EXISTS check_operation_type;
    """)
    op.execute("""
        ALTER TABLE politician_operation_logs
        ADD CONSTRAINT check_operation_type
        CHECK (operation_type IN ('create', 'update', 'delete'));
    """)
