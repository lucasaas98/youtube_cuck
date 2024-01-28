"""add channels

Revision ID: 979c997e319a
Revises: 9a5bfc0e48cc
Create Date: 2024-01-27 14:29:03.199999+00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from backend.backfills import backfill_channels, backfill_video_channels

# revision identifiers, used by Alembic.
revision: str = "979c997e319a"
down_revision: Union[str, None] = "9a5bfc0e48cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "channel",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("channel_url", sa.String(length=255), nullable=False),
        sa.Column("channel_name", sa.String(length=255), nullable=False),
        sa.Column("keep", sa.Boolean(), nullable=True),
        sa.Column("inserted_at", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id"),
        sa.UniqueConstraint("channel_url"),
        sa.UniqueConstraint("id"),
    )
    op.add_column("youtube_video", sa.Column("channel_id", sa.Integer(), nullable=True))

    # create the channels from the subscription_manager file
    titles = backfill_channels()
    backfill_video_channels(titles)

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("youtube_video", "channel_id")
    op.drop_table("channel")
    # ### end Alembic commands ###