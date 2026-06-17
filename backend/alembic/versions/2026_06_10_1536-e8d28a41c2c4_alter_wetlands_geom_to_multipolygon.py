"""alter wetlands geom to multipolygon

Revision ID: e8d28a41c2c4
Revises: f2c8a70da037
Create Date: 2026-06-10 15:36:00.000000

"""

from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e8d28a41c2c4"
down_revision: Union[str, None] = "f2c8a70da037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop existing GIST index
    op.execute("DROP INDEX IF EXISTS idx_wetlands_geom")

    # 2. Alter column type using PostGIS helpers to convert to MultiPolygon
    op.execute(
        "ALTER TABLE wetlands ALTER COLUMN geom "
        "TYPE geometry(MultiPolygon, 4326) USING ST_Multi(geom)"
    )

    # 3. Re-create GIST index
    op.execute("CREATE INDEX idx_wetlands_geom ON wetlands USING GIST (geom)")


def downgrade() -> None:
    # 1. Drop index
    op.execute("DROP INDEX IF EXISTS idx_wetlands_geom")

    # 2. Revert back to POLYGON (by taking the first polygon component)
    op.execute(
        "ALTER TABLE wetlands ALTER COLUMN geom TYPE geometry(Polygon, 4326) "
        "USING ST_GeometryN(geom, 1)"
    )

    # 3. Re-create index
    op.execute("CREATE INDEX idx_wetlands_geom ON wetlands USING GIST (geom)")
