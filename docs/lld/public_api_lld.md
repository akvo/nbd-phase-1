# Low-Level Design (LLD) — Public Open Data API (Sub-Task 1)

## 1. Component Overview
The Public Open Data API component provides unauthenticated, read-only REST endpoints under the `/api/v1` namespace. This layer separates public access from authenticated administrative services, strictly enforcing privacy by aggregating incident data to the sub-county level and exposing only pre-sanitized health score metrics.

## 2. Interface Specifications (API Contract)

### 2.1 Get Sites
- **Path**: `GET /api/v1/sites`
- **Authentication**: None
- **Query Parameters**:
  - `search` (string, optional): Matches `site.name` or `site.description` (case-insensitive ILIKE).
  - `health_class` (string, optional): Comma-separated list of health class letters (e.g. `A,B,C`).
  - `basin` (string, optional): Matches name of the containing `Basin`.
- **Response**: List of sites including latest health status color and code.

### 2.2 Get Site Details
- **Path**: `GET /api/v1/sites/{site_id}`
- **Authentication**: None
- **Response**: Detailed site record including its latest calculated status and recommendations (moved from spatial router to public namespace).

### 2.3 Get Site Scores History
- **Path**: `GET /api/v1/sites/{site_id}/scores`
- **Authentication**: None
- **Query Parameters**:
  - `limit` (integer, default 100): Pagination limit.
  - `offset` (integer, default 0): Pagination offset.
- **Response**: Paginated array of `HealthScore` history ordered by date descending.

### 2.4 Get Site External GEE Data
- **Path**: `GET /api/v1/sites/{site_id}/external/{source}`
- **Authentication**: None
- **URL Parameters**:
  - `source` (string): Pre-defined identifier matching `ndvi` (Sentinel-2) or `precipitation` (CHIRPS).
- **Response**: Latest values matching GEE dataset.

### 2.5 Get Incident Aggregations
- **Path**: `GET /api/v1/incidents`
- **Authentication**: None
- **Query Parameters**:
  - `basin` (string, optional): Filter by basin name.
- **Response**: Array of reports grouped by sub-county. Zero PII is returned.

## 3. Data Model & Database Changes
- **Migration**: Added `description` column (TEXT, NULL) to `sites` table.
- **Model Integration**: Updated SQLAlchemy model `Site` with `description = Column(Text, nullable=True)`.

## 4. Logic & Implementation Details

### 4.1 Incident Grouping Join Strategy
```
datapoint
  |--> site_id -> Site --> wetland_id -> Wetland --> basin_id -> Basin --> sub_county
```
For instances where `datapoint.site_id` is set, we resolve sub-counties through the Site -> Wetland -> Basin hierarchy. If coordinates are present, PostGIS spatial join checks are applied.

### 4.2 Error Handling & Fallbacks
- Returns `HTTP 404 Not Found` for invalid site IDs or unknown external sources.
- Returns `HTTP 422 Unprocessable Entity` for invalid query formats or unsupported health classes.
