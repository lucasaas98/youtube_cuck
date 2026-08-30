"""add channel avatar and description

Revision ID: e4a9fe9674f8
Revises: 3fed6076c66a
Create Date: 2026-08-30 14:16:55.043166+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4a9fe9674f8"
down_revision: Union[str, None] = "3fed6076c66a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "channel", sa.Column("avatar_path", sa.String(length=255), nullable=True)
    )
    op.add_column("channel", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("channel", "description")
    op.drop_column("channel", "avatar_path")
