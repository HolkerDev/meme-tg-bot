"""add messages table

Revision ID: b1c2d3e4f5a6
Revises: a9b8774f4efb
Create Date: 2026-07-18 23:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a9b8774f4efb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "messages",
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reaction_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("posted_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("chat_id", "message_id"),
    )
    op.create_index("ix_messages_user_id", "messages", ["user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_messages_user_id", table_name="messages")
    op.drop_table("messages")
