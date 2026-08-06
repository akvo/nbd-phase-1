"""add ward level spatial boundaries index

Revision ID: b9e8d7c6f5a4
Revises: a8b7c6d5e4f3
Create Date: 2026-08-06 10:35:00.000000

"""

from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b9e8d7c6f5a4"
down_revision: Union[str, None] = "a8b7c6d5e4f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_spatial_boundaries_level_parent",
        "spatial_boundaries",
        ["level", "parent_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_spatial_boundaries_level_parent",
        table_name="spatial_boundaries",
    )
