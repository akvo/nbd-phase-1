# LLD — Wetland Domain Map Zoom & Overlay

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) / Amelia (Developer) | Target Location: `docs/lld/wetland_map_integration_lld.md`
> Initiative/Epic: Wetland Domain Map Zoom & Overlay

---

## 1. Asset Storage
- Store spatial GeoJSON datasets as static files inside the frontend public folder:
  - `frontend/public/spatial/mara-wetland.geojson`
  - `frontend/public/spatial/sio-siteko-wetland.geojson`

---

## 2. Component Design & State Integration

### 2.1 App Page State (`frontend/src/app/page.tsx`)
- Add a new `wetlandGeometry` state to store the parsed GeoJSON shapefile representation for the active wetland:
  ```typescript
  const [wetlandGeometry, setWetlandGeometry] = useState<any>(null);
  ```
- Fetch the appropriate GeoJSON geometry asynchronously when `selectedDomain === "wetland"` and the active basin changes:
  - MARA basin -> Fetch `/spatial/mara-wetland.geojson`
  - SIO basin -> Fetch `/spatial/sio-siteko-wetland.geojson`
  - Otherwise -> Reset `wetlandGeometry` to `null`.
- Pass `wetlandGeometry` as a prop to the `MapViewer` component.

### 2.2 Leaflet Map Viewer (`frontend/src/components/ui/map-viewer.tsx`)

#### 2.2.1 Props Interface
Extend `MapViewerProps` to receive `wetlandGeometry`:
```typescript
interface MapViewerProps {
  // ... existing props
  wetlandGeometry?: any;
}
```

#### 2.2.2 Bounds Controller Adjustment (`MapController` component)
Update the bounds adjustment logic to prioritize focusing on the wetland polygon if it is loaded:
```typescript
const targetGeom = wetlandGeometry || basinGeometry;
if (targetGeom) {
  const layer = L.geoJSON(targetGeom);
  map.fitBounds(layer.getBounds(), { padding: [30, 30] });
}
```

#### 2.2.3 Layer Rendering Order
- Render the base map `<TileLayer>` first.
- Render the outer `<GeoJSON>` layer for the `basinGeometry` (styled with a thin outline: `color: "#0d9488"`, weight `2`, opacity `0.8`, `fillOpacity: 0.05`).
- Render the inner `<GeoJSON>` layer for the `wetlandGeometry` (styled with a solid teal fill: `color: "#14b8a6"`, weight `2`, opacity `0.9`, `fillOpacity: 0.12`).
- Disable event propagation on GeoJSON overlays (`interactive={false}`) so that marker clicks are not intercepted.

---

## 3. Verification & Testing Plan
- Validate that switching domain to "Wetlands" shifts map focus and centers it directly around the wetland boundaries.
- Ensure the basin boundary outline is still displayed for geographical reference.
- Verify that switching back to "Pollution Reports" resets map zoom to the full basin.
