"""create_sync_watermarks_table

Revision ID: d3f7a1f5922c
Revises: 31a98d3049de
Create Date: 2026-06-09 07:20:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d3f7a1f5922c"
down_revision: Union[str, None] = "31a98d3049de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sync_watermarks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_system", sa.String(length=50), nullable=False),
        sa.Column("form_id", sa.String(length=100), nullable=True),
        sa.Column("last_sync_time", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_system", "form_id", name="uq_sync_watermarks_source_form"
        ),
    )


def downgrade() -> None:
    op.drop_table("sync_watermarks")
