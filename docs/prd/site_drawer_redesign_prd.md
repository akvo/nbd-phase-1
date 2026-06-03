# PRD — Monitoring Site Details Drawer Redesign

* **Stage 2 of 3 — Documentation Hierarchy**
* **Owner**: Product Manager (John) / Business Analyst (Mary)
* **Initiative/Epic**: Wetland Monitoring Platform UI Enhancements
* **Status**: Proposed / Under Review

---

## I. Overview & Goal

### Problem Statement
The current monitoring site detail panel is functionally complete but lacks visual hierarchy, structured parameter classifications, and does not align with the premium Figma design system layout specifications for NBD.

### Core Metric
* **User Engagement & Readability**: Increase time spent viewing details and lower visual complexity score (assessed via user feedback).
* **Intervention Alignment**: Ensure 100% of generated management actions are clearly readable and match their warning severity levels.

---

## II. User Stories & Flows

### Personas
* **Wetland Analyst (Mary)**: Needs to view complex physico-chemical indicators, parameter group scores, and community FGD indicators in a structured grid and breakdown view.
* **Citizen Observer**: Wants to easily read community signals, country badges, and recommended actions without getting overwhelmed by raw data tables.

### User Journey
1. User clicks a site marker or card on the map.
2. The side drawer opens from the right (desktop) or slides up (mobile).
3. The header section prominently displays the site name, code, overall health letter grade (e.g. "C" in a status-colored circle), country pin, approval state, and adjust state.
4. A warning alert notice is displayed if the site's health is critical or at-risk.
5. Below this, the user sees a bold community signal quote, followed by structured grids:
   * **Key Metrics**: A 2x2 grid displaying pH, Water Temperature, Dissolved Oxygen, and Water Level (each with numeric value, status label, and color-coded status dot).
   * **Score Breakdown**: Interactive progress bars detailing physico-chemical, catchment/hydro, ecological, and governance indexes, plus pre- and post-adjustment composite scores.
   * **Raw Sampling Table**: A structured grid listing all physical metrics, units, and flags.
   * **FGD Session**: Cards showing indigenous knowledge indicators (fish abundance, water quality, vegetation).
   * **Interventions / Actions**: Clear panels detail necessary management responses.

---

## III. Requirements (Scope Guardrails)

### Must-Have
1. **Figma-Perfect Header**: Left side shows name and ID; right side shows absolute circular letter-grade badge (`A`, `B`, `C`, `D`, `E`). Badge colors must match the health status (green for healthy, orange for at risk, red for critical).
2. **Horizontal Status Badges**: Country badge with map-pin icon, approval badge (Pending/Approved), and IK-adjusted badge.
3. **Structured Parameter Grids**: Card metrics with status indicator dots (e.g., green dot for "Normal", orange dot for "Declining").
4. **Interactive Progress Bars**: Progress indicators representing sub-group indices.
5. **Raw Sampling Method Grid**: Table detailing parameter, value, unit, and flag columns.
6. **Triggered Actions list**: Intervention cards showing recommended management responses.

### Nice-to-Have
1. **Interactive Charts**: Interactive ECharts timeline showing past samplings when clicking on individual parameter cards.

### Out of Scope
1. **Direct Edit Mode**: Editing parameters inside the drawer (this is a view-only canvas).

---

## IV. Architecture Design & Data Flow

### Data Schema mapping
The details mapping directly reads from `public/data/mock_map_data.json` site payload:
* Header Letter Grade: `site.current_health_class`
* Badges: `site.country`, `site.is_approved`, `site.is_ik_adjusted`
* Physico-Chemical Cards: `site.details.physico_chemical` (pH, dissolved_oxygen, temperature, and new parameters like water level if added to mock data).
* Score Breakdown progress values.
* FGD session details: `site.details.ik_signal`.

---

## V. Acceptance Criteria

### User Acceptance Criteria (UAC)
* **UAC-1**: When opening the drawer, the header must show the site's letter grade badge inside a colored circle corresponding to its class.
* **UAC-2**: Key metrics (pH, DO, Temp, Water Level) must be presented in a clean grid where each card has a colored dot denoting state (green/orange/red).
* **UAC-3**: Score breakdown progress bars must render matching widths based on mock JSON values.

### Technical Acceptance Criteria (TAC)
* **TAC-1**: Responsive design: Side drawer behaves as a full-height right sidebar on desktop, and a sliding bottom drawer sheet on mobile screen sizes.
* **TAC-2**: Static data parsing must maintain 0ms latency.

---

## VI. Edge Cases & Errors
* **Missing Details**: If the selected site is missing physico-chemical or FGD fields, the drawer should display "No sampling data available" placeholder states without crashing.

---

## VII. Epic & Ballpark Estimation

| Component | Complexity | Ballpark Estimate |
|---|---|---|
| Frontend Layout Redesign (`site-drawer.tsx`) | Medium | 1.5 Days |
| CSS/Tailwind Layout Polish | Simple | 0.5 Days |
| Verification & Responsive testing | Simple | 0.5 Days |

---

## VIII. Rollout Plan
* Launch immediately as part of the frontend release.
