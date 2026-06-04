# Low-Level Design (LLD) — Spatial Boundaries Reference Model (PostGIS)

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) | Target Location: `docs/lld/spatial_boundaries_lld.md` | References: `docs/prd/spatial_boundaries_prd.md`, `docs/database_schema.md`
> Status: `Draft`

---

## 1. Physical Schema and postgis Extension

We will define a new reference table `spatial_boundaries` that stores sub-counties mapping, linking them to parent basins and storing centroid coordinates.

### 1.1 Table Definition: `spatial_boundaries`

| Column | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY` | Unique UUID. |
| `name` | `VARCHAR(100)` | `NOT NULL` | Name of the sub-county / district. |
| `basin_id` | `UUID` | `REFERENCES basins(id) ON DELETE CASCADE` | Foreign Key pointing to the parent basin UUID. |
| `centroid_geom` | `geometry(Point, 4326)` | `NOT NULL` | Spatial point coordinates of the sub-county centroid. |

```sql
CREATE TABLE spatial_boundaries (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    basin_id UUID NOT NULL REFERENCES basins(id) ON DELETE CASCADE,
    centroid_geom geometry(Point, 4326) NOT NULL
);
CREATE INDEX idx_spatial_boundaries_geom ON spatial_boundaries USING GIST (centroid_geom);
CREATE INDEX idx_spatial_boundaries_basin_id ON spatial_boundaries(basin_id);
```

---

## 2. Component Design & Relationships

We will implement:
- **ORM Model**: `SpatialBoundary` in `backend/app/models/spatial.py`.
- **Pydantic Schemas**: `SpatialBoundaryBase`, `SpatialBoundaryCreate`, `SpatialBoundary` in `backend/app/schemas/spatial.py`.
- **FastAPI Endpoints**: `GET /api/v1/reference/sub-counties` and `POST /api/v1/reference/sub-counties` in `backend/app/routers/spatial_router.py`.

---

## 3. Pydantic GeoJSON Schemas & Serialization

For API requests and responses, the GeoJSON structure is validated using Pydantic:
* Request payload validation converts a GeoJSON Point object to WKT.
* Response serialization converts WKB/WKT geometry back to GeoJSON.

---

## 4. API Endpoints Contract

### 4.1 Get Sub-Counties list
* **Endpoint**: `GET /api/v1/reference/sub-counties`
* **Response Payload (200 OK)**:
  ```json
  [
    {
      "id": "e22934ef-7e9b-4f1b-90f1-4df2348a7b1b",
      "name": "Tarime",
      "basin_id": "9bd4883b-ba50-42a7-8277-0fc5e44e0ffe",
      "centroid_geom": {
        "type": "Point",
        "coordinates": [34.47, -1.24]
      }
    }
  ]
  ```

### 4.2 Create Sub-County
* **Endpoint**: `POST /api/v1/reference/sub-counties`
* **Role Requirement**: `Admin`.
* **Request Payload**:
  ```json
  {
    "name": "Butiama",
    "basin_id": "9bd4883b-ba50-42a7-8277-0fc5e44e0ffe",
    "centroid_geom": {
      "type": "Point",
      "coordinates": [34.05, -1.78]
    }
  }
  ```
* **Response Payload (201 Created)**
