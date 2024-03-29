"""

Revision ID: 10354a99f503
Revises: df8424836a65
Create Date: 2023-09-30 18:13:57.115314+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "10354a99f503"
down_revision: Union[str, None] = "df8424836a65"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "youtube_video", sa.Column("downloaded_at", sa.Integer(), nullable=True)
    )
    op.execute(
        """
        UPDATE youtube_video
        SET downloaded_at = inserted_at
    """
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("youtube_video", "downloaded_at")
    # ### end Alembic commands ###
