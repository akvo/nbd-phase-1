# Low-Level Design (LLD) — Spatial Boundaries Reference Model (PostGIS)

## 1. Physical Schema and PostGIS Extension

We will update the definition of `spatial_boundaries` to use the **Adjacency List** pattern (`parent_id`) combined with **Hierarchical Depth Levels** (`level`).

### 1.1 Table Definition: `spatial_boundaries`

| Column | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, `DEFAULT gen_random_uuid()` | Unique identifier. |
| `name` | `VARCHAR(100)` | `NOT NULL` | Name of the boundary element (e.g. "Mara Region"). |
| `level` | `INTEGER` | `NOT NULL` | Hierarchy level (Indexed). |
| `parent_id` | `UUID` | `REFERENCES spatial_boundaries(id) ON DELETE CASCADE` | Parent boundary pointer. |
| `basin_id` | `UUID` | `REFERENCES basins(id) ON DELETE CASCADE`, `NOT NULL` | Associated basin pointer. |
| `centroid_geom` | `geometry(Point, 4326)` | `NOT NULL` | PostGIS centroid coordinate. |

### 1.2 SQL Schema & Indices

```sql
CREATE TABLE spatial_boundaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    level INTEGER NOT NULL,
    parent_id UUID REFERENCES spatial_boundaries(id) ON DELETE CASCADE,
    basin_id UUID NOT NULL REFERENCES basins(id) ON DELETE CASCADE,
    centroid_geom geometry(Point, 4326) NOT NULL
);

-- Optimize USSD menu queries filtering by basin and level
CREATE INDEX idx_spatial_boundaries_basin_level ON spatial_boundaries (basin_id, level);

-- Spatial index for centroid queries
CREATE INDEX idx_spatial_boundaries_centroid_gist ON spatial_boundaries USING GIST (centroid_geom);
```

---

## 2. Component Design & Python Enum

We will define a strict Python Enum for hierarchy levels to avoid magic numbers in application code.

### 2.1 Enum Definition
```python
# backend/app/models/spatial.py
import enum

class BoundaryLevel(int, enum.Enum):
    REGION = 1        # Province / Region
    DISTRICT = 2      # District / County / Kabupaten
    SUB_COUNTY = 3    # Sub-county / Parish / Kecamatan
```

### 2.2 SQLAlchemy ORM Model
```python
class SpatialBoundary(Base):
    __tablename__ = "spatial_boundaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    level = Column(Integer, nullable=False, index=True)
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("spatial_boundaries.id", ondelete="CASCADE"),
        nullable=True,
    )
    basin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("basins.id", ondelete="CASCADE"),
        nullable=False,
    )
    centroid_geom = Column(Geometry("POINT", srid=4326), nullable=False)

    basin = relationship("Basin")
    parent = relationship("SpatialBoundary", remote_side=[id], backref="children")
```

---

## 3. Data Seeding Strategy

Upon database migration, an Alembic seed or custom migration command will execute:
1. Lookup the `Basin` records for "Mara Basin".
2. Seed 'Mara Region' (`level=1`, `parent_id=null`).
3. Seed the sub-counties/districts: 'Butiama', 'Rorya', 'Tarime', 'Serengeti' (`level=2`, `parent_id` pointing to Mara Region).
