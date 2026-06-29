# LLD — NBD Platform Landing Page

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Tech Lead / Winston (Architect) | Target Location: `docs/lld/landing_page_lld.md` | References: `docs/prd/landing_page_prd.md`
> Status: `Approved`

---

## 1. Overview & Scope

**Component / Module**:
Interactive landing page at `/` (`src/app/page.tsx`) mapping basins, monitoring sites, and pollution incidents with search, category filtering, and parameter drill-downs.

**PRD References**:

- FR-001 (Leaflet Map Render)
- FR-002 (Health Grade & Incident Markers)
- FR-003 (Status Toggle Tags)
- FR-004 (Dynamic Search Filtering)
- FR-005 (Figma Detail Cards)
- FR-006 (Static JSON Integration)

---

## 2. Component Design & Layout

The page utilizes a mobile-first responsive layout matching Figma specifications:

- **HeaderNavigation**: Logo, navigation action buttons (Log in, Sign up).
- **Map Container**: Fully fills the background/viewport height. Employs `next/dynamic` to load the Leaflet wrapper with `ssr: false`.
  - **GIS Popups**: Clicking on a site or incident marker opens an enriched, styled popup containing:
    - **Header**: Station name / incident category and a colored status badge (Critical, Elevated, Moderate, or health class letter A-E).
    - **Station Code**: Subtext showing unique station identifier.
    - **Health Index (Sites only)**: Progress bar matching the station's score.
    - **Details Box**: Displaying qualitative signal descriptions or details.
    - **Meta details**: Subtext containing submission date or additional descriptors.
- **Search & Incident Panel**:
  - Appears as a sliding bottom drawer (`src/components/ui/site-drawer.tsx`) on mobile screens (< 768px).
  - Appears as a left-hand floating sidebar on desktop screens (>= 768px).
  - Contains the View Toggle switch (`All`, `Critical`, `At risk`, `Healthy`), search input field, and list of site cards.
  - **Collapsible Cards List (Mobile & Desktop)**: The site cards list itself is collapsible (toggled via the "Monitoring Sites" section header, or via the mobile drag handle button at the top of the panel) to allow maximizing map visibility on mobile screens while keeping the dropdown filters and search input visible at all times.
- **Detailed Site View Card**:
  - **Site Card Anatomy**: Displays the Location Name, site_id code (e.g., `NBD-MARA-002`), and a clean color-coded status dot representing the site's health class.
  - **Removed Elements**: The approved/pending status tags, "IK-adjusted" badge, and "Community Signal" description section are removed to simplify the visual layout.
  - Clicking on a card opens a modal/drawer parameter breakdown (pH, DO, Temp, unit weights, and triggered management actions matching the API contract).

## 3. Data Integration & Schema

Rather than using local static mock JSON, the landing page fetches data from the database using the unauthenticated API endpoints:

### 3.1 API Endpoints

1. **Basin Boundaries**: `GET /api/v1/basins`
   - Returns a list of basins with GeoJSON MultiPolygon geometries.
2. **Monitoring Sites**: `GET /api/v1/sites`
   - Returns a list of sites including their UUID, name, coordinates (in GeoJSON Point `[longitude, latitude]` format), latest health class, and recommended management actions.
3. **Approved Pollution Incidents**: `GET /api/v1/submissions?status=APPROVED`
   - Returns all approved submissions. The frontend filters these by `form_name === "Pollution Reporting Form"`.
   - The coordinates are extracted from the `geo` field (`[longitude, latitude]` format).

### 3.2 Coordinate and Severity Mapping

- **Leaflet Coordinate Flip**: All coordinates are mapped from database GeoJSON format `[longitude, latitude]` to Leaflet's coordinate structure `[latitude, longitude]`.
- **Incident Severity Translation**: Submissions do not contain an explicit severity string. The frontend maps the `incident_type` option value to a severity status:
  - Option `3` (Fish or animal kills) -> **Critical**
  - Options `1` (Water colour) and `2` (Smell) -> **Elevated**
  - Options `4` (Storm event), `5` (High water level), and `6` (Low water level) -> **Moderate**

---

## 4. Verification Plan

### Automated Tests

- Run `yarn test` to verify component compilation.
- Verify that dynamic search and status filtering update the markers and card listing correctly.

### Manual Verification

- Simulate mobile devices (e.g. 375px width) in Chrome DevTools:
  - Verify map occupies the top section (`45vh`) and the panel forms the bottom half.
  - Verify that a single-finger swipe on the map scrolls the page, and two-finger swipe pans the map.
  - Verify coordinates are correctly positioned on the map (not flipped).
  - Verify filtering by health/severity.
