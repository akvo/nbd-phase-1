# LLD — NBD Platform Landing Page

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Tech Lead / Winston (Architect) | Target Location: `docs/lld/landing_page_lld.md` | References: `docs/prd/landing_page_prd.md`
> Status: `Approved`

---

## 1. Overview & Scope

**Component / Module**:
Interactive landing page at `/` (`src/app/page.tsx`) mapping basins, monitoring sites, and pollution incidents with search, category filtering, and parameter drill-downs.

**PRD References**:
- FR-001 (Leaflet Map Render)
- FR-002 (Health Grade & Incident Markers)
- FR-003 (Status Toggle Tags)
- FR-004 (Dynamic Search Filtering)
- FR-005 (Figma Detail Cards)
- FR-006 (Static JSON Integration)

---

## 2. Component Design & Layout

The page utilizes a mobile-first responsive layout matching Figma specifications:
- **HeaderNavigation**: Logo, navigation action buttons (Log in, Sign up).
- **Map Container**: Fully fills the background/viewport height. Employs `next/dynamic` to load the Leaflet wrapper with `ssr: false`.
- **Search & Incident Panel**:
  - Appears as a sliding bottom drawer (`src/components/ui/site-drawer.tsx`) on mobile screens (< 768px).
  - Appears as a left-hand floating sidebar on desktop screens (>= 768px).
  - Contains the View Toggle switch (`All`, `Critical`, `At risk`, `Healthy`), search input field, and list of site cards.
- **Detailed Site View Card**:
  - Displays site identity (`NBD-MARA-002`), water health grade (`A`, `C`, `D`), progress bar showing aggregate health score %, and country badge.
  - Toggles a modal/drawer parameter breakdown (pH, DO, Temp, unit weights, and triggered management actions matching the API contract).

---

## 3. Data Schema & Mocking

A local static JSON file `public/data/mock_map_data.json` will replicate the public API responses:

### 3.1 JSON Format Overview
```json
{
  "basins": [
    {
      "basin_id": "MARA",
      "basin_name": "Mara Basin",
      "active_sites": 4,
      "basin_health_status": "YELLOW",
      "latest_incidents": []
    }
  ],
  "sites": [
    {
      "site_id": "NBD-MARA-001",
      "site_name": "Lower Mara Wetland",
      "country": "Tanzania",
      "basin": "Mara Basin",
      "current_health_class": "C",
      "current_score": 0.55,
      "last_updated": "2026-06-16T08:00:00Z",
      "coordinates": [34.5678, -1.2345],
      "community_signal": "Declining fish & water clarity",
      "progress_percent": 55,
      "is_approved": true,
      "is_ik_adjusted": true,
      "details": {
        "physico_chemical": {
          "group_score": 0.16,
          "ph": 7.8,
          "dissolved_oxygen": 4.77,
          "temperature": 23.25,
          "weights": { "ph": 0.3704, "dissolved_oxygen": 0.6297 }
        },
        "catchment_hydrological": { "group_score": 0.65 },
        "ecological": { "group_score": 0.45 },
        "ik_signal": {
          "encoded_signal_value": 0.67,
          "fish_abundance": "MODERATELY_DECLINED",
          "water_clarity": "MUCH_WORSE",
          "vegetation_cover": "PARTIALLY_LOST"
        },
        "management_actions": [
          { "label": "Silt Trap Install", "description": "Install vegetative filters along the edges of agricultural plots." },
          { "label": "Constructed Wetland Build", "description": "Encourage small-scale, man-made wetlands." }
        ]
      }
    }
  ],
  "incidents": [
    {
      "incident_type": "ANIMAL_KILLS",
      "coordinates": [34.5710, -1.2410],
      "report_source": "WhatsApp",
      "timestamp": "2026-06-15T09:00:00Z",
      "status": "Critical"
    }
  ]
}
```

---

## 4. Verification Plan

### Automated Tests
- Run `yarn test` to verify component compilation.
- Verify that dynamic search filtering updates both the DOM card listing and Leaflet marker layers correctly.

### Manual Verification
- Test UI layout on Chrome DevTools mobile view simulation (375px width) to verify bottom drawer drag handles and responsive text wrap.
- Verify status filtering behavior when selecting different toggle tags (`Healthy`, `Critical`, etc.).
