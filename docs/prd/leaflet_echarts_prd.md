# PRD — Leaflet and ECharts Integration

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: PM + Design Lead | Target Location: `docs/prd/leaflet_echarts_prd.md`
> Status: `Draft`

---

## 1. Overview

**One-liner**:
Add interactive GIS mapping and data visualization charting capabilities to the NBD platform frontend by integrating Leaflet and Apache ECharts.

**What we are building**:
We are integrating two key packages into the Next.js 16/React 19 frontend stack:
1. **Leaflet & React-Leaflet**: To render spatial GIS layers, maps of the Nile Basin region, and site locations.
2. **Apache ECharts**: To render high-performance, interactive data visualization charts (line, bar, pie, and radar graphs).

**Why now**:
The Nile Basin Discourse (NBD) platform requires robust visualization of regional basin projects, member states, and project impact data. Integrating these standard libraries now establishes a stable visual framework for all upcoming analytical modules.

---

## 2. Goals & Success Metrics

| Goal | Success Metric | Baseline | Target | Owner |
|------|---------------|----------|--------|-------|
| Enable GIS mapping | Core map rendering capability inside dashboard widgets | None | 100% functional | PM |
| Enable charts | High-performance interactive chart widgets | None | 100% functional | PM |
| Maintain type-safety | Zero TypeScript compilation errors on import and instantiation | N/A | 0 errors | Dev |

**Anti-Goals**:
- Implementing full business dashboards in this setup phase (this PRD only covers dependency installation and baseline wrapper validation).
- Importing full GIS databases locally (maps will render from public tile servers/GeoJSON layers).

---

## 3. Target Users & Personas

| Persona | Job-to-be-Done | Key Frustration | v1 Priority |
|---------|---------------|-----------------|-------------|
| Regional Analyst | View and interact with geospatial maps and charts of basin projects | Clunky, static data visualization without spatial context | Primary |

---

## 4. User Stories

| ID | User Story | Priority (MoSCoW) | FR Reference |
|----|-----------|-------------------|--------------|
| US-001 | As a developer, I want map and chart packages installed and typed so that I can construct UI views quickly. | Must Have | FR-001, FR-002 |

---

## 5. Functional Requirements

| ID | Requirement | User Story | Priority |
|----|-------------|------------|----------|
| FR-001 | The system MUST support standard tile maps and custom markers using Leaflet v1.9.4 and React-Leaflet v5.0.0. | US-001 | Must Have |
| FR-002 | The system MUST support ECharts visualization rendering with responsive container sizing using ECharts v6.1.0. | US-001 | Must Have |

---

## 6. Non-Functional Requirements

| Category | Requirement | Metric |
|----------|-------------|--------|
| **Compatibility** | Packages must compile cleanly under React 19 and Next.js 16 | Zero build errors |
| **Performance** | Map & chart imports must be chunked and lazy-loaded dynamically to avoid bloating primary bundle | Lighthouse performance score >= 90 |

---

## 7. Dependency Specification

Based on compatibility checks with the active stack (**Next.js 16.2.6**, **React 19.0.0**, **TypeScript 5.x**), the following package specifications are recommended:

### 1. Leaflet (GIS Mapping)
*   **leaflet**: `^1.9.4` (Latest stable release)
*   **react-leaflet**: `^5.0.0` (Required for React 19 compatibility)
*   **@types/leaflet**: `^1.9.12` (TypeScript definitions)

### 2. Apache ECharts (Data Visualization)
*   **echarts**: `^6.1.0` (Latest stable release)
*   **echarts-for-react**: `^3.0.6` (Optional: May trigger minor peer dependency warnings under strict React 19 rules. Alternatively, a simple custom lightweight hook wrapper using `useRef` and `useEffect` is recommended for maximum stability and performance.)

---

## 8. Scope

**v1 — In Scope**:
- Installation of dependencies inside the frontend project.
- Setting up baseline mock configurations to verify import compilation.

**v1 — Explicitly Out of Scope**:
- Rendering complex GIS dashboards or database-connected analytics pipelines.

---

## 9. Exit Criterion

This PRD must be reviewed by the developer/user before executing the dependency installation step.
