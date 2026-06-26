# LLD — Map Filter Bar Component

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) / Amelia (Developer) | Target Location: `docs/lld/map_filter_lld.md`
> Initiative/Epic: Map Filter Bar — Fixed Sub-Header Filter Component

---

## 1. UI Architecture & Sticky Layout
- Create a new component at `frontend/src/components/ui/map-filter.tsx`.
- The filter bar is styled as a sticky sub-header underneath the main header:
  - Parent container uses Tailwind classes `sticky top-16 z-20 w-full border-b border-slate-200 bg-white/95 backdrop-blur-sm shadow-sm`.
  - Header height + Filter bar height are accounted for in absolute positioning of sidebars (`top-[112px]`).

---

## 2. Component Design (`map-filter.tsx`)

### 2.1 Props Interface
```typescript
interface MapFilterProps {
  domain: "wetland" | "pollution";
  selectedBasin: string;
  onBasinChange: (basin: string) => void;
  // Wetland filters
  wetlandOptions: { value: string; label: string }[];
  selectedWetland: string;
  onWetlandChange: (wetland: string) => void;
  selectedHealthFilter: string;
  onHealthFilterChange: (status: string) => void;
  // Pollution filters
  selectedIncidentType: string;
  onIncidentTypeChange: (type: string) => void;
  selectedDateFrom: string;
  onDateFromChange: (date: string) => void;
  selectedDateTo: string;
  onDateToChange: (date: string) => void;
}
```

### 2.2 Domain-Aware Layout & Mobile Collapsing
- **Desktop (md and larger)**: Displayed as a single horizontal row.
  - Wetland: Basin dropdown, Wetland dropdown, Status buttons group.
  - Pollution: Basin dropdown, Incident Type dropdown, Date Range Pickers.
- **Mobile (< md)**: Show only the Basin Selector dropdown and a toggle button `More Filters`.
  - Clicking `More Filters` expands/collapses a lower panel containing the domain-specific filters using standard transition animations.

---

## 3. Integration & Code Cleanups (`page.tsx`)
- Import and render `<MapFilter>` directly below `<SiteHeader>`.
- Remove the search input components and all `searchQuery` state filter operations from `filteredSites` and `filteredIncidents` arrays.
- Remove `<DomainSelector>` from the collapsible sidebar and feed it to the new filter bar props.

---

## 4. Verification & Testing Plan
- Verify that changing filters correctly cascades down to filtered lists and map markers.
- Verify mobile collapsing layout on responsive screens.
- Run tests in `map-filter.test.tsx` to verify component triggers and callbacks.
