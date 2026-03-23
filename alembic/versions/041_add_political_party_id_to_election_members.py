"""election_membersにpolitical_party_idカラムを追加.

Revision ID: 041
Revises: 040
Create Date: 2026-03-23

選挙時の所属政党をElectionMemberに直接記録するためのカラムを追加する。
"""

import sqlalchemy as sa

from alembic import op


revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """political_party_idカラムを追加."""
    op.add_column(
        "election_members",
        sa.Column(
            "political_party_id",
            sa.Integer(),
            sa.ForeignKey("political_parties.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """political_party_idカラムを削除."""
    op.drop_column("election_members", "political_party_id")
