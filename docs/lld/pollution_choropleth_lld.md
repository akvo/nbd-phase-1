# LLD — Pollution Report Choropleth Map

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) / Amelia (Developer) | Target Location: `docs/lld/pollution_choropleth_lld.md`
> Initiative/Epic: Pollution Report Choropleth — Sub-Country Shapefile Overlay

---

## 1. Technical Strategy & Library Setup
- Use `@turf/boolean-point-in-polygon` and `@turf/helpers` for high-performance point-in-polygon tests.
- Copy sub-county shapefiles into the public directory as static JSON datasets:
  - `/spatial/mara-subcounties.geojson`
  - `/spatial/sio-subcounties.geojson`

---

## 2. Dynamic Point-in-Polygon Aggregation (`page.tsx`)
- Define `ChoroplethFeature` extending GeoJSON `Feature` with:
  - `incidentCount: number`
  - `incidentBreakdown: Record<string, number>`
- Compute `choroplethLayers` inside a `useMemo` dependent on `[filteredIncidents, selectedBasin, selectedDomain]`:
  - Fetch/load the sub-regions shapefile for the active basin.
  - Classify each incident in `filteredIncidents` using `booleanPointInPolygon`.
  - Accumulate the total count and group counts by incident type (extracted from answer values where `question_id === 2`).
- Pass the compiled array as the `choroplethLayers` prop to `MapViewer`.
- Set `markers=[]` when the Pollution domain is active to hide individual point markers.

---

## 3. Choropleth Map Layer (`map-viewer.tsx`)
- Render the `choroplethLayers` using a Leaflet `<GeoJSON>` component.
- **Dynamic Fill Color**: Shaded by count:
  - 0: Slate-grey (`#f1f5f9`)
  - 1–5: Amber (`#fef3c7`)
  - 6–15: Orange (`#f97316`)
  - 16+: Red (`#dc2626`)
- **Hover Styles**: Bind `onEachFeature` events to update border weights (to `3px`) and fill opacity on mouseover/mouseout.
- **Popups**: Bind clicks to open standard Leaflet Popups detailing:
  - Sub-region name label.
  - Total incident count.
  - Tabular breakdown of counts grouped by incident type.

---

## 4. Verification & Testing Plan
- Test that selecting the Pollution domain removes point pins and displays sub-region boundary overlays.
- Verify that clicking a sub-region polygon shows correct summary details.
- Verify that color coding updates dynamically when filters or active basins change.
