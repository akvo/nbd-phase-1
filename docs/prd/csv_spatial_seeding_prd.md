# Product Requirements Document (PRD) — CSV Spatial Seeding

## I. Overview & Goal
We need to import and seed county and sub-county boundaries dynamically using CSV data instead of relying on hardcoded records in the JSON seeder file. This ensures the database is populated with official administrative boundaries for the Mara and Sio-Siteko basins.

## II. User Stories
* **Story**: As a system administrator, I want the spatial seeding routine to read official CSV lists for counties and sub-counties, so that the database matches the actual Kenyan administrative hierarchy.

## III. Scope Guardrails
* **Must-Have**:
  * Parse `backend/app/seeds/spatial/Mara-sub-counties.csv` and associate with the `MARA` Basin.
  * Parse `backend/app/seeds/spatial/Sio-sub-counties.csv` and associate with the `SIO_SITEKO` Basin.
  * Create Region/County (Level 2) and Sub-County (Level 3) entries dynamically.
  * Correctly link sub-counties to their respective parent counties.
* **Nice-to-Have**:
  * Auto-lookup actual coordinate ranges for centroid generation.
* **Out of Scope**:
  * Loading external GeoJSON boundaries for Level 2/3 (using point centroids instead).

## IV. Technical Acceptance Criteria (TAC)
* **TAC-1**: The script must read standard comma-separated files using Python's `csv` module.
* **TAC-2**: Centroid coordinates column `centroid_geom` on `spatial_boundaries` table must be altered to allow `NULL` values, allowing county/sub-county imports with omitted coordinates.
* **TAC-3**: Sub-counties must hold a valid foreign key referencing their parent county.
