# LLD — [FE Mobile] Task 6: PDF Export Trigger

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) / Amelia (Developer) | Target Location: `docs/lld/pdf_export_lld.md`
> Initiative/Epic: PDF Export Trigger

---

## 1. Component Enhancements (`frontend/src/components/ui/site-drawer.tsx`)

### 1.1 Dynamic Import of MapViewer
To prevent server-side rendering (SSR) failures when importing Leaflet:
```typescript
import dynamic from "next/dynamic";

const MapViewer = dynamic(() => import("@/components/ui/map-viewer"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-slate-50 text-xs text-slate-400">
      Loading map...
    </div>
  ),
});
```

### 1.2 Interactive Map Section
Add a Location Map section before the final scroll container padding:
- Check if `site.coordinates` exists.
- Render a standard Card/Box containing the `MapViewer` centered at the coordinates with a single Marker representing the site.

### 1.3 Export Trigger Button
- Render a blue button at the bottom of the drawer body.
- Label: `"Export detailed report (PDF)"`
- Icon: `LucideIcons.Printer`
- On Click: Trigger `window.print()`.

---

## 2. Print Layout Styling

### 2.1 CSS Utility classes
Inject media rules inside the stylesheet or as specific inline print utilities (`print:*` tailwind classes if tailwind is active, or standard `@media print` rules inside global css).
- Hide everything except the print container:
  ```css
  @media print {
    body {
      background: white !important;
      color: black !important;
    }
    /* Hide map viewer control overlays, close buttons, and page backgrounds */
    .no-print,
    .leaflet-control-zoom,
    .leaflet-control-attribution,
    button[aria-label="Close"] {
      display: none !important;
    }
    /* Force grid elements to stretch full width on mobile print */
    .grid {
      display: block !important;
    }
    .grid > * {
      margin-bottom: 1rem !important;
      width: 100% !important;
    }
  }
  ```

---

## 3. Verification & Testing Plan

### 3.1 Automated Vitest suite (`frontend/src/components/ui/__tests__/site-drawer.test.tsx`)
Verify the presence of the button and action binding:
- Mock `window.print` using `vi.spyOn(window, 'print').mockImplementation(() => {})`.
- Render the `SiteDrawer` with a mock site.
- Find the button with text containing `"Export detailed report"`.
- Simulate a click event on it.
- Assert that `window.print` was called.
