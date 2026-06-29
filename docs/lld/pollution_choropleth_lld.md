# LLD — Pollution Report Choropleth Map

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) / Amelia (Developer) | Target Location: `docs/lld/pollution_choropleth_lld.md`
> Initiative/Epic: Pollution Report Choropleth — Sub-Country Shapefile Overlay

---

## 1. Technical Strategy & Library Setup

* Use `@turf/boolean-point-in-polygon` and `@turf/helpers` for high-performance point-in-polygon tests.
* Load generated sub-county shapefiles into the public directory as static JSON datasets:
  * `/spatial/mara-subcounties.geojson`
  * `/spatial/sio-subcounties.geojson`

---

## 2. Dynamic Point-in-Polygon Aggregation (`page.tsx`)

* Define `ChoroplethFeature` extending GeoJSON `Feature` with:
  * `incidentCount: number`
  * `incidentBreakdown: Record<string, number>`
* Compute `choroplethLayers` inside a `useMemo` dependent on `[filteredIncidents, selectedBasin, selectedDomain]`:
  * Fetch/load the sub-regions shapefile for the active basin.
  * Classify each incident in `filteredIncidents` using `booleanPointInPolygon`.
  * Accumulate the total count and group counts by incident type (extracted from answer values where `question_id === 2`).
* Manage state for `selectedSubCounty` (default `null`).
* Pass the compiled array as the `choroplethLayers` prop to `MapViewer`.
* Set `markers=[]` when the Pollution domain is active to hide individual point markers.

### 2.1 Photo Card List Behaviour

* If `selectedSubCounty` is `null`, hide the sidebar cards list entirely.
* If a sub-county is selected, filter `filteredIncidents` to only those inside the selected sub-county.
* Display the filtered reports containing photos, sorted by `created_at` ASC.

---

## 3. Map Viewer & Legend Changes (`map-viewer.tsx`)

* Accept `choroplethLayers?: ChoroplethFeature[]` and `selectedSubCounty` props.
* Render the `choroplethLayers` using a Leaflet `<GeoJSON>` component.
* **Dynamic Fill Color**: Shaded by count:
  * 0: Slate-grey (`#f1f5f9`)
  * 1–5: Amber (`#fef3c7`)
  * 6–15: Orange (`#f97316`)
  * 16+: Red (`#dc2626`)
* **Hover Styles**: Bind `onEachFeature` events to update border weights (to `3px`) and fill opacity on mouseover/mouseout.
* **Click Event**: Bind clicks to set the active `selectedSubCounty` in parent state, triggering the Details Drawer. Do not show standard Leaflet Popups.
* **Legend Component**:
  * Replace the static wetland legend with a graduated choropleth color scale gradient legend when `selectedDomain === "pollution"`.

---

## 4. Details Drawer & Chart (`pollution-details-drawer.tsx`)

Create a right-hand sliding panel `<PollutionDetailsDrawer>` that mounts when `selectedSubCounty` is active:
* **Sub-County Name**: Display the clicked feature name.
* **Latest Status**: Render status indicators based on the most recent incident or environmental status for the sub-county.
* **Horizontal Bar Chart**:
  * Render a horizontal bar chart of grouped incident types (e.g. Oil Spill, Chemical Waste).
  * Render both the incident type labels (names) and the total count labels **inside** the horizontal bars.

---

## 5. Verification & Testing Plan

* Verify that selecting the Pollution domain removes point pins, displays sub-region boundary overlays, and shows the color gradient legend.
* Verify that clicking a sub-region polygon opens the Details Drawer showing the horizontal bar chart with count labels inside the bars.
* Verify that the sidebar card list only appears when a sub-county is selected and displays photo cards sorted by `created_at` ASC.
