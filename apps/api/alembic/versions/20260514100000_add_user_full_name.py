"""Add users.full_name for profile display."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260514100000"
down_revision: Union[str, Sequence[str], None] = "20260513120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "full_name")
