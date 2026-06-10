# Product Requirements Document (PRD) — Frontend Basin Boundary Map

## I. Overview & Goal

### Problem Statement
Currently, the public dashboard interactive map renders site locations (monitoring stations) and incident reports as markers on an OpenStreetMap canvas, but it lacks the visual bounding boundaries for the selected hydrological basin (Mara Basin or Sio-Siteko Basin). Showing these transboundary boundaries gives geographical context to citizens, analysts, and regional coordinators, allowing them to instantly see the active monitoring zone.

### Core Metric
* **GIS Context Clarity**: 100% of the active basin's MultiPolygon/Polygon boundary outlines load and display correctly on the dashboard map based on the user's selected basin filter.
* **Responsive Visual Fit**: The map auto-fits/re-centers dynamically to contain the bounding box of the active basin.

---

## II. User Stories & Flows

### User Personas
* **Citizen Scientist / Analyst**: Wants to view the dashboard map and see the outline of the basin so that they understand the geographic coverage of the reports and sampling sites.

### User Journey / Flow
1. User loads the portal home page (`/`).
2. The dashboard fetches the active basin list and selects `"MARA"` by default.
3. The page calls the backend to fetch the basin detail including its GeoJSON MultiPolygon coordinates.
4. The Leaflet map renders the Mara Basin boundary outline with a styled, semi-transparent teal overlay.
5. The user toggles the basin selector dropdown to `"SIO_SITEKO"`.
6. The dashboard fetches Sio-Siteko's geometry, re-renders the boundary overlay, and re-centers the map view to fit Sio-Siteko's bounds.

---

## III. Requirements (Scope Guardrails)

### Must-Have
- **Active Basin Boundary Rendering**: Display the selected basin's boundary outline as a styled overlay on the Leaflet map.
- **Dynamic Centering / Fit**: Auto-adjust the map zoom and bounding box (`fitBounds`) to contain the active basin boundary when the selected basin changes.
- **GeoJSON Schema Integration**: Parse standard GeoJSON coordinates returned by the `/api/v1/basins` or `/api/v1/basins/{basin_id}` backend endpoints.

### Nice-to-Have
- Hover effects on the boundary overlay showing basin metadata.

### Out of Scope
- Rendering Level 2 administrative district polygons on the frontend map (only Basin-level boundaries are in-scope for this phase).

---

## IV. Acceptance Criteria

### User Acceptance Criteria (UAC)
* **UAC-1.1**: Toggling the basin selector immediately draws the boundary outline for the selected basin.
* **UAC-1.2**: The map automatically adjusts its bounds to center and show the entire selected basin outline.

### Technical Acceptance Criteria (TAC)
* **TAC-1.1**: The frontend uses Leaflet's `<GeoJSON>` component to render the boundary layers.
* **TAC-1.2**: Style settings use premium custom CSS tokens (e.g., `#0d9488` teal outline, `0.05` fill opacity, `2` stroke width).
* **TAC-1.3**: Integrate map references using Leaflet hooks to perform bounds adjustments.
