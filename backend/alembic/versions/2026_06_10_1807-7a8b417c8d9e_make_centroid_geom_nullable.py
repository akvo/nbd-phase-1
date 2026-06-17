"""make centroid_geom nullable

Revision ID: 7a8b417c8d9e
Revises: e8d28a41c2c4
Create Date: 2026-06-10 18:07:00.000000

"""

from typing import Sequence, Union
from alembic import op
from geoalchemy2 import Geometry


# revision identifiers, used by Alembic.
revision: str = "7a8b417c8d9e"
down_revision: Union[str, None] = "e8d28a41c2c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "spatial_boundaries",
        "centroid_geom",
        existing_type=Geometry("POINT", srid=4326),
        nullable=True,
    )


def downgrade() -> None:
    # Note: downgrade might fail if there are rows with
    # NULL values in the table.
    op.alter_column(
        "spatial_boundaries",
        "centroid_geom",
        existing_type=Geometry("POINT", srid=4326),
        nullable=False,
    )
