"""Add answerability to query_messages."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260515120000"
down_revision: Union[str, Sequence[str], None] = "20260514100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "query_messages",
        sa.Column("answerability", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("query_messages", "answerability")
