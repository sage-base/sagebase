"""government_officials_drop_name_yomi

Revision ID: 7b06efead047
Revises: 039
Create Date: 2026-03-09 10:34:17.779079

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "7b06efead047"
down_revision: str | Sequence[str] | None = "039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """government_officialsテーブルからname_yomiカラムを削除する."""
    op.drop_column("government_officials", "name_yomi")


def downgrade() -> None:
    """name_yomiカラムを復元する."""
    op.add_column(
        "government_officials",
        sa.Column("name_yomi", sa.String(200), nullable=True),
    )
