# Product Requirements Document (PRD) — Wetland Domain Map Zoom & Overlay

* **Stage 2 of 3 — Documentation Hierarchy**
* **Initiative**: Wetland Domain Map Zoom & Overlay
* **Owner**: John (Product Manager) & Winston (Architect)
* **Status**: Draft — Pending Approval
* **Related Docs**:
* [Frontend Basin Boundary Map PRD](./frontend_basin_map_prd.md)
* [Map Filter Bar Component PRD](./map_filter_prd.md)

---

## I. Overview & Goal

### Problem Statement

When a user selects the **Wetland domain** on the portal, they are interested in monitoring specific wetland areas (Mara Wetland or Sio-Siteko Wetland). Currently, the map stays zoomed out at the basin-wide scale (Mara Basin or Sio-Siteko Basin). We want the map to automatically zoom and center directly onto the boundary of the respective wetland polygon while maintaining the outer basin border overlay for geographical context.

### Core Metrics

* **GIS Target Precision**: 100% of the active wetland's GeoJSON polygon outline loads and renders overlay on the map.
* **Auto-Zoom Accuracy**: The map automatically adjusts its bounds (`fitBounds`) to tightly wrap the wetland geometry upon switching to the Wetland domain.
* **Context Preservation**: The outer basin boundary remains visible as a thin stroke overlay when zoomed into the wetland.

---

## II. User Stories & Flows

### Personas

* **Ecologist / Field Manager**: Wants to select the Wetland domain and see the exact extent of the wetland polygon so they can assess which monitoring stations (site pins) fall inside or near the wetland area.

### User Journey

1. The user visits the portal dashboard.
2. Under the default domain selection (**Wetland domain**), the dashboard fetches the relevant wetland GeoJSON boundary (e.g., `mara-wetland.geojson` for MARA, or `sio-siteko-wetland.geojson` for SIO_SITEKO).
3. The map automatically zooms and centers around the bounds of the wetland area.
4. The wetland polygon is displayed as a solid teal/green overlay (opacity ~12%), while the larger basin border outline is still rendered as a thin boundary line (opacity ~5%).
5. The user switches to the **Pollution Reports domain** in the header.
6. The map zooms back out to fit the full basin boundary outline (reverting to basin level).

---

## III. Scope Guardrails

### Must-Have

1. **Dynamic Wetland Zooming**: When `selectedDomain === "wetland"`, the map `fitBounds()` is directed to the bounds of the wetland GeoJSON geometry.
2. **Double GeoJSON Layers**: Render both `basinGeometry` (thin boundary) and `wetlandGeometry` (semi-transparent filled polygon) at the same time.
3. **Responsive bounds adjustment**: Ensure touch/drag maps fit correctly on both mobile aspect ratios and desktop widths.
4. **Resets**: Switch back to basin-bounds fitting when switching to other domains (e.g., pollution).

### Nice-to-Have

* Loading state spinner overlay on the map while fetching/rendering large GeoJSON geometries.

### Out of Scope

* Adding individual wetland subset selectors (dynamic cropping of parts of the wetland).

---

## IV. Acceptance Criteria

### User Acceptance Criteria (UAC)

* **UAC-1**: Toggling the domain to "Wetlands" shifts map focus and centers it directly around the wetland coordinates (Mara or Sio-Siteko).
* **UAC-2**: The basin boundary remains visible at all times as an outer reference outline.
* **UAC-3**: Switch to "Pollution Reports" zooms map back out to fit the full basin boundary.

### Technical Acceptance Criteria (TAC)

* **TAC-1**: Store static wetland GeoJSON assets under `frontend/public/spatial/` for fast clientside retrieval.
* **TAC-2**: Pass `wetlandGeometry` prop into `<MapViewer>` alongside `basinGeometry`.
* **TAC-3**: Update the Leaflet map bounds controller (`MapController`) to conditionally prioritize `wetlandGeometry` bounds over `basinGeometry` bounds.
* **TAC-4**: Styling for the wetland layer must use `#14b8a6` (teal-500) with a `fillOpacity` of `0.12` to distinguish it from the outer basin boundary (fill opacity `0.05`).
