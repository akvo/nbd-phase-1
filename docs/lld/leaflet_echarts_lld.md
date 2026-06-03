# LLD — Leaflet and ECharts Integration

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Tech Lead | Target Location: `docs/lld/leaflet_echarts_lld.md`
> References: [leaflet_echarts_prd.md](docs/prd/leaflet_echarts_prd.md)

---

## 1. Overview & Setup

This Low-Level Design (LLD) documents the implementation of example components for Leaflet and Apache ECharts on the NBD design system gallery page.

---

## 2. Component Design & Architecture

### A. ECharts Component
We will construct a reusable and clean wrapper for Apache ECharts using standard React refs. This avoids peer dependency conflicts in React 19.

*   **Location**: `src/components/ui/echarts-chart.tsx`
*   **Implementation Strategy**:
    *   Use a React `useRef<HTMLDivElement>` to hold the target element.
    *   Initialize the chart instance inside a `useEffect` hook using `echarts.init()`.
    *   Apply options with `chart.setOption()`.
    *   Attach a `ResizeObserver` or window resize listener to trigger `chart.resize()` dynamically.

### B. Leaflet Map Component (SSR Handling)
Leaflet tries to access `window` on import. In Next.js App Router, this will crash during server-side pre-rendering (`window is not defined`).
*   **Location**: `src/components/ui/map-viewer.tsx` (using `"use client"`)
*   **Import Strategy**:
    *   Create the map viewer containing `<MapContainer>`, `<TileLayer>`, and `<Marker>`.
    *   In the main `page.tsx` (under `src/app/page.tsx`), import `MapViewer` dynamically using:
        ```typescript
        const MapViewer = dynamic(() => import("@/components/ui/map-viewer"), {
          ssr: false,
          loading: () => <div className="h-64 bg-grey-100 flex items-center justify-center">Loading Map...</div>
        });
        ```

---

## 3. Data Schema & Props

### EChartsChart Props
```typescript
interface EChartsChartProps {
  options: echarts.EChartsOption;
  className?: string;
}
```

### MapViewer Props
```typescript
interface MapViewerProps {
  center: [number, number];
  zoom: number;
  markers?: Array<{ position: [number, number]; popupText?: string }>;
  className?: string;
}
```

---

## 4. Verification Plan

- Run `./dc.sh exec frontend npx next build` to guarantee SSR and bundler compilation works without errors.
- Navigate to `http://localhost:3000/` and check both components rendering and interacting correctly.
