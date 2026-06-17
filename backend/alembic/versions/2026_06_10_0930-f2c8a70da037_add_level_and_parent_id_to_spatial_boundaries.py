"""add level and parent_id to spatial_boundaries

Revision ID: f2c8a70da037
Revises: b7d23a41c2c3
Create Date: 2026-06-10 09:30:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2c8a70da037"
down_revision: Union[str, None] = "b7d23a41c2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add level column,
    # default to 1 so existing rows are valid, then remove default
    op.add_column(
        "spatial_boundaries",
        sa.Column("level", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("spatial_boundaries", "level", server_default=None)

    # Add parent_id column
    op.add_column(
        "spatial_boundaries",
        sa.Column("parent_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_spatial_boundaries_parent_id",
        "spatial_boundaries",
        "spatial_boundaries",
        ["parent_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Create indexes
    op.create_index(
        "idx_spatial_boundaries_level", "spatial_boundaries", ["level"]
    )
    op.create_index(
        "idx_spatial_boundaries_basin_level",
        "spatial_boundaries",
        ["basin_id", "level"],
    )


def downgrade() -> None:
    op.drop_index("idx_spatial_boundaries_basin_level")
    op.drop_index("idx_spatial_boundaries_level")
    op.drop_constraint(
        "fk_spatial_boundaries_parent_id",
        "spatial_boundaries",
        type_="foreignkey",
    )
    op.drop_column("spatial_boundaries", "parent_id")
    op.drop_column("spatial_boundaries", "level")
