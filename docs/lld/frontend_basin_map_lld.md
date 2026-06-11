# Low-Level Design (LLD) — Frontend Basin Boundary Map

## 1. Component Interface and Props

We will extend `MapViewer` in `frontend/src/components/ui/map-viewer.tsx` to receive and display the active basin's GeoJSON geometry.

### 1.1 Props Extension

```typescript
// frontend/src/components/ui/map-viewer.tsx
interface MapViewerProps {
  center: [number, number];
  zoom: number;
  markers?: MapMarker[];
  className?: string;
  zoomOffsetClass?: string;
  basinGeometry?: any; // Added: GeoJSON geometry of the selected basin
}
```

---

## 2. Dynamic Map Bounds Adjustment

Leaflet's `<MapContainer>` center/zoom props are immutable after initial mount. To re-center the map when the active basin changes, we will implement a helper component `<MapController>` that accesses Leaflet's map instance via the `useMap` hook:

```typescript
import { useMap, GeoJSON } from "react-leaflet";
import * as L from "leaflet";

function MapController({ basinGeometry }: { basinGeometry: any }) {
  const map = useMap();

  useEffect(() => {
    if (basinGeometry) {
      try {
        const layer = L.geoJSON(basinGeometry);
        map.fitBounds(layer.getBounds(), { padding: [30, 30] });
      } catch (err) {
        console.error("Failed to fit bounds to basin geometry:", err);
      }
    }
  }, [basinGeometry, map]);

  return null;
}
```

---

## 3. Leaflet Rendering and Styling

We will render the basin boundary using `react-leaflet`'s `<GeoJSON>` component inside `<MapContainer>`:

```typescript
{basinGeometry && (
  <GeoJSON
    key={JSON.stringify(basinGeometry)}
    data={basinGeometry}
    style={{
      color: "#0d9488",      // Premium teal stroke color
      weight: 2,             // Thin clean boundary outline
      opacity: 0.8,
      fillColor: "#0d9488",  // Light fill
      fillOpacity: 0.05      // Semi-transparent interior overlay
    }}
  />
)}
```

---

## 4. Frontend API Data Integration

In `frontend/src/app/page.tsx`, we will fetch the active basin's spatial geometry from `/api/v1/basins/{basin_id}` or load it dynamically from the backend and pass it down to `<MapViewer>`:

```typescript
// Example fetch or state assignment:
const [basinGeometry, setBasinGeometry] = useState<any>(null);

useEffect(() => {
  // Fetch active basin coordinates from API when selectedBasin changes
  fetch(`/api/v1/basins`)
    .then(r => r.json())
    .then(data => {
      const activeBasin = data.find((b: any) => b.code === selectedBasin);
      if (activeBasin && activeBasin.geom) {
        setBasinGeometry(activeBasin.geom);
      }
    });
}, [selectedBasin]);
```
