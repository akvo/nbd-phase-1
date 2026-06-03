# LLD — Monitoring Site Details Drawer Redesign

* **Stage 3 of 3 — Documentation Hierarchy**
* **Owner**: Winston (Architect) / Amelia (Developer)
* **Initiative/Epic**: Wetland Monitoring Platform UI Enhancements
* **Status**: Proposed / Under Review
* **References**: `docs/prd/site_drawer_redesign_prd.md`

---

## 1. Overview & Scope
Redesign the detailed view inside the monitoring site drawer `frontend/src/components/ui/site-drawer.tsx` to conform to the high-fidelity Figma spec `8222:2494`. This incorporates advanced status indicators, score progress bars, parameter tables, and formatted intervention messages.

---

## 2. Component Design & Layout

We will reconstruct `SiteDrawer` with the following sections (arranged vertically, scrolling within the drawer body):

### 2.1 Header Section
- Left: Site Name (`site.site_name`) in bold text, ID (`site.site_id`) in gray text.
- Right: Large circular status badge (`site.current_health_class`) with background/border tailwind colors matching the severity grade:
  - Class A/B: Green circle (`bg-green-50 text-green-600 border-green-500`)
  - Class C: Orange/Amber circle (`bg-orange-500 text-orange-100 border-transparent` - as per FGD Figma theme details)
  - Class D/E: Red circle (`bg-red-50 text-red-600 border-red-500`)
- Badges line:
  - Country Badge: Map-pin icon + country name.
  - Approval Badge: Pill styling (`Pending Review` vs `Approved`).
  - Adjusted Badge: Pill styling (`IK-adjusted` if `site.is_ik_adjusted`).

### 2.2 Alert Banner (Message Note)
- An orange alert banner (`bg-orange-50 border border-orange-200 text-orange-700`) is displayed if the health grade is `C`, `D`, or `E`, suggesting appropriate intervention measures.

### 2.3 Community Signal Section
- Displays: **Community signal**: `site.community_signal` formatted as regular text with the title bolded.

### 2.4 Parameters Grid (2x2 Card Small Grid)
- Cards for:
  - **pH**: Shows `site.details.physico_chemical.ph` with health status indicator dot.
  - **Water Temperature**: Shows `site.details.physico_chemical.temperature` °C.
  - **Dissolved Oxygen**: Shows `site.details.physico_chemical.dissolved_oxygen` mg/L.
  - **Water Level**: Shows `site.details.catchment_hydrological.water_level` (defaulting to a mock value or `142 cm` from database).

### 2.5 Score Breakdown (Progress Bars)
- Visual progress bar controls representing:
  - Physico-chemical: `site.details.physico_chemical.group_score`
  - Catchment / hydro: `site.details.catchment_hydrological.group_score`
  - Ecological: `site.details.ecological.group_score`
  - Governance index (defaulting to mock values).
- Bottom calculation summary table matching the FGD adjustment scoring block in Figma.

### 2.6 Raw Sampling Method Grid
- A structural table listing metric parameters, values, units, and flags.

---

## 3. Data Schema & Props

### Props Definition
```typescript
interface SiteDrawerProps {
  site: Site | null;
  onClose: () => void;
}
```

---

## 4. Verification Plan

### Automated Tests
- Production compilation verification check: `./dc.sh exec frontend yarn build`

### Manual Verification
- Render the Drawer on mobile and desktop viewports.
- Confirm all card states, color dots, progress bar fills, and alert banners render perfectly.
