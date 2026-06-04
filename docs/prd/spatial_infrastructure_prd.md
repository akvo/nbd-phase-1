# PRD — Spatial Infrastructure Hierarchy (The Anchors)

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) | Target Location: `docs/prd/spatial_infrastructure_prd.md` | References: `docs/product_brief.md`, `docs/database_schema.md`
> Status: `In Review`

---

## 1. Overview & Goal

The physical geography of the Nile Basin Wetland Monitoring Platform is structured hierarchically:
- A **Hydrological Basin** (e.g., Mara) contains many **Wetlands**.
- A **Wetland** contains many **Monitoring Sites**.

We need to establish the foundational PostGIS tables (`basins`, `wetlands`, `sites`), backend ORM models, schemas, and verification tests to anchor all environmental, citizen-led, and satellite data models.

## 2. User Stories

- **US-001**: As an Admin, I want to create a Basin with its name and polygon boundaries.
- **US-002**: As an Admin, I want to create a Wetland explicitly linked to a Basin with its name and polygon boundaries.
- **US-003**: As an Admin, I want to create a Site explicitly linked to a Wetland with its name and point coordinate, ensuring hierarchical containment.

## 3. Requirements (Scope Guardrails)

### Must-Have
- Relational tables: `basins`, `wetlands`, `sites`.
- PostGIS data types:
  - `basins.geom`: `geometry(MultiPolygon, 4326)`
  - `wetlands.geom`: `geometry(Polygon, 4326)`
  - `sites.geom`: `geometry(Point, 4326)`
- Database constraint: A Site cannot be added without a valid parent `wetland_id`.
- SQLAlchemy ORM models matching the physical schema in `docs/database_schema.md`.
- Pydantic schemas for request validation (handling GeoJSON coordinates/Point/Polygon/MultiPolygon).
- FastAPI backend router with CRUD endpoints to manage these tables.

### Out of Scope
- Frontend UI mapping controls or map displays.
- Import scripts for massive spatial shapefiles (handled in later spikes/tasks).

## 4. Acceptance Criteria

- **UAC-1.1**: As an Admin, I can add a new Site (e.g., `NBD-MARA-001`) only if it is explicitly linked to an existing Wetland parent record.
- **TAC-1.1**: The `wetlands` table must use a PostGIS `GEOMETRY(Polygon, 4326)` or `MultiPolygon` column type.
- **TAC-1.2**: The `sites` table must use a PostGIS `GEOMETRY(Point, 4326)` column type.

## 5. Epic & Ballpark Estimation
- **Component Breakdown**:
  - DB Migration (Alembic/PostGIS): Medium complexity (requires GeoAlchemy2 support).
  - Backend ORM Models & Services: Medium complexity.
  - API Endpoints: Simple complexity.
- **Ballpark Estimate**: 2-3 developer days.
