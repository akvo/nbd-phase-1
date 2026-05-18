# Solution Design: Citizen-Led Wetland Monitoring Platform
**Version:** 0.1 — Draft
**Date:** 2026-05-11
**Authors:** [names]
**Status:** Draft

---

## 1. Background & Context

This document describes the solution design for the data platform built under the assignment "Technical Support to Implement Citizen-Led Data Generation and Management Activities", commissioned by the Nile Basin Discourse (NBD).

NBD brings together civil society, academic institutions, and government bodies across the Nile Basin to promote equitable, sustainable management of shared water resources. Wetland degradation — driven by encroachment, pollution, and climate variability — is a priority concern. Decision-makers lack regular, ground-level data on these wetlands. Without it, enforcement windows close before degradation is documented.

This assignment addresses that gap. It establishes a citizen-led monitoring system at two transboundary pilot sites:

- **Mara Basin** — shared between Kenya and Tanzania;
- **Sio Basin** — shared between Kenya and Uganda;

This document describes the technical backbone of that system. The platform collects data submitted by community members, processes and validates it, and presents results to partners and decision-makers through a public-facing portal.

### Partner Organisations

| Organisation | Role |
|-------------|------|
| **Akvo Foundation** | Lead implementation; platform design, build, and data management |
| **Makerere University** (Uganda) | Academic partner; laboratory validation and quarterly shadow sampling |
| **University of Nairobi** (Kenya) | Academic partner; laboratory validation and quarterly shadow sampling |
| **UWASNET** | Uganda Water and Sanitation NGO Network; community engagement and CSO oversight |
| **KEWASNET** | Kenya Water and Sanitation Civil Society Network; community engagement and CSO oversight |
| **NBD Secretariat** | Strategic governance and coordination across Nile Basin countries |
| **National Discourse Forums (NDFs)** | Country-level governance |
| **TAFIRI** | Tanzania Fisheries Research Institute |

---

## 2. Problem Statement

Wetland managers and government authorities in the Nile Basin lack reliable, regular data on the health of transboundary wetlands. Formal monitoring is infrequent, expensive, and conducted by specialists who are rarely present on the ground.

Communities alongside the Mara and Sio-Siteko wetlands observe changes daily: unusual water colour, reduced fish catch, encroachment by farms, shifting flood patterns. This knowledge has no formal channel into decision-making systems.

This platform creates that channel. The design must respect three real-world constraints:

**Connectivity.** Many sampling sites have no mobile data coverage. The USSD channel requires only GSM voice coverage. KoboCollect stores data offline and syncs when connectivity is available.

**Device access.** Not all community members have smartphones. The pollution reporting workflow must be accessible from a basic feature phone.

**Digital literacy.** Wetland watchers and citizen scientists are not technical users. Every interaction must be guided, menu-driven, and completable without reading instructions.

---

## 3. Solution Overview

Akvo will build a mobile-first, citizen-centric data platform. It enables community-driven data collection, administration, and visualisation through familiar and accessible tools.

The platform is an MVP — a foundational system supporting the two pilot basins. It can be extended if NBD decides to add new basins, wetlands, or data layers during scale-up.

The platform has three layers: data collection, administration, and visualisation. Two purpose-built workflows feed into a single public-facing wetland data portal.

### Guiding Principles

**Open source first.** All custom components are built under open-source licences. KoboToolbox and all backend components are fully open source. Google Earth Engine, used for satellite data processing, has a generous free tier and a long-standing commitment to support non-commercial use.

**Low-connectivity resilience.** USSD runs on the GSM voice network only. KoboCollect captures data offline and syncs on reconnect.

**Community data ownership.** Data collected by citizens belongs to the communities and partner organisations. The platform is designed to facilitate handover to NBD without vendor lock-in.

**Interoperability.** Every monitoring site has a persistent, structured identifier (e.g. `NBD-MARA-001`). This identifier is embedded in the KoboCollect form, every admin layer record, every GEE pipeline output, every lab QA record, every FGD session record, and every portal API response. Any external dataset can join to platform data using this key alone — no custom field mapping is needed. Spatial layers are published as GeoJSON via documented API endpoints.

### Scope

- Pollution episode reporting via USSD and WhatsApp (Kenya)
- Monthly structured water quality sampling via KoboToolbox (Tanzania — Mara wetlands; Kenya and Uganda — Sio-Siteko)
- Admin layer for data cleaning and approval
- Wetland data portal with pollution incident map, health scores, and management actions
- Sentinel 1 & 2 / CHIRPS Earth Observation data integration via Google Earth Engine
- Laboratory QA data ingestion
- FGD session data capture for indigenous knowledge

### 3.1 Constraints & Hardware Requirements

#### User-side Devices and Roles

| Role | Description | Minimum device | Connectivity needed |
|------|-------------|---------------|---------------------|
| **Wetland watcher** | Community member reporting pollution episodes (Kenya) | Basic feature phone | GSM only (USSD) or smartphone with WhatsApp |
| **Citizen scientist** | Trained volunteer conducting monthly structured water quality sampling (Tanzania, Kenya, Uganda) | Android smartphone with KoboCollect | Intermittent data (offline-capable) |
| **CSO staff** | UWASNET / KEWASNET staff socialising the platform and entering FGD session data | Laptop or tablet | Reliable medium to low bandwidth internet |
| **Academic partner** | Makerere / UoN staff conducting shadow sampling and lab QA | Any browser-capable device | Reliable internet |
| **NBD / NDF / County / District officials** | Strategic and operational data users accessing the wetland data portal | Any browser-capable device | Reliable internet |

KoboCollect stores survey data on the device when there is no connectivity. It syncs automatically to the KoboToolbox server when the device reconnects.

Citizen scientists and wetland watchers are trained through a Train-the-Trainers (ToT) model. The platform must be fully usable from the first day of deployment by users who received training second-hand, without requiring IT support.

Handheld multi-parameter probes — used by citizen scientists to measure pH, temperature, and dissolved oxygen — are provided by the project. These are separate hardware items. The data they produce is entered through the KoboCollect form.

#### Hosting Infrastructure

- Hosting model: **Cloud-based, Dockerised**
- Production server: **8 GB RAM, 4-core CPU, 30 GB storage**
- Media attachments (photos, documents) stored in cloud object storage, separate from the VM

---

## 4. Architecture Design

### 4.1 System Layers

The platform has three layers. The two data collection workflows maintain separate pipelines through the admin layer, then converge at the output stage.

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA COLLECTION LAYER                       │
│                                                                 │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐   │
│  │   Pollution Reporting   │  │  Monthly Structured Sampling │   │
│  │   (Kenya)               │  │  (Tanzania, Kenya, Uganda)   │   │
│  │                         │  │                              │   │
│  │  USSD (feature phone)   │  │  KoboCollect (Android,       │   │
│  │  WhatsApp bot           │  │  offline-capable)            │   │
│  │  via Africa's Talking   │  │  via KoboToolbox             │   │
│  └───────────┬─────────────┘  └──────────────┬──────────────┘   │
└──────────────┼─────────────────────────────────┼────────────────┘
               │                                 │
               ▼                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ADMIN / PROCESSING LAYER                     │
│                                                                 │
│  Pollution pipeline         Sampling pipeline                   │
│  ┌─────────────────┐        ┌────────────────────────────────┐  │
│  │ Ingest → Clean  │        │ Ingest → Clean → Approve       │  │
│  │ → Approve       │        │ → Score & classify (auto)      │  │
│  └─────────────────┘        └────────────────────────────────┘  │
│                                                                 │
│  External data: Sentinel 1&2 + CHIRPS (via GEE), Lab QA        │
│  Indigenous knowledge: FGD session records (via admin form)    │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     WETLAND DATA PORTAL                         │
│                                                                 │
│  Pollution incident map  │  Health scores  │  Trend charts      │
│  Satellite overlays      │  Traffic light  │  Management actions│
│  Public: no login        │  Partners: SSO / email login         │
└─────────────────────────────────────────────────────────────────┘
```

**Data Collection Layer** — the citizen-facing interfaces. Wetland watchers submit pollution episodes via USSD or WhatsApp Business bot. Citizen scientists submit monthly structured sampling data via KoboCollect.

**Admin / Processing Layer** — the internal layer where staff clean and approve submissions. The pollution and sampling pipelines remain separate. Scoring is automated from approved data. External data (Sentinel 1 & 2, CHIRPS, lab QA results) and FGD session records are also ingested here.

**Wetland Data Portal Layer** — the public-facing output. The two pipelines converge in a single portal showing pollution incidents on an interactive map, wetland health scores, management actions, and satellite overlays. All views are accessible on mobile and can be exported as PDFs.

### 4.2 Pollution Episode Reporting (Kenya)

**Actors:** wetland watchers — community members who report pollution events as they occur.

**Incident types reported:** unusual water colour, smell, fish or other animal kills, storm events, changes in water levels.

Two parallel channels serve the same reporting flow:

#### Channel A — USSD (Feature Phone Users)

Feature phone users dial a dedicated short code and navigate a branching menu.

```
Wetland watcher dials short code
        │
        ▼
USSD branching menu presented
        │
        ├── Select incident type
        │   (water colour / smell / fish kill / storm / water level change)
        │
        ├── Select location
        │
        ▼
Report submitted to admin layer
```

The flow runs entirely over the GSM voice network. No mobile data, smartphone, or app installation required.

#### Channel B — WhatsApp Business Bot (Smartphone Users)

```
Wetland watcher opens WhatsApp
        │
        ▼
Menu-driven bot flow initiated
        │
        ├── Select incident type
        │
        ├── Select sub-county
        │
        └── Attach GPS-stamped photo or voice note (optional)
        │
        ▼
Report submitted to admin layer
```

WhatsApp users can attach photos and voice notes alongside their submission. Both channels use Africa's Talking as the telco gateway and feed into the same admin-layer pipeline.

#### Admin Layer — Pollution Pipeline

1. **Ingest** — report received from USSD or WhatsApp webhook; written to the admin layer
2. **Clean** — staff review for completeness; remove obviously erroneous entries
3. **Approve** — submission approved for publication to the wetland data portal
4. **Traffic light classification** — approved records contribute to basin health status (Green / Yellow / Red)

### 4.3 Monthly Structured Water Quality Sampling (Tanzania, Kenya, Uganda)

**Actors:** citizen scientists — trained community volunteers who visit designated sampling sites once per month.

**Collection tool:** KoboToolbox, accessed via the KoboCollect Android app. KoboToolbox is open source and has robust offline functionality.

All numeric fields in the KoboCollect form have min-max constraints configured at the form level. This catches obvious probe entry errors before the form is saved.

| Parameter | Minimum | Maximum |
|-----------|---------|---------|
| pH | 2 | 12 |
| Temperature | 0 °C | 50 °C |
| Dissolved Oxygen | 0 mg/L | 20 mg/L |
| Water level | 0 cm | NA |

Out-of-range entries prompt the citizen scientist to re-enter the value before the form can be submitted.

#### Data Collection Flow

```
Citizen scientist arrives at sampling site (e.g. NBD-MARA-001)
        │
        ▼
Opens KoboCollect on Android smartphone (offline mode)
        │
        ▼
Completes geo-referenced structured form:
  ├── Physico-chemical measurements
  │     (pH, Temperature, Dissolved Oxygen — handheld multi-parameter probe)
  ├── Ecological observations
  │     (papyrus density, invasive species, bird counts, fish CPUE)
  ├── Hydrological observations
  │     (water levels, flow patterns, flooding extent, encroachment)
  └── GPS-stamped photographs
        │
        ▼
Form saved locally on device (no connectivity required)
        │
        ▼
Connectivity available → KoboCollect syncs to KoboToolbox server
        │
        ▼
Submission received by KoboToolbox
        │
        ▼
KoboToolbox API → processing service pulls new submissions
        │
        ▼
Admin layer — sampling pipeline
```

#### Admin Layer — Sampling Pipeline

Same steps as the pollution pipeline: Ingest → Clean → Approve. After approval, the scoring engine computes parameter group scores and the composite score automatically.

#### Shadow Sampling and Lab QA Integration

Every quarter, academic partners (Makerere University / University of Nairobi) conduct shadow sampling at the same sites as citizen scientists. They collect independent samples and test for all citizen scientist parameters, plus Biochemical Oxygen Demand, Orthophosphate, Nitrate, and Mercury.

Shadow sampling results are compared against citizen scientist submissions to validate measurements and flag systematic discrepancies for retraining.

Lab QA results are ingested as a separate record type in the admin layer, linked to the site identifier and sampling period.

### 4.4 Admin Interface

The admin interface is the internal processing layer. It is a restricted section of the platform, accessible to authorised staff only. The admin interface and the public portal are part of the same application — admin routes are protected by role-based access control.

#### Roles

Two roles are defined. Admin is a strict superset of Reviewer.

| Role | Permissions |
|------|------------|
| **Reviewer** | Review and approve or reject pollution reports, sampling records, lab QA reports, and FGD session records |
| **Admin** | All Reviewer permissions plus: invite users and assign roles; create and manage monitoring sites; delete records |

#### Sidebar Navigation

Both roles see **Data** as the primary workspace item. Admins additionally see **User management** and **Site management** under a Management section. Reviewer accounts see these items but they are locked.

#### Data Screen

The Data screen is the central working view. All submitted records appear in a single filterable list. Three selectors narrow the list:

- **Form** — Pollution report · Sampling data · Lab QA report · FGD session
- **Status** — Pending approval · Approved
- **Basin** — Mara Basin · Sio-Siteko

The record count updates live as selectors change. A **Clear** control resets all three selectors.

Each row represents one submission. A Form chip (colour-coded by type) and a Basin / Site chip identify the record at a glance. Clicking a row expands it inline to show the full submission detail. The row collapses on a second click.

Actions available in the expanded view:

| Status | Reviewer actions | Admin additional actions |
|--------|-----------------|--------------------------|
| Pending approval | Approve · Reject · Edit | Delete |
| Approved | View | Edit · Delete |

For sampling data records, the expanded view shows the automated score and health class (A–E). These values are read-only — they are computed from submitted measurements.

#### Add New

A blue **+ Add New** button sits right-aligned in the filter bar. Clicking it opens a modal to select a form type and basin, then launches the corresponding webform.

Four form types are available:

**Pollution report** — basin-level; no specific site required.

**Sampling data** — the modal additionally prompts for the specific monitoring site.

**Lab QA report** — entry point for academic partners entering lab results. Links to the relevant sampling record and site.

**FGD session** — entry point for CSO staff entering structured indigenous knowledge data from Monthly Baraza sessions. The form captures:
- Date of Baraza
- Basin and associated sampling site
- Number of FGD participants
- Structured responses per dimension (dropdown):
  - Fish abundance change: Same or increased / Slightly declined / Moderately declined / Severely declined
  - Water clarity change: Same or clearer / Somewhat worse / Much worse
  - Vegetation cover change: Same or more / Partially lost / Severely lost
  - Pollution events reported: None / Occasional / Frequent
- Open notes (stored but not scored)
- Facilitator name

FGD records link to a basin and sampling period. The scoring pipeline reads the most recent FGD record for each site and period to compute the indigenous knowledge signal used in the fuzzy logic adjustment (see Section 5.6).

```
Monthly Baraza (FGD session)
        │
CSO staff enters FGD session record via Add New
        │
        ▼
Admin layer — FGD record
  site:          NBD-MARA-001
  period:        June 2026
  fish_decline:  moderately_declined  → 0.6
  clarity:       much_worse           → 1.0
  vegetation:    partially_lost       → 0.4
        │
        ▼
Scoring pipeline reads record
→ IK signal = average(0.6, 1.0, 0.4) = 0.67
→ fuzzy adjustment applied to composite score
```

Data added via Add New webforms is moved directly to Approved status.

#### User Management (Admin only)

Displays all platform users as cards showing name, email, organisation, and assigned role. Admins can invite new users by email and assign Admin or Reviewer roles. Users cannot self-register.

**Authentication:** the admin interface uses SSO via common identity providers (Google, Microsoft). No passwords are managed by the platform.

#### Site Management (Admin only)

Lists all registered monitoring sites in a table with columns for Site ID, name, country, basin, and coordinates. Admins can add new sites, edit site metadata, or disable a site (which hides it from the Add New form but retains its historical records). Site identifiers follow the format `NBD-MARA-001`.

Each site record supports attached documents. Supported formats: PDF, JPG, PNG (maximum 10 MB per file). Documents are stored in cloud object storage, linked to the site by Site ID. Attachments are visible to Admins and Reviewers in the expanded site view. They are not publicly visible on the portal.

Examples of attached documents: wetland management plans, baseline assessment reports, field notes, boundary maps.

---

### 4.5 Wetland Data Portal

The portal gives NBD Secretariat, NDFs, county and district officials, CSOs, academic partners, and communities access to collected data, derived health scores, and management actions.

**Key features:**
- **Pollution incident map** — geospatial display of reported pollution episodes by basin
- **Wetland health scores** per site, per time period
- Trend visualisation over time
- Satellite data overlays (vegetation indices, water surface extent, land use change)
- Mobile-friendly layout; exportable as PDF for offline use at Barazas and government meetings

**Data sources:** pollution episode outputs + monthly sampling outputs + external data (Section 4.7)

**Access:**
- Public view: health scores, pollution incident map, site-level detail, trend data — no login required
- Partner view: restricted data layers — SSO or email and password login; no self-registration; accounts created by Admin

**Data refresh:** weekly

**Tech stack:** Next.js (frontend), Leaflet.js (maps), ECharts (charts), FastAPI backend API, PostgreSQL database

### 4.6 Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Data collection — USSD | Africa's Talking | GSM-only; no smartphone or data required |
| Data collection — WhatsApp | WhatsApp Business bot (Africa's Talking) | Menu-driven; same gateway as USSD |
| Data collection — structured sampling | KoboToolbox | Open source; offline-capable; proven in field contexts |
| Satellite data processing | Google Earth Engine | Managed compute; free tier for non-commercial use; no infrastructure to maintain |
| Database | PostgreSQL + PostGIS | Open source; relational; robust geospatial support |
| Backend API | FastAPI (Python) | Open source; fast; auto-generates OpenAPI documentation |
| Frontend — admin and portal | Next.js | Open source; React-based; supports server-side rendering |
| Visualisation — charts | ECharts | Open source; performant for time-series and score display |
| Visualisation — maps | Leaflet.js | Open source; lightweight interactive maps |
| Infrastructure | Docker | Containerised; portable; supports cloud or in-country hosting |
| Codebase | GitHub | Version control; issue tracking; CI/CD via GitHub Actions |

All components are open-source licensed except the Africa's Talking API (commercial SaaS) and Google Earth Engine (free tier, non-commercial use).

The platform is designed so that NBD and its national partners can operate and maintain it independently after the pilot period.

### 4.7 External Data Integration

**Purpose:** augment citizen-collected ground-truth data with authoritative external datasets.

**Known sources — Phase 1:**

- **Sentinel 1 & 2** (Earth Observation) — vegetation indices, water surface extent, land use change
- **CHIRPS** — precipitation and climate data
- **Lab QA results** from academic partners — heavy metals, nutrients, biochemical oxygen demand, orthophosphate, nitrate, mercury

Sentinel 1 & 2 imagery and CHIRPS precipitation data are processed using Google Earth Engine (GEE). GEE scripts extract vegetation indices, water surface extent, and land use change indicators and export results as GeoJSON or GeoTIFF for ingestion into the platform database.

**Anticipated future sources:**
- Data from Earthwatch
- Additional EO datasets

**Integration pattern:**
- Sentinel 1 & 2 / CHIRPS: automated batch pipeline (scheduled jobs) pulling and processing data via GEE; results ingested as structured records
- Lab QA results: submitted by academic partners via the portal webform (Add New → Lab QA report)
- Format standards: GeoTIFF (EO data), CSV (lab results), REST API (future sources)
- Temporal alignment: monthly

**Data provenance:** every external dataset record carries source name, collection date, and version. This is displayed alongside derived scores in the portal.

---

## 5. Data Model

### 5.1 Parameters Collected

| Category | Parameters | Collected by |
|----------|-----------|--------------|
| Physico-chemical | pH, Temperature, Dissolved Oxygen | Citizen scientists (handheld multi-parameter probes) |
| Ecological | Fish Catch Per Unit Effort (CPUE) | Citizen scientists |
| Hydrological / catchment | Water levels/flow, Flooding extent | Citizen scientists + wetland watchers |
| Pollution episodes | Industrial/sewage discharge, Storm events, Overgrazing, Encroachment | Wetland watchers (USSD/WhatsApp) |
| Lab validation | Biochemical Oxygen Demand, Orthophosphate, Nitrate, Mercury, Heavy metals and nutrient loads (N/P) | Academic partners (shadow sampling) |
| Indigenous knowledge | Community observations captured through FGD sessions at Monthly Barazas | CSO staff (via admin FGD session form) |

### 5.2 Data Schema — Pollution Episode Reporting

*[Schema to be defined — fields, types, constraints, units, aligned with Annex 1 of inception report (citizen reporting form)]*

### 5.3 Data Schema — Monthly Structured Water Quality Sampling

*[Schema to be defined — aligned with KoboToolbox form design and Annex 5 QA/QC protocol]*

### 5.4 External Data Schema

*[Schema per external source type — how Sentinel 1&2 / CHIRPS / lab records join to citizen science records via site identifier and date]*

### 5.5 Site Identifiers

Persistent, structured site identifiers follow the format `NBD-MARA-001`, `NBD-SIO-001`, etc. Four sampling sites per wetland. The site ID must be consistent across all data layers.

The site ID is the primary key for interoperability. It is embedded in every layer of the platform:

```
KoboCollect form      →  site_id field (fixed, pre-loaded per device)
        │
        ▼
Admin layer record    →  site_id: NBD-MARA-001
        │
        ├──► GEE pipeline output    {"site_id": "NBD-MARA-001", "ndvi": 0.72}
        │
        ├──► Lab QA record          site_id: NBD-MARA-001, period: 2026-06
        │
        ├──► FGD session record     site_id: NBD-MARA-001, period: 2026-06
        │
        └──► Portal API response    GET /api/sites/NBD-MARA-001/scores
```

Any external dataset can join to platform data using the site ID alone. No custom field mapping is needed.

### 5.6 Wetland Health Scores

Health scores are calculated at the parameter level, aggregated into group means, and combined into a single composite score per site. The methodology follows Annex 2 (Wetland Health Report Card Template).

#### Health Classes

| Class | Label | Score range | Description |
|-------|-------|-------------|-------------|
| A | Very Good / Natural | 0.8 – 1.0 | Unmodified or natural; very high ecological integrity |
| B | Good / Slightly modified | 0.6 – 0.8 | Largely natural with few modifications; small loss of natural habitat |
| C | Moderate / Moderately modified | 0.4 – 0.6 | Moderate change in ecosystem processes and loss of natural habitats |
| D | Poor / Largely modified | 0.2 – 0.4 | Large change in ecosystem processes; serious loss of natural habitat and biota |
| E | Very Poor / Critically modified | 0.0 – 0.2 | Critical modifications; ecosystem processes completely altered |

#### Parameter Groups and Scoring

| Parameter group | Parameters scored |
|----------------|------------------|
| Physico-chemical | Water temperature, pH, Dissolved Oxygen (converted to Water Quality Index score) |
| Catchment and hydrological | % wetland converted to non-wetland use; ratio of natural inlets choked/diverted to total natural inlets |
| Ecological | % wetland area covered by invasive macrophytes; Fish Catch Per Unit Effort |

Each group is scored on a 0.0–1.0 scale. Group scores are averaged to produce the composite score.

#### Scoring Pipeline

```
Monthly sampling record (approved)
        │
        ▼
┌────────────────────────────────────────┐
│  Score each parameter group (0.0–1.0)  │
│                                        │
│  Physico-chemical  ──────────► 0.68    │
│  Catchment/hydro   ──────────► 0.58    │
│  Ecological        ──────────► 0.65    │
│                                        │
└──────────────────┬─────────────────────┘
                   │
                   ▼
         Composite = average = 0.638
                   │
     ┌─────────────┴──────────────┐
     │  FGD session IK signal     │
     │  fish: moderately declined │
     │  clarity: much worse       │
     │  vegetation: partially lost│
     │  encoded signal = 0.67     │
     └─────────────┬──────────────┘
                   │
                   ▼
       Fuzzy logic adjustment
       0.638 → 0.55
                   │
                   ▼
     ┌─────────────────────────────┐
     │  Health class: C (Moderate) │
     │  Traffic light: YELLOW      │
     │  Action: community response │
     └─────────────────────────────┘
```

#### Fuzzy Logic Adjustment

A composite score of 0.638 sits on the border between Yellow and Green. The number alone does not capture whether the wetland is degrading relative to its historical state. Indigenous knowledge from FGD sessions at Monthly Barazas provides that context as a soft signal.

**Step 1 — Encode the IK signal.**

FGD session records use structured dropdowns per dimension. Each response maps to a numeric score. The scores are averaged into a single IK signal (0.0 = no decline reported; 1.0 = severe decline reported).

| Dimension | FGD response | Encoded score |
|-----------|-------------|--------------|
| Fish abundance | Moderately declined | 0.6 |
| Water clarity | Much worse | 1.0 |
| Vegetation cover | Partially lost | 0.4 |
| **IK signal** | | **0.67** |

**Step 2 — Express inputs as fuzzy sets.**

Both inputs (composite score and IK signal) are assigned membership values across three fuzzy sets: low, medium, high. A score of 0.638 falls mainly in the "medium" set. An IK signal of 0.67 falls mainly in the "moderate" set.

**Step 3 — Apply if-then rules.**

Rules fire based on the combination of input fuzzy sets:

| Composite score | IK signal | Output |
|----------------|-----------|--------|
| High | None | High |
| High | Moderate | Medium |
| High | Strong | Medium |
| Medium | None | Medium |
| **Medium** | **Moderate** | **Low** ← fires |
| Medium | Strong | Low |
| Low | Any | Low |

**Step 4 — Defuzzify.**

The fired rule output is converted back to a single number using the centroid method.

**Result:** composite 0.638 → adjusted score **0.55** → traffic light **YELLOW** → community response triggered.

Without the FGD data, 0.638 would classify as Green. No action would be taken.

#### Traffic Light Classification

| Status | Score threshold | Action triggered |
|--------|----------------|-----------------|
| Green | > 0.6 | No immediate action required |
| Yellow | 0.4 – 0.6 | Local community response triggered |
| Red | 0 – 0.4 | Formal report submitted to NBD and relevant national/local government authority for enforcement |

#### Management Actions

Management actions are displayed publicly on the portal alongside the traffic light status for each site. Each action shows a short 3-word label as the primary display, with the full description available on expansion. Actions are defined per wetland by the NBD Secretariat and national partners and updated via the admin interface.

**Green — No action required.** The wetland is within acceptable health bounds. Monitoring continues at the regular monthly cadence.

**Yellow — Community response.** The following six actions are triggered:

- **Establishment of Silt Traps and Grass Strips** — Install vegetative filters along the edges of agricultural plots to catch sediment and nutrient runoff (phosphates/nitrates) before they reach the water.
- **Constructed Wetlands for Tertiary Treatment** — Encourage small-scale, man-made wetlands at the edge of settlement zones to naturally treat domestic greywater.
- **Promotion of Livelihoods** — Transition farmers in the buffer zone from high-input crops (like sugarcane or maize) to low-impact activities such as apiculture (beekeeping) or sustainable papyrus harvesting.
- **Riparian Re-vegetation** — Conduct targeted planting of indigenous species (e.g., Ficus sycomorus or Typha) in degraded patches to maintain the 0.4–0.6 ecological integrity score.
- **Establishment of Community Conservation Areas (CCAs)** — Designate no-catch zones or seasonal closures during fish spawning periods to allow stocks to replenish.
- **Introduction of Co-Management Groups** — Form Beach Management Units (BMUs) that are empowered to self-regulate gear sizes and monitor illegal fishing, reducing the burden on the central Authority.

**Red — Government escalation.** The following five actions are triggered and displayed on the portal:

| Label | Full action |
|-------|-------------|
| **Report effluent discharge** | Prompt reporting of effluent and sewage discharge incidences to the local unit of the Ministry of Environment and Water. Contact: XXXXXX |
| **Install interceptor STPs** | Set up interceptor sewage treatment plants to direct sewage to a sewage treatment plant or combined effluent treatment plant. A budget and timeline plan will be presented at the meeting on xx.xx.2026. |
| **Enforce buffer zones** | Prevent further wetland encroachment by enacting protected area and buffer zone regulations — including increasing buffer widths — under the Environment Management and Coordination Act. Violations to be reported immediately to the County Environment Committee. Contact: XXXXXX |
| **Upgrade fishing gear** | Fishermen to switch to lower mesh-size gillnets to improve catch per unit effort and reduce overfishing pressure on the wetland. |
| **Draft management plan** | The Environment Management Authority to prepare a draft wetland management plan for public review by December 2026. |

The portal shows the 3-word label on the site health card. Clicking it expands the full action text. All Red actions are publicly visible — no login required. The NBD Secretariat updates action text via the admin interface when escalation steps change.

---

## 6. Integration Design

| Integration | Direction | Protocol | Notes |
|-------------|-----------|---------|-------|
| Africa's Talking (USSD) | Inbound | HTTP webhook | Stateful session management required |
| Africa's Talking (WhatsApp Business bot) | Inbound/outbound | HTTP webhook | Menu-driven flow |
| KoboToolbox API | Outbound pull | REST/JSON | Scheduled daily sync |
| Wetland data portal data feed | Internal | FastAPI REST endpoints | Admin layer serves data to portal frontend via documented API |
| Sentinel 1 & 2 ingestion | Inbound (Monthly) | GEE export (GeoTIFF / GeoJSON) | Scheduled batch pipeline |
| CHIRPS ingestion | Inbound (Monthly) | GEE export (GeoJSON) | Batch, scheduled |
| Lab QA data ingestion | Inbound (Quarterly) | Portal webform (Add New → Lab QA report) | Reviewed before publication |

---

## 7. Security, Privacy & Data Governance

### 7.1 Citizen Data Privacy

All personal identifiable information is stripped before data is displayed on the public portal. Only aggregated data is displayed for pollution episodes.

### 7.2 Data Classification

| Tier | Examples | Who can access |
|------|----------|---------------|
| Public | Aggregated wetland health scores, pollution incident map, trend charts | Anyone |
| Private | Wetland watcher / citizen scientist PII, phone numbers, individual episode links | Admins only |

### 7.3 Access Control Model

| Role | Permissions |
|------|------------|
| Wetland watcher | Submit own pollution episode reports only |
| Citizen scientist | Submit own sampling records via KoboCollect only |
| Akvo , NBD| Full platform administration |
| Public | Read public tier only (portal) |

**Authentication:**
- Admin interface: SSO via common identity providers (Google, Microsoft). No passwords managed by the platform.
- Portal (partner access): email and password login.
- No self-registration. All accounts are created by an Admin via the invite flow.
- Public portal views require no login.

### 7.4 Data Ownership & Sovereignty

**Ownership.** NBD and the communities from which data is collected are the data owners. Akvo is the data processor — it operates the platform on behalf of NBD .

**Akvo's role.** Akvo has no right to use platform data for any purpose beyond operating the platform for this project. Akvo will not share, sell, or analyse the data for its own purposes.


### 7.5 Infrastructure Security

- Secrets management: no credentials in code or Docker images; use environment secrets or a secrets manager
- Encryption at rest: all PII and observation data
- Encryption in transit: TLS for all services
- Audit logging: all admin actions logged with actor, timestamp, and action

---

## 8. Deployment Architecture

### 8.1 Docker Services

The platform is fully Dockerised. Each major component runs as a separate Docker service.

### 8.2 Hosting

The platform is cloud-hosted. The architecture also supports local in-country server deployment should NBD choose to operate it independently post-pilot.

**Production server specification:** 8 GB RAM, 4-core CPU, 30 GB storage. Media attachments (photos, documents) are stored in cloud object storage, separate from the VM.

Three environments are maintained: development, staging, and production.

**Codebase.** Maintained on GitHub under the Akvo organisation. Continuous integration via GitHub Actions runs automated tests on every pull request. Deployments to staging and production are triggered via GitHub Actions.

### 8.4 Backup & Recovery

- Daily automated backups of all platform data
- Backup retention: 30 days

### 8.5 Monitoring & Alerting

- Infrastructure monitoring: server uptime, CPU and memory utilisation, disk usage
- Application monitoring: Africa's Talking webhook delivery failures, KoboToolbox sync errors, admin layer processing queue depth, portal availability
- Alerting: email notification to Akvo operations team on critical failures

---

## 9. Testing & Validation Strategy

### 9.1 Technical Testing

- Unit testing: core business logic (health score calculation, validation rules, traffic light classification, data transformations)
- Integration testing: USSD session flows, WhatsApp Business bot flows, KoboToolbox API sync, Sentinel 1 & 2 and CHIRPS ingestion pipelines
- End-to-end testing: full wetland watcher journey (pollution episode) and full citizen scientist journey (monthly sampling)

### 9.2 Field Validation

- Field pilot with actual wetland watchers and citizen scientists before full rollout; document failure modes
- Train-the-Trainers (ToT) workshop as a system validation checkpoint — system must be usable by ToT-trained users from day one

---

## 10. Project Timeline

| Milestone | Date |
|-----------|------|
| Design signoff | 22 May 2026 |
| Platform development | 25 May – 26 June 2026 |
| Training | End of June 2026 |
| Data collection begins | Early July 2026 |

---

*Appendices (to be added):*
- *A: Forms*
- *E: QA/QC protocol mapping (Annex 5 alignment)*
