# PRD — NBD Platform Landing Page

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: Sally (UX Designer) + John (Product Manager) | Target Location: `docs/prd/landing_page_prd.md`
> Status: `Approved`

---

## 1. Overview

**One-liner**:
An interactive, high-fidelity, and mobile-optimized landing/home page for the Nile Basin Discourse (NBD) platform that lets users explore wetland health and report pollution incidents on an interactive map.

**What we are building** (What):
We will implement the home page screen matching the Figma specifications, including:

1. **Interactive Leaflet Map**: Displaying the Mara and Sio-Siteko basin overview with site status markers (using colors corresponding to A/B/C/D/E health classifications) and pollution incident markers (Critical, Elevated, Moderate).
2. **Search and Filter Navigation Panel**:
   - A search input to query sites by field, area, or water source.
   - Status toggle tags ("All", "Critical", "At risk", "Healthy") to filter site markers and listings.
   - Dropdown or tab-based control to switch focus between basins (Mara vs. Sio-Siteko).
3. **Site & Incident Information Cards**:
   - Scrollable/collapsible drawer or sidebar displaying list cards with site metrics (site name, ID, health grade, progress indicators, community signal summaries, and badges like "Approved", "IK-adjusted", and country tags).
   - Support for detailed slide-out views showing parameter breakdowns (pH, dissolved oxygen, temperature) and qualitative Indigenous Knowledge (IK) signals when a card is selected.
4. **Live Database Integration**: Fetch all active sites and approved pollution incidents dynamically from backend FastAPI endpoints (`/api/v1/sites` and `/api/v1/submissions?status=APPROVED`).

**Why now** (Strategic context):
The landing page serves as the entry point for citizen scientists, wetland managers, and the public. Providing a responsive, map-centric view immediately brings transparency to wetland degradation trends.

---

## 2. Goals & Success Metrics

| Goal                      | Success Metric                                                          | Baseline         | Target                                | Owner       |
| ------------------------- | ----------------------------------------------------------------------- | ---------------- | ------------------------------------- | ----------- |
| Interactive GIS View      | Correct rendering of Leaflet map with custom styles                     | Generic map      | HSL styled map matching Figma mockups | Developer   |
| Advanced Filter & Search  | Filter response latency for sites and incidents                         | N/A              | < 100ms client-side                   | Developer   |
| Premium Visual Aesthetics | Responsive design system compliance (colors, typography, glassmorphism) | Core skeleton    | 100% match with high fidelity         | UX Designer |
| Accessibility             | Focus outlines and aria labels on interactive map controls and toggles  | Standard browser | WCAG 2.1 AA Compliant                 | Developer   |

---

## 3. Target Users & Personas

| Persona               | Job-to-be-Done                                                   | Key Frustration                                                                  | v1 Priority |
| --------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------- | ----------- |
| **Wetland Watcher**   | View localized pollution incidents and report statuses.          | Complex pages that perform poorly on low-bandwidth/mobile connections.           | Primary     |
| **Citizen Scientist** | View the list of active monitoring sites and review data trends. | Clunky GIS tools that fail to load or are difficult to search on mobile screens. | Primary     |
| **Wetland Manager**   | Scan basin health status and read community/scientific reports.  | Fragmented data overlays with no visual trend summary.                           | Secondary   |

---

## 4. User Stories

| ID     | User Story                                                                                                                                  | Priority (MoSCoW) | FR Reference   |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | -------------- |
| US-001 | As a visitor, I want to see an interactive map representing active basins so I can visually locate monitoring sites and pollution events.   | Must Have         | FR-001, FR-002 |
| US-002 | As a user, I want to filter sites by health categories ("Healthy", "At risk", "Critical") so I can focus on degraded wetlands.              | Must Have         | FR-003         |
| US-003 | As a user, I want to search for specific sites by name, ID, or area so I can jump directly to their location.                               | Must Have         | FR-004         |
| US-004 | As a visitor, I want to click on a site card to view a detailed popup/drawer showing water parameters (pH, DO, Temp) and community signals. | Must Have         | FR-005         |

---

## 5. Functional Requirements

| ID         | Requirement                                                                                                                                                                                                                             | User Story | Priority  |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | --------- |
| **FR-001** | The system MUST render an interactive Leaflet.js map component initialized to the Mara/Sio-Siteko basin coordinates.                                                                                                                    | US-001     | Must Have |
| **FR-002** | The system MUST display site markers colored by health grade (Green for A/B, Orange for C, Red for D/E) and approved pollution incidents with distinct warning colors.                                                                  | US-001     | Must Have |
| **FR-003** | The system MUST support filtering both map markers and list items via the status toggle tags (All, Critical, At risk, Healthy).                                                                                                         | US-002     | Must Have |
| **FR-004** | The system MUST implement a search bar that dynamically filters the list of sites on keyup/change.                                                                                                                                      | US-003     | Must Have |
| **FR-005** | The system MUST display site details matching Figma (including name, ID, and a clean color-coded health status indicator dot).                                                                                                          | US-004     | Must Have |
| **FR-006** | The system MUST fetch active sites and approved incidents dynamically from the database using public API endpoints.                                                                                                                     | US-001     | Must Have |
| **FR-007** | Each site card MUST display Location Name, site_id (code), and a health status indicator dot.                                                                                                                                           | US-004     | Must Have |
| **FR-008** | The site card layout is simplified to remove status tags (Approved/Pending), "IK-adjusted" badges, and community signals to avoid visual clutter.                                                                                       | US-004     | Must Have |
| **FR-009** | If a site requires intervention (e.g., poor health class or recommended management actions exist), a distinct warning banner (e.g. "Action: Site stewards notified...") with an alert icon MUST be displayed at the bottom of the card. | US-004     | Must Have |

---

## 6. Non-Functional Requirements

| Category           | Requirement                 | Metric                                                                                  |
| ------------------ | --------------------------- | --------------------------------------------------------------------------------------- |
| **Aesthetics**     | Premium layout design       | Smooth slide-up drawer animation on mobile, HSL themed borders/badges                   |
| **Map Engine**     | Exclusive use of Leaflet.js | Zero external commercial APIs (e.g. Google Maps)                                        |
| **Responsiveness** | Mobile-First layout         | Adaptive design transitioning from a bottom drawer on mobile to a side panel on desktop |
| **Performance**    | Instant static filtering    | Latency under 50ms for client-side search/filter operations                             |

---

## 7. Folder Flow

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx            # Landing/Home page with interactive map and side panel
│   │   └── globals.css         # Project design system styles
│   └── components/
│       └── ui/
│           ├── map-viewer.tsx  # Map component wrap
│           └── site-drawer.tsx # Detailed view drawer
│   └── lib/
│       └── api.ts              # Frontend API client
```

---

## 8. Scope

**v1 — In Scope**:

- Design and build of the Next.js home page integrating the Leaflet.js interactive map.
- Side panel/bottom sheet component that listing sites, filterable by health category and search string.
- Detail drawer detailing physico-chemical parameters and IK signals.
- Direct database query calls to fetch sites, basins, and incidents.
- Implementation of the scrollable feed of sites/incidents beneath the map, incorporating the complex badge UI, status/location chips, and intervention warning banners.

**v1 — Explicitly Out of Scope**:

- Dynamic pollution reporting submission forms (only reporting visualizer maps are in scope).

---

## 9. Epic & Ballpark Estimation

| Component                    | Task Description                                                                                                                      | Complexity | Ballpark Estimate (Hours) | Assumptions                                           |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------- | ----------------------------------------------------- |
| **API Client Integration**   | Implement API hooks and queries for database fetching                                                                                 | Simple     | 3h                        | APIs are available and unauthenticated                |
| **GIS Map Component**        | Dynamic marker rendering, tooltips, custom icons, and scroll protection in Leaflet                                                    | Medium     | 8h                        | Leaflet is fully integrated                           |
| **Search & Filters**         | State hooks for status tags, search queries, database loading                                                                         | Simple     | 4h                        | Frontend search is instant                            |
| **Site List & Status Cards** | Scrollable feed of sites/incidents beneath the map, implementing complex badge UI, status/location chips, and action warning banners. | Medium     | 6h                        | Tailwind utility classes and premium styling elements |
| **Detail Drawer**            | Responsive bottom drawer displaying metrics and actions                                                                               | Medium     | 6h                        | Glassmorphism/visual styles apply                     |
| **QA / Verification**        | Viewport layout testing, functionality audit                                                                                          | Simple     | 3h                        | None                                                  |

---

## Exit Criterion

> This PRD must be approved by the user to proceed to LLD and implementation plan.
