# Response to NBD IT Team Comments on the Solution Design Document

**Document under review:** *NBD Solution Design Document* (`final-docs/NBD Solution design document.pdf`, v0.1 — 15 May 2026)
**Source assignment:** *Technical Support to Implement Citizen-Led Data Generation and Management Activities* (Inception Report, April 2026)
**Response prepared by:** Akvo Foundation
**Date:** 28 May 2026
**Status:** Draft — for discussion with NBD IT team

---

## How to read this response

Each NBD IT comment is quoted in italics, then answered in two blocks:

- **Position** — one sentence: what we are doing about it.
- **Ready-to-paste replacement** — the actual revised text for v0.2 of `design-docs/solution-design-technical.md`. Copy it directly.

---

## 1. Title

> *Title does not reflect the scope of the stated assignment "Technical Support to Implement Citizen-Led Data Generation and Management Activities". "Wetland Monitoring Platform," limits the perceived objective and overall system scope.*
>
> *Fear that the implementation framework might get confined to wetland monitoring alone, whereas the proposed solution encompasses broader "citizen-led data generation" – far beyond wetland monitoring data.*

**Position:** Agreed — we are renaming the document and adding a scope note.

**Ready-to-paste replacement — replaces the cover title block:**

> # Solution Design: Citizen-Led Data Generation & Management Platform
> ## Phase 1 / MVP — Wetland Monitoring (Mara and Sio-Siteko)
>
> **Version:** 0.2 — Draft  **Date:** TBD  **Authors:** Joy Ghosh  **Status:** Draft
>
> ---
>
> **Scope of this document.** This document describes a citizen-led data generation and management platform built under the NBD assignment *"Technical Support to Implement Citizen-Led Data Generation and Management Activities"*. Phase 1 deploys the platform with wetland monitoring as its first thematic use case, at two transboundary pilot sites (Mara and Sio-Siteko).
>
> The platform is designed so that adding a new thematic domain in a later phase — for example sanitation reporting, biodiversity surveys, or climate observations — is a development task, not a re-architecture. The reusable parts are the ingest channels (USSD, WhatsApp, KoboCollect), the admin moderation workflow, the portal shell, the identity and access model, and the external-data ingestion pattern. The domain-specific parts (the form, the scoring rule, the per-domain external sources) are added by a developer through a new form definition, new scoring code, and configuration — not through a no-code UI for NBD admins. A no-code domain builder is out of scope for Phase 1.

---

## 2. Background & Context

> *Section further limits the assignment to wetland degradation monitoring only.*
>
> *Fear is that NBD might end up with a wetland monitoring tool and not the intended Citizen-led data platform – This is an issue discussed before – more assurance is needed.*

**Position:** Agreed — Section 1 is rewritten below to position wetlands as the first instantiation of a generic platform.

**Ready-to-paste replacement — replaces all of Section 1:**

> ## 1. Background & Context
>
> This document describes the citizen-led data generation and management platform commissioned by the Nile Basin Discourse (NBD) under the assignment *"Technical Support to Implement Citizen-Led Data Generation and Management Activities"*.
>
> NBD brings together over 600 civil-society and academic organisations across the Nile Basin, organised under ten National Discourse Forums (NDFs). Ground-level data on basin health is fragmented across agencies, often outdated, and rarely reaches decision-makers in time to act. Citizens living around basin ecosystems observe ecological change daily, but that knowledge has no formal channel into management systems. This platform is the channel.
>
> **Phase 1 (MVP) — wetland monitoring at two pilot sites:**
>
> - **Mara Basin** — Kenya and Tanzania
> - **Sio-Siteko Basin** — Kenya and Uganda
>
> Wetlands are the first use case for three reasons. NBD has the strongest stakeholder pull at these sites. The degradation drivers (encroachment, pollution, climate variability) produce signals that citizen observations can capture. The enforcement window is short enough that a faster reporting channel produces visible programme outcomes inside the 12-month pilot.
>
> ### 1.1 What is generic vs. what is wetland-specific
>
> The thematic domain is configuration, not code. Wetland monitoring is one configured domain. Adding a new domain in Phase 2 means adding a form, a scoring rule set, optional new external data sources, and role assignments — nothing else.
>
> | Generic platform capability (built once, reused per domain) | Wetland-specific configuration (Phase 1) |
> | --- | --- |
> | USSD, WhatsApp, and KoboCollect ingest channels | Pollution-incident menu and the KoboCollect water-quality form |
> | Site-identifier schema (`NBD-<BASIN>-<NNN>`) | The 8 sampling sites in Mara and Sio-Siteko |
> | Admin moderation workflow (Ingest → Clean → Approve) | Reviewer / admin assignments for the two basins |
> | Scoring engine (parameter groups → composite → fuzzy adjustment → traffic light) | Wetland health parameters and the fuzzy rule set |
> | Public portal (map, scores, trends, management actions) | Wetland health classes A–E and per-wetland management actions |
> | External-data ingestion (Sentinel 1 & 2, CHIRPS, lab QA) | Sentinel indices chosen for wetland health (NDVI, water surface extent) |
> | Indigenous-knowledge capture (structured FGD form) | Mara / Sio-Siteko FGD dimensions (fish abundance, water clarity, vegetation cover) |
> | Role-based access (Admin / Reviewer / Partner / Public) | Per-basin role assignments |
>
> ### 1.2 Platform success indicators
>
> This document covers what the platform can control and measure. Programme-level outcomes — whether authorities act on alerts, whether management plans are adopted, whether partner organisations change behaviour — depend on stakeholder engagement, training, and governance processes that sit outside the platform. Those indicators are tracked by NBD through the programme results matrix and are not in scope here.
>
> The platform is considered successful if it reliably delivers:
>
> - Pollution reports ingested and published to the portal per basin per month.
> - Sampling submissions received per active site per month.
> - Wetland health classes (A–E) published per site per month.
> - Portal uptime and public API availability within the targets in §4.8.
> - Portal data accessible to the public without a login.

---

## 3. Problem Statement

> *Problem is clearly articulated, it would be good to provide references to evidence/statistics/records on the stated current reporting gaps, existing monitoring limitations, and comparison between current and the proposed systems.*

**Position:** Agreed — the evidence sits in the Inception Report and was not pulled into the SDD. Section 2 is rewritten below with citations and a current-vs-proposed table.

**Ready-to-paste replacement — replaces all of Section 2:**

> ## 2. Problem Statement
>
> Wetland managers and government authorities in the Nile Basin lack reliable, regular data on the health of transboundary wetlands. Formal monitoring is infrequent, expensive, and done by specialists who are rarely on the ground.
>
> The Mara Wetlands — 400–500 km² of papyrus-dominated floodplain spanning Kenya and Tanzania — have lost more than 100 km² to land conversion over the past decade. The drivers are upstream deforestation in the Mau Highlands, sedimentation, nutrient loading from intensive cultivation, and pollution from small-scale mining. Climate projections show ≈ 1.8 °C of warming and 10–12% more rainfall by 2050, raising both flood and drought risk for ~56,000 wetland-dependent residents.[^usaid2019]
>
> The Sio-Siteko Wetland Landscape — ~415 km² straddling Kenya and Uganda — is an Important Bird Area with over 520 bird species. It is degrading from unsustainable land use, charcoal-driven vegetation clearing, encroachment, sand harvesting, invasive species (*Mimosa pudica*, *Lantana camara*, *Pontederia crassipes*), and weak transboundary coordination.[^nelsap2020]
>
> Reconnaissance field visits under this assignment confirmed those pressures. They also documented that most observed pollution incidents are reported only verbally to local leaders, with no formal record reaching the relevant authority inside an actionable window.[^nbdrecon2026]
>
> Communities alongside the Mara and Sio-Siteko wetlands observe these changes daily: unusual water colour, reduced fish catch, encroachment by farms, shifting flood patterns. That knowledge has no formal channel into decision-making. This platform creates one.
>
> ### 2.1 Current state vs. proposed state
>
> | Dimension | Current state | Proposed state |
> | --- | --- | --- |
> | Pollution reporting cadence | Ad hoc; verbal to local leaders; rarely reaches authority in an actionable window | Same-day digital report via USSD or WhatsApp; visible on portal within 24 hours |
> | Wetland health assessment | Specialist field surveys, annual or rarer; results held in PDF | Monthly citizen sampling at fixed sites; quarterly academic shadow-validation; results published as live scores |
> | Data accessibility for decisions | Held by individual agencies, format varies, often unavailable | Public portal with health scores, trends, pollution-incident map, and downloadable PDF reports |
> | Indigenous knowledge | Captured informally at Monthly Barazas; not aggregated | Captured through a structured FGD form; aggregated into the IK signal that adjusts the composite health score |
> | Cross-border comparability | Each country uses its own format and indicators | Single site-identifier schema (`NBD-MARA-001`, `NBD-SIO-001`) and a unified parameter set across Kenya, Uganda, and Tanzania |
> | Cost per data point | High (specialist time + travel) | Low (incremental cost is a USSD session or a citizen scientist's monthly site visit) |
> | Time from observation to decision | Weeks to months | Hours (pollution) to one month (sampling cycle) |
>
> ### 2.2 Real-world constraints the design must respect
>
> **Connectivity.** Many sampling sites have no mobile data coverage. The USSD channel needs only GSM voice. KoboCollect stores data offline and syncs on reconnect.
>
> **Device access.** Not all community members have smartphones. Pollution reporting must work from a basic feature phone.
>
> **Digital literacy.** Citizen reporters and citizen scientists are not technical users. Every interaction must be guided, menu-driven, and completable without reading instructions.
>
> [^usaid2019]: USAID, *Vulnerability and Adaptation in the Mara River Basin* (Washington DC: USAID ATLAS Project, 2019), pp. 69–70.
> [^nelsap2020]: NBI/NELSAP, *Sio-Siteko Conservation Investment Plan* (Entebbe: NBI/NELSAP and GIZ on behalf of BMUKN under IKI, 2020), pp. 3–5.
> [^nbdrecon2026]: Reconnaissance and stakeholder-debriefing field notes, Akvo / NBD consortium, Mara and Sio-Siteko sites, March–April 2026 (consolidated in the Inception Report, April 2026, §2.3).

---

## 4. Section 3 — Solution Overview

### 4.1 MVP terminology

> *Would be good to state MVP in full – might be too technical for some audience.*

**Position:** Agreed — fixed on first mention.

**Ready-to-paste replacement — replaces the second paragraph of Section 3:**

> The platform is delivered as a **Minimum Viable Product (MVP)** — the smallest version of the platform that delivers value end-to-end across all user roles. A citizen can submit an observation, a reviewer can clean and approve it, the scoring engine turns it into a health status, and the public or a partner can see the result on the portal. Subsequent mentions in this document use the acronym.

### 4.2 System Context Diagram

> *Where is the System Context Diagram? Should clearly elaborate the major platform components, System boundaries, Data flows, External systems, External users etc. It should give a 360o view of the system immediately.*

**Position:** Agreed — this was the most important missing artefact in v0.1. Rendered version: [`diagrams/01-system-context.svg`](diagrams/01-system-context.svg). The ASCII block below is the textual specification it follows.

**Ready-to-paste replacement — new §3.1 inserted at the top of Section 3, before "Guiding Principles":**

> ### 3.1 System Context Diagram (C4 Level 1)
>
> Users, external systems, and the system boundary. Every data flow is annotated with its protocol. Rendered diagram: `diagrams/01-system-context.svg`.
>
> A C4 Level 2 Container Diagram follows in §4.1, breaking the system boundary into its Docker services.

### 4.3 Non-Functional Requirements

> *Non-functional system requirements are missing. You explain well what the system will do but not how well it must perform the tasks Issues of performance targets, availability targets, concurrent user assumptions, API response expectations, maximum acceptable downtime, sync latency, scalability thresholds, backup recovery objectives, technical assumptions and dependencies, etc*

**Position:** Agreed — new subsection added below. Targets are sized for the pilot workload (two basins, ~8 sampling sites, ~20 active citizen scientists, ~50 citizen reporters). We will re-baseline against real telemetry at the end of Year 1 before any scale-up.

**Ready-to-paste replacement — new subsection at the end of Section 3:**

> ### 3.x Non-Functional Requirements
>
> Targets are sized for the pilot workload: two basins, eight sampling sites, approximately 20 active citizen scientists, and approximately 50 citizen reporters. They will be re-baselined against real telemetry at the end of Year 1.
>
> **Availability.** Platform availability target is 99% per month (excludes pre-announced maintenance windows). The USSD and WhatsApp pipeline availability is bounded by the Africa's Talking SLA.
>
> **Performance.** Portal pages load within 2 seconds on a 3G connection. API responses for cached site and score data return within 800 ms. A pollution report submitted via USSD or WhatsApp is visible in the admin interface within 30 seconds. A KoboCollect submission is visible within 15 minutes of device reconnection.
>
> **Concurrent users.** The portal is designed for up to 200 simultaneous visitors, with capacity to handle short bursts beyond that through autoscaling. The admin interface serves a small team of up to 10 reviewers and administrators.
>
> **Recovery.** Recovery Point Objective (RPO): 24 hours — in the event of a failure, at most one day of data may need to be re-entered. Recovery Time Objective (RTO): 4 hours — the platform is restored from backup and redeployed from the GitHub repository within that window. Backups run daily and are retained for 30 days.
>
> **Localisation.** The interface is in English at MVP. The form and USSD menu structure supports translation; Swahili and Luganda are planned for a post-MVP release.
>
> **Key dependencies.** Africa's Talking must maintain the USSD short codes in each country. GEE must continue to offer the non-commercial free tier at pilot volume (licence risk is treated in §4.7.1). NBD must procure and distribute the handheld multi-parameter probes that citizen scientists use for water-quality sampling.

---

## 5. Section 3.1 — Constraints & Hardware Requirements

> *Device categories are listed but no mention of technical device standards: Which android/whatsapp versions are targeted(minimum), storage requirements for offline data and synchronization functioning, GPS accuracy requirements - how is GPS determined on feature phones??*

**Position:** Agreed — the expanded table below replaces the existing one. GPS on feature phones is the most important clarification: there is none, the USSD flow uses a sub-county menu lookup instead.

**Ready-to-paste replacement — replaces the "User-side Devices and Roles" table in §3.1:**

> #### User-side Devices and Roles
>
> | Role | Device & OS minimum | Connectivity | Location |
> | --- | --- | --- | --- |
> | **Citizen reporter — USSD** (Kenya) | Any GSM handset | GSM voice only; no data required | No device GPS. User picks sub-county from a menu; platform geo-codes it server-side. |
> | **Citizen reporter — WhatsApp** (Kenya) | Smartphone; Android 5.0+ / iOS 12+ | Intermittent mobile data | Photo EXIF GPS; user confirms on submission |
> | **Citizen scientist** (TZ · KE · UG) | Android 7.0+; KoboCollect v2024.x; ≥ 500 MB free storage | Intermittent data; offline-capable | Device GPS; form requires ≤ 10 m accuracy |
> | **CSO staff / Academic partner** | Laptop, tablet, or smartphone; any current browser | Medium-to-low bandwidth | n/a |
> | **NBD / NDF / officials / public** | Any browser-capable device; min 360 px screen width | Reliable internet | n/a |
>
> Citizen scientist submissions average 3–5 MB each (form + photos). KoboCollect queues submissions offline and syncs automatically on reconnect.

---

## 6. Section 4 — Architecture Design (diagrams)

> *System architecture is too basic. It only defines user levels and actions and not the entire system assembly. It relies heavily on narrative workflows without visual architecture diagrams. Diagrams for proposed Logical Architecture, Deployment Architecture, Data Flow Diagram, Security Boundary, and Integration Architecture Diagram*

**Position:** Strongly agreed — the v0.1 doc leaned on narrative because the diagram set was still being drafted at the v0.1 cut-off. v0.2 commits to the ten diagrams listed below. Rendered SVGs for Container, DFD Level 1, and Security Boundary are in `diagrams/02-container.svg`, `diagrams/03-data-flow.svg`, and `diagrams/04-security-zones.svg`. The ASCII blocks below are the textual specifications they follow.

**Ready-to-paste replacement — new subsection at the top of Section 4:**

> ### 4.0 Architecture Diagram Catalogue
>
> Source files live under `architecture/` and are re-rendered when the markdown is built.
>
> | # | Diagram | What it shows | Section |
> | --- | --- | --- | --- |
> | 1 | System Context (C4 Level 1) | Users, external systems, system boundary | §3.1 |
> | 2 | Container Diagram (C4 Level 2) | Deployable containers and their protocols | §4.1 |
> | 3 | Logical Architecture | Three layers; named modules; internal interfaces | §4.1 |
> | 4 | Component Diagram — Admin / Processing Layer (C4 L3) | Ingest workers, review queue, scoring engine, integration adapters | §4.4 |
> | 5 | Data Flow Diagram (Level 1) | Each citizen data source through ingest → store → portal, with trust boundaries | §4.x |
> | 6 | Sequence Diagrams | (a) USSD pollution report; (b) KoboCollect submission with offline sync; (c) GEE batch ingest; (d) shadow-sampling lab-QA reconciliation | §§4.2–4.3 |
> | 7 | Security Boundary / Trust Zone | Public vs. authenticated zones, PII storage zone, secrets boundary, network boundaries | §7 |
> | 8 | Integration Architecture | All external integration points with direction, protocol, frequency, auth method | §6 |
> | 9 | Deployment Diagram | Cloud VM(s), Docker services, object storage, backup target, DNS, TLS termination | §8 |
> | 10 | Entity-Relationship (Physical) | Tables, columns, types, FKs, indices | §5 |
>
> #### 4.0.1 Container Diagram (C4 Level 2)
>
> Rendered diagram: `diagrams/02-container.svg`.
>
> The Cloud account boundary contains the Docker VM and the cloud infrastructure we consume directly (object storage, backup snapshot). Third-party services sit outside that boundary — separate vendors, separate SLAs, separate accounts. The Docker VM runs **4 containers**: Next.js (Portal + Admin in one app), FastAPI (REST + webhooks + scoring engine), Postgres, and a single background-workers container for scheduled jobs. TLS termination is handled by the cloud provider's load balancer upstream of the VM and is not deployed as a separate container.
>
> #### 4.0.2 Data Flow Diagram (Level 1)
>
> Rendered diagram: `diagrams/03-data-flow.svg`.
>
> #### 4.0.3 Security Boundary / Trust Zone Diagram
>
> Rendered diagram: `diagrams/04-security-zones.svg`.

---

## 7. Section 4.5 — Wetland Data Portal

> *What are the accessibility standards/compliance, performance requirements, search/filter functionality, public API strategy,……??*

**Position:** Agreed — Section 4.5 is extended with the four subsections below.

**Ready-to-paste replacement — appends four new subsections to §4.5:**

> #### 4.5.1 Accessibility & Compliance
>
> The portal targets **WCAG 2.1 Level AA** conformance.
>
> - All map content has a parallel text or table view, so a screen-reader user reaches the same information without using the map.
> - Colour contrast is ≥ 4.5:1 for body text and ≥ 3:1 for the traffic-light status chips. Traffic-light status is always paired with a text label, never colour-only.
> - All interactive controls are reachable and operable by keyboard. The focus outline is preserved (not removed by CSS reset).
> - Semantic HTML headings (`h1`–`h3`) in document order; page `lang` set; every non-decorative image has `alt`.
> - Forms have labels (not just placeholders); error messages are tied to inputs via `aria-describedby`.
>
> Conformance is verified at end of build by automated audit (axe-core) plus a manual keyboard and screen-reader pass. Documented exceptions, if any, go in the release notes.
>
> #### 4.5.2 Performance
>
> Text content, health scores, and charts load quickly on low-bandwidth connections. Satellite raster overlay load times depend on connection quality and are not subject to a fixed target. Data shown on the portal is refreshed weekly.
>
> #### 4.5.3 Search and Filter
>
> Users can narrow the portal view by:
>
> - **Basin** — Mara · Sio-Siteko
> - **Site** — any of the eight `NBD-<BASIN>-<NNN>` sites
> - **Date range** — preset (last 30 days, last quarter, last year) or custom
> - **Health class** — A · B · C · D · E (multi-select)
> - **Pollution incident type** — water colour change, smell, fish or animal kill, water-level change (multi-select)
> - **Free-text search** — across site name and description
>
> Filter state is serialised into the URL query string so any view can be shared by link or bookmarked.
>
> #### 4.5.4 Public API Strategy
>
> The FastAPI backend auto-generates an OpenAPI specification. A documented subset of read-only endpoints is exposed publicly under a stable contract:
>
> - `GET /api/v1/sites` — list all sites with metadata and current health class.
> - `GET /api/v1/sites/{site_id}` — site detail including geometry.
> - `GET /api/v1/sites/{site_id}/scores` — historical health scores and traffic-light status.
> - `GET /api/v1/sites/{site_id}/external/{source}` — external data joined to the site (Sentinel NDVI, CHIRPS rainfall, etc.).
> - `GET /api/v1/incidents` — pollution incidents, aggregated, no PII.
>
> Partner endpoints (raw submissions, individual reporter contact, full audit log) sit behind SSO. They are not part of the public contract.
>
> The platform publishes:
>
> - **OpenAPI spec** at `/api/openapi.json` and human-readable docs at `/api/docs`.
> - **Data dictionary** documenting every field returned and its units.
> - **Versioning policy:** all URLs prefixed `/api/v1/`; the v1 contract is frozen at go-live; breaking changes ship under `/api/v2/`, with v1 supported for at least 12 months after v2 release.
> - **Fair-use rate limit:** 60 requests / minute / IP on public endpoints (HTTP 429 on excess); higher limits available to partners on request.
> - **Attribution and licence notice** on every API response payload, naming source(s) and applicable licence.

---

## 8. Section 4.6 — Technology Stack

> *The technologies are appropriate, but the document does not explain why each technology was selected, risks of using them, long-term maintenance implications etc.*
>
> *A technology comparison analysis with cost implications, support availability and skills requirements should be included. What are the alternatives and why do they not fit into this project. What if the chosen technology/service failed, was discontinued, becomes expensive to maintain…is there a fallback/backup?*

**Position:** Agreed — Section 4.6 is replaced with a per-component Technology Decision Record. Each one names alternatives, rationale, risks, maintenance and skills profile, cost, and the fallback path.

**Ready-to-paste replacement — replaces all of §4.6:**

> ### 4.6 Technology Stack — Decision Records
>
> None of the components below are experimental. They are the tools the team uses on citizen-data and environmental reporting platforms in this region, and the selection reflects both that experience and the constraints the requirements gathering and field reconnaissance surfaced: intermittent connectivity at monitoring sites, feature-phone access, limited digital literacy among citizen reporters, a tight cost ceiling, and a handover target of NBD staff operating the platform independently after the pilot. Each decision record below names the alternatives considered and why they were set aside.
>
> #### 4.6.1 Backend API — FastAPI (Python)
>
> The geospatial workload is already Python — GeoAlchemy2, Shapely, and rasterio for GEE result ingestion — so a Python backend keeps the stack consistent. Django REST Framework was considered and rejected: its conventions and bundled components suit larger, multi-domain applications, and this portal's scope does not justify that overhead. FastAPI is lighter, auto-generates the OpenAPI spec, and matches the team's established pattern for portals of this complexity. Python skills are widely available across the Nile Basin partner pool. The async-first style takes ramp-up for newcomers, but the community is mainstream and growing. The OpenAPI contract is the abstraction that makes the backend replaceable: re-implementing in Django + DRF or Flask + APISpec leaves the portal and mobile channels unchanged.
>
> #### 4.6.2 Frontend (Portal + Admin) — Next.js
>
> Next.js provides mature server-side rendering, good portal SEO, and fast mobile first-paint. A shared component library covers both the public portal and the admin interface. React skills are the most widely available frontend profile in East Africa, which matters for long-term maintainability. The frontend consumes the FastAPI REST API and holds no application logic, so if NBD needs to move away from Next.js later, the API contract is unchanged and the swap is a frontend-only exercise. The main risk is Vercel-driven release pace between major versions; we pin and upgrade on a deliberate release cadence. The platform is self-hosted in our Docker stack, not on Vercel, so there is no commercial dependency on Vercel services.
>
> #### 4.6.3 Database — PostgreSQL + PostGIS
>
> PostGIS is the de-facto standard for geospatial relational work — mature, supported by every major cloud, with deep tooling. MySQL with spatial extensions was considered but offers a thinner geospatial layer. MongoDB with geospatial indexes was considered but a relational model fits the structured tabular data better. Postgres skills are abundant; PostGIS training is widely available. At pilot scale, tuning complexity is not a concern. At scale-up, managed Postgres services on any major cloud run at roughly $50–150 per month.
>
> #### 4.6.4 Satellite Processing — Google Earth Engine
>
> The free non-commercial tier covers the pilot volume, and GEE provides ready-access to pre-computed Sentinel and CHIRPS catalogues with no raster-processing infrastructure to operate or maintain. Alternatives considered were Sentinel Hub (commercial, ~$500–2,000 per month for equivalent compute), a self-hosted Sentinel pipeline on Open Data Cube, and AWS Open Data Sentinel with GDAL. None match GEE's cost profile at pilot scale.
>
> Two risks are documented. First, licence tier: if NBD later monetises derived data, the non-commercial terms would require an upgrade to the GEE commercial licence. Second, discontinuation: low probability given Google's long-running public commitment, but non-zero. Both risks are mitigated by the architecture: every GEE script is exportable, and derived index values are stored in PostgreSQL, so historical results survive a tier transition regardless of what happens to GEE. The documented migration path is Sentinel Hub or a self-hosted Open Data Cube.
>
> #### 4.6.5 USSD & WhatsApp Gateway — Africa's Talking
>
> No other provider offers equivalent USSD and WhatsApp Business coverage in East Africa under a single API contract. Twilio has no USSD in Kenya. Infobip's regional coverage and support quality are weaker. Hover SDK delivers USSD via an Android app rather than the network, which is unusable on feature phones. Africa's Talking is East Africa-based and the dominant operator for exactly this use case. The primary risk is vendor lock-in on short-code allocation — short codes are tied to the AT account — and cost growth with submission volume. At pilot scale, cost is roughly $50–150 per month. If AT were discontinued, USSD could be sourced directly through a telco aggregator (slow to procure) and WhatsApp via the Meta Cloud API, now generally available.
>
> #### 4.6.6 Data Collection — KoboToolbox (cloud, free tier)
>
> KoboToolbox on the public cloud (`kf.kobotoolbox.org`) was chosen over self-hosting. Self-hosting was considered and rejected for the pilot: it adds container surface area not needed at pilot volume, and the free tier comfortably covers the expected submission and storage rate (~32 sampling submissions per month at ≤ 5 MB each). Alternatives considered were ODK Central (SaaS or self-hosted), SurveyCTO, and raw ODK. KoboToolbox is open-source, has strong offline behaviour through the KoboCollect Android app, and its UX is already familiar to many partner organisations in the region. No infrastructure for Akvo or NBD to maintain. The risks are the usual dependency on cloud availability and annual re-checking of free-tier limits against actual volume. If either limit were hit, self-hosting KoboToolbox on the same cluster is a documented path, and ODK Central is a second drop-in replacement sharing the XLSForm spec.
>
> #### 4.6.7 Visualisation — ECharts (charts) and Leaflet.js (maps)
>
> All mature charting libraries produce equivalent chart output; they differ in component API, configuration style, and default visual language. Swapping one for another is a frontend-only change with no impact on data or the API. ECharts is the team's working preference and the one the team delivers fastest in. Chart.js and Plotly were the alternatives considered. Leaflet is the lightest mature mapping option for our polygon and marker layers, with no proprietary tile dependency. Nothing in the portal's requirements points to a reason to use Mapbox GL or OpenLayers — both would add complexity without adding capability at this scope. Tile hosting costs are negligible via OSM-compatible providers. Both libraries are fully open-source.
>
> #### 4.6.8 Infrastructure — Docker
>
> Containerised services are portable between cloud environments and give a clean, reproducible deployment. Raw VM with systemd units was considered but offers no portability. Kubernetes was considered but imposes significant operational overhead not justified at pilot scale. Docker Compose is the right tool for a four-container application. If volume at scale-up requires Kubernetes, Compose-to-Kubernetes translation is a straightforward one-week task.
>
> #### 4.6.9 Codebase & CI/CD — GitHub + GitHub Actions
>
> GitHub provides the lowest friction for a multi-organisation contributor base, built-in CI, and mature dependency scanning. GitLab (SaaS or self-hosted) and a self-hosted Gitea + Jenkins combination were considered; both add operational overhead. Vendor lock-in is low — git history and Actions YAML are portable and the YAML conversion to GitLab CI is well documented.
>
> All components above are open-source licensed, except Africa's Talking (commercial SaaS) and Google Earth Engine (free non-commercial tier).
>
> The cost profile is deliberate. A citizen data platform should be cheap to run, particularly in its first phase — cost is a sustainability constraint, not a secondary consideration. Every component was chosen with an eye to minimising the recurring bill and keeping the platform operable without Akvo after handover.
>
> Replacing GEE or KoboToolbox with self-hosted alternatives is possible, but both would add infrastructure weight — a raster-processing pipeline or a managed form service — without improving Phase 1 outcomes. Those paths are documented as fallbacks and deferred to a later phase if the free-tier terms change or the volume outgrows them.
>
> NBD and its national partners can operate and maintain the platform independently after the pilot.

---

## 9. Section 4.7 — External Data Integration

> *Data from external sources – cost implications and user rights considering that some day NBD will monetize the data. What are the implications for cost and license violations.*

**Position:** Important point, not addressed in v0.1. The binding constraint on monetisation is the Google Earth Engine compute service licence, not the underlying open data. The licensing matrix below is the artefact NBD legal will use to decide.

> *An overview on error handling with external systems, data synchronization rules and data reconciliation monitoring and external system outages.*

**Position:** Agreed — added below.

**Ready-to-paste replacement — appends two new subsections to §4.7:**

> #### 4.7.1 Data Licensing and Downstream-Use Matrix
>
> | Source | Licence | Permits commercial / monetised re-use? | Attribution required? | Implication for NBD if/when monetising portal data |
> | --- | --- | --- | --- | --- |
> | Sentinel 1 & 2 (Copernicus) | Free, full and open | **Yes** — explicitly | Yes — attribute Copernicus / ESA | None — safe for commercial derivative products |
> | CHIRPS (UCSB Climate Hazards Center) | Public domain | **Yes** | Citation recommended | None |
> | Google Earth Engine (compute service) | Non-commercial tier free; **commercial use requires GEE Commercial licence** | **No** under the free tier | N/A | **Binding constraint.** NBD must upgrade to the GEE Commercial tier, or migrate the satellite-processing compute to Sentinel Hub or a self-hosted Open Data Cube, before monetising any GEE-derived product. The constraint is on the compute service, not on the underlying data. |
> | Lab QA results (Makerere / UoN) | Contributed under the assignment MoU | Defined in the MoU — currently silent on monetisation | Yes — partner credit | Amend the MoU before any monetisation, to clarify revenue sharing and authorise commercial-derivative use |
> | Earthwatch / WWF (future) | Per source — typically CC-BY-NC for citizen-data layers | Often **No** under the NC clause | Yes | Each future source needs a per-source legal check before ingest. A standing onboarding checklist is part of the operating procedure. |
>
> Every external dataset record carries a `provenance` field with source name, collection date, version, and licence string. The portal surfaces the licence string alongside derived scores so any downstream consumer sees the terms.
>
> #### 4.7.2 Integration Resilience and Reconciliation
>
> Each external integration has a documented failure-handling contract.
>
> - **Africa's Talking webhook (USSD + WhatsApp).** Delivery is at-least-once. Every report carries an idempotency key, so retries do not double-count. The webhook receiver returns HTTP 200 only after the message is durably persisted. AT retries failed deliveries with exponential backoff on its side. An alert fires if the webhook receiver is unavailable for > 5 minutes.
> - **KoboCollect → KoboToolbox → admin pull.** KoboCollect retries indefinitely on the device. The admin-layer pull worker runs every 10 minutes, uses a watermark cursor on `submission_time`, and writes to a dead-letter table on schema mismatch. The reviewer triages dead-letter entries.
> - **GEE batch.** Scheduled monthly. Processes Sentinel and CHIRPS data in GEE and writes derived index values to PostgreSQL as aggregated rows. Where a map overlay tile is generated, it is stored in Cloud Storage only if the value has changed from the prior month's export. On failure, re-run automatically up to 3 times with 1-hour backoff. Success criterion: expected database rows present for the period. Persistent failure alerts the Akvo operations team with the GEE error code.
> - **Lab QA.** Submitted manually by academic partners through the portal Add-New form. Automatic reconciliation runs against the citizen-scientist measurement for the same site and period. The record is flagged for review if the delta exceeds the configured per-parameter threshold (currently > 1 pH unit, > 2 mg/L dissolved oxygen, > 2 °C temperature).
> - **Outage policy.** The portal continues to serve last-known-good data with a visible "as of" timestamp. No external-integration outage takes the portal itself down.
>
> A **synchronisation status dashboard** (admin-only) displays the last successful run, last failed run, lag from upstream, and any dead-letter count for each integration.

---

## 10. Section 5 — Data Model

> *Sections 5.2, 5.3 and 5.4 are incomplete. Please include proposed visual Conceptual, Logical, and Physical data models. At this stage we should already have "complete" schemas. If they are already in another document, let us duplicate them here.*

**Position:** The v0.1 placeholders are a gap we own. This document limits itself to high-level design. The conceptual model below describes entities and relationships. Detailed schemas — logical data model (attributes, types, constraints) and physical model (PostgreSQL + PostGIS DDL) — will be developed during the platform build and shared with NBD as part of the Low-Level Design (LLD).

**Ready-to-paste replacement — replaces §§5.2, 5.3, 5.4 in full:**

> ### 5.2 Conceptual Data Model
>
> Rendered diagram: `diagrams/05-conceptual-erd.svg`.
>
> The platform organises data across three levels of geographic hierarchy: Basin, Wetland, and Site. Every data record attaches to one of these three levels, and that attachment determines which identifier it carries.
>
> **Basin** is the top-level container. Two basins are configured for Phase 1: Mara (Kenya/Tanzania) and Sio-Siteko (Kenya/Uganda). Pollution reports attach at basin level — citizen reporters select a sub-county, not a specific monitoring site. Basin-catchment external data (CHIRPS rainfall) also attaches here.
>
> **Wetland** sits within a Basin. FGD session records attach at wetland level — a Monthly Baraza is a wetland-community meeting, not a site-specific event. Wetland-polygon external data (Sentinel 1 & 2 indices) also attaches here, because Sentinel indices are computed over the wetland boundary polygon, not a point.
>
> **Site** (e.g. NBD-MARA-001) is the most specific level — a fixed point location visited monthly by citizen scientists. Sampling records, lab QA results, health scores, and management actions all attach to a site.
>
> The main data entities are:
>
> - **PollutionReport** — submitted by a Citizen (watcher role) via USSD or WhatsApp at basin level; records incident type, sub-county, and optional media.
> - **SamplingRecord** — submitted by a Citizen (scientist role) via KoboCollect at site level monthly; records physico-chemical, ecological, and hydrological measurements plus GPS location and photos.
> - **LabQAResult** — submitted by an academic partner quarterly at site level via the admin portal; records lab parameters (BOD, nitrate, mercury, orthophosphate, nutrient loads).
> - **FGDRecord** — submitted by CSO staff at wetland level monthly; captures structured indigenous knowledge from Baraza sessions across three dimensions: fish abundance, water clarity, and vegetation cover.
> - **ExternalDataPoint** — ingested on a monthly schedule; attaches at wetland-polygon scope (Sentinel 1 & 2) or basin-catchment scope (CHIRPS).
> - **HealthScore** — a derived entity computed per site per period from an approved SamplingRecord, adjusted by the FGD indigenous knowledge signal through the fuzzy logic pipeline (see §5.6). It does not exist until a sampling record is approved and scored.
> - **ManagementAction** — editorial content maintained by the NBD Secretariat; defined per site and per traffic light status; displayed publicly on the portal.
>
> Citizen and User are distinct. Citizens (watchers and scientists) are data submitters, identified by phone number (PII). Users are admin-layer staff (Admin and Reviewer roles), authenticated via SSO.
>
> Three interoperability keys tie the model together: site_id for sampling records and lab QA; wetland_id for FGD records and Sentinel data; basin_id for pollution reports and CHIRPS data. Any external dataset can join to platform data using the appropriate key without custom field mapping.
>
> ### 5.3 Logical and Physical Data Models
>
> Detailed schemas — attribute definitions, data types, validation constraints, and the PostgreSQL + PostGIS DDL — will be developed as part of the platform build and documented in a Low-Level Design (LLD). The LLD will be shared with NBD in due course. This document limits itself to high-level design.

---

## 11. Section 6 — Integration Design

> *Would be beneficial to add these 3 columns: Data Format, Frequency, failure handling, Cost projection/yr*

**Position:** Agreed — the table below adds all four columns.

**Ready-to-paste replacement — replaces the integration table in §6 in full:**

> ## 6. Integration Design
>
> | Integration | Direction | Protocol | Data format | Frequency | Failure handling | Cost projection / yr (pilot) | Notes |
> | --- | --- | --- | --- | --- | --- | --- | --- |
> | Africa's Talking USSD | Inbound | HTTP webhook | URL-encoded form params; XML response | Per session (event-driven) | AT-side retry with exponential backoff; idempotency key on report; alert if receiver unavailable > 5 min | ~$600–1,200 | Stateful session |
> | Africa's Talking WhatsApp Business bot | In/Out | HTTP webhook | JSON | Per message | Same as USSD; message dropped after 24h per WhatsApp policy | ~$400–800 | Menu-driven flow |
> | KoboToolbox cloud API | Outbound pull | REST / JSON | JSON | Every 10 minutes | Watermark cursor on `submission_time`; dead-letter table on schema mismatch | $0 (free tier) | Public KoboToolbox cloud (`kf.kobotoolbox.org`); free-tier limits reviewed annually |
> | Sentinel 1 & 2 via GEE | Inbound | GEE Python API | Aggregated index values (tabular) written to PostgreSQL; web-resolution tile to Cloud Storage only if value changed from prior month | Monthly | 3 retries × 1h backoff; alert on persistent failure | $0 (GEE free tier) | Licence-tier risk in §4.7.1 |
> | CHIRPS via GEE | Inbound | GEE Python API | Aggregated rainfall values (tabular) written to PostgreSQL | Monthly | Same as Sentinel | $0 | |
> | Lab QA results | Inbound | Portal webform | Structured form fields | Quarterly | Form-level validation; reviewer queue; auto-reconcile vs. citizen-scientist value | $0 | Submitted by academic partners |
> | Cloud object storage (media) | In/Out | Google Cloud Storage API | Binary | Per upload | Multipart upload; optional cross-region replication | ~$120–600 | ~$10–50 / month at pilot scale |
> | SSO (Google / Microsoft) | Inbound | OIDC | JWT | Per login | Fallback to email + password for portal partners | $0 | |
> | Backup target | Outbound | Cloud snapshot | Native | Daily | 30 days retention; restore tested quarterly | ~$60–240 | |
> | Wetland data portal data feed | Internal | FastAPI REST endpoints | JSON | On-demand (cached 1h at edge) | Standard HTTP error semantics; cached fallback | n/a | Admin layer serves data to portal frontend via documented API |
>
> Cost projections are pilot-scale order-of-magnitude only. We will re-baseline at the end of pilot Year 1 with actual telemetry and re-project for any scale-up scenarios.

---

## 12. Section 7 — Security, Privacy & Data Governance

> *Need to see technical threat analysis - enhance security policies, incident response plans, and a compliance framework for legal readiness.*

**Position:** The previous draft was calibrated for an enterprise system with a dedicated security team. This is a public citizen data portal with a small PII surface and a small operational team. The controls below are proportionate to that reality.

**Ready-to-paste replacement — replaces §§7.6, 7.7, 7.8:**

> ### 7.6 Security Controls
>
> The platform has two trust levels: public and admin. The security design follows from that split.
>
> **Public tier.** The portal serves aggregated health scores, pollution incidents, and satellite overlays with no login required. No PII appears in any public endpoint — phone numbers are never stored in or returned by the public API. HTTPS is terminated at the GCP load balancer. Rate limiting is applied at the load balancer (configurable, default 60 requests / minute / IP). No additional controls are needed beyond standard GCP network defaults.
>
> **Admin tier.** The admin interface and FastAPI privileged endpoints are protected by Google SSO. Staff log in with their existing Google accounts — the platform manages no passwords. Two roles are defined: Reviewer and Admin (see §4.4). Every approve, reject, edit, and delete action is written to an audit log with the actor's identity and a timestamp. Accounts cannot be self-created; all invitations go through the Admin role.
>
> **PII surface.** The only personal data the platform holds is the phone number of each citizen reporter and citizen scientist. Phone numbers are stored in the admin-tier database only. They are never returned by the public API, never included in portal displays, and never exported in any aggregated dataset. Deleting a citizen record removes the phone number while preserving the anonymised submission data.
>
> **Secrets.** API keys (Africa's Talking, GEE) and database credentials are stored in GCP Secret Manager and injected at container start. No credentials appear in code, Docker images, or files committed to the repository.
>
> **Media files.** Photos from KoboCollect submissions are stored in a private Google Cloud Storage bucket. Where satellite-derived map tiles are stored (web-resolution overlays only, generated when values change), they go to the same bucket. All access is via signed URLs with a 15-minute TTL. The bucket has no public access policy.
>
> **TLS.** All traffic — public portal, admin interface, USSD/WhatsApp webhooks, API calls to external services — is encrypted in transit via HTTPS. Internal container-to-container traffic runs on the Docker overlay network and is not externally reachable.
>
> ### 7.7 Incident Handling
>
> This is a small platform operated by a small team. The procedure is proportionate.
>
> **Platform down or data incorrect.** The Akvo operations contact investigates and resolves. GCP monitoring sends email alerts to the operations team on container failures, high error rates, and backup failures. NBD is notified if an outage exceeds 4 hours or if data integrity is affected.
>
> **Personal data exposed outside the admin tier.** Akvo notifies NBD immediately. NBD notifies the relevant supervisory authority within 72 hours per the applicable data protection law. Affected individuals are informed.
>
> After any significant incident, the Akvo operations team documents what happened and what changed. The note is shared with NBD.
>
> ### 7.8 Data Protection
>
> Citizen reporters and citizen scientists are residents of Kenya, Uganda, and Tanzania. The applicable laws are the Kenya Data Protection Act 2019, the Uganda Data Protection and Privacy Act 2019, and the Tanzania Personal Data Protection Act 2022. NBD is the data controller. Akvo is the data processor. A Data Processing Agreement between NBD and Akvo is signed before the platform goes live.
>
> The platform collects one category of personal data: phone numbers. They are used solely to identify the submitter and send automated acknowledgements. They are not shared with third parties and not used for any purpose beyond operating the platform.
>
> Citizen scientists give written consent at enrolment. Citizen reporters submitting via USSD or WhatsApp receive a one-line consent notice at the start of the menu flow.
>
> GCP has no region in East Africa. The default hosting region is `africa-south1` (Johannesburg) — the only GCP region on the continent, which keeps data within Africa and satisfies the data-residency intent of the applicable laws. Latency to East Africa from Johannesburg is acceptable for a web portal. The final hosting region is confirmed with NBD before go-live.

---

## 13. Section 8 — Deployment Architecture

> *The proposed infrastructure specifications seem undersized for production GIS data growth, image storage, and scale-up.*
>
> *Explicitly document the sizing assumptions and workload model behind the hosting infrastructure specifications. Without that, the hardware section reads as arbitrary and reviewers will immediately ask how the 8 GB / 4-core / 30 GB figures were derived. Speak to operational resilience and smooth but cost-effective scaling after pilot time.*

**Position:** Partly agreed — the v0.1 spec lacked its derivation. The replacement below adds the workload model, the sizing rationale, and the storage principle. The spec is a starting baseline, not a fixed ceiling; it is adjusted from observed usage at the end of Year 1.

**Ready-to-paste replacement — appends three new subsections to §8.2 and revises the production-server line:**

> #### 8.2.1 Workload Model (Pilot Year 1)
>
> | Driver | Value | Source |
> | --- | --- | --- |
> | Active sampling sites | 8 (4 Mara, 4 Sio-Siteko) | Inception Report |
> | Active citizen scientists | ~20 | Inception Report |
> | Active citizen reporters | ~50 | Inception Report |
> | Sampling submissions / month | ~32 (8 sites × ~4 visits) | Monthly cadence per site |
> | Sampling submission size | ~400 KB (form + 4 photos at ~100 KB each) | KoboCollect and WhatsApp compress photos at source |
> | Pollution reports / month | ~100–300 | Estimate; calibrated at end of Q1 |
> | Portal monthly visitors | ~500–2,000 | Estimate; bursty around events |
>
> Re-baselined at the end of Year 1 from actual telemetry.
>
> #### 8.2.2 Sizing Rationale
>
> The four Docker services — Next.js, FastAPI, PostgreSQL + PostGIS, and background workers — together require approximately 2.5 GB RAM and 2 vCPU at idle. The 8 GB / 4-core VM provides comfortable headroom for portal traffic bursts and the monthly GEE batch ingest without requiring autoscaling infrastructure at pilot scale. Photos are stored in cloud object storage separately and are not counted against the VM.
>
> Final resource limits are set at deployment time and adjusted from observed usage. A sizing review takes place at the end of Year 1 before any scale-up or handover decision.
>
> #### 8.2.3 Resilience and Scaling
>
> **Resilience.** Docker restarts failed containers automatically. If the VM itself fails, the platform is restored from the daily backup and redeployed from GitHub — target recovery within 4 hours (RTO). No data beyond the previous day's backup is lost (RPO 24 h).
>
> **Scaling after the pilot.** The 8 GB / 4-core spec is the starting point, not the ceiling. If the Year 1 telemetry review shows sustained resource pressure, the next step is upsizing the VM — a cheap, reversible change with no code changes required. If traffic grows beyond what a single VM handles, Docker Compose translates to Kubernetes with about a week's work. Cost scales with actual usage, not speculatively.
>
> #### 8.2.4 Storage
>
> The dominant storage item is photos from KoboCollect and WhatsApp submissions. Satellite-derived index values (Sentinel, CHIRPS) are written to PostgreSQL as aggregated rows — they produce negligible file storage. Where map overlay rasters are stored for the portal, they are kept at display resolution only — the resolution needed to render responsive portal tiles, not full satellite resolution.
>
> Year 1 projection: **~1 GB** in cloud object storage. KoboCollect and WhatsApp compress photos at source (~100–200 KB each); at 32 sampling submissions and ~150 WhatsApp reports per month with photos, total photo storage is roughly 1 GB by end of Year 1. Map overlay rasters at display resolution add a few MB. The VM's 30 GB disk covers the operating system, Docker images, and the live database only. Database backups go to cloud object storage separately — storing them on the same disk as the live data would defeat the purpose of a backup.
>
> Daily automated backups cover the database (RPO 24 h, 30 days retention). RTO target is 4 hours — restore from backup and redeploy from GitHub. Backup restores are tested quarterly.

---

## Summary — change-set for SDD v0.2

The paragraphs above are the editing source for v0.2. The full change-set:

1. Document re-titled; new scope paragraph on cover (§1).
2. Section 1 rewritten with the generic-vs-wetland-specific table and the success indicators.
3. Section 2 rewritten with citations and the current-vs-proposed table.
4. Section 3: MVP expanded on first mention; System Context Diagram (C4 L1) added at §3.1; NFR subsection added at §3.x.
5. Section 3.1 device table replaced with the version specifying OS, GPS handling, and sync sizing.
6. Section 4: diagram catalogue (§4.0) added, with Container, DFD L1, and Security Boundary diagrams included.
7. Section 4.5 extended with WCAG 2.1 AA, performance, search/filter, and public API subsections.
8. Section 4.6 replaced with the Technology Decision Records.
9. Section 4.7: licensing matrix (§4.7.1) and integration resilience (§4.7.2) added.
10. Sections 5.2, 5.3, 5.4 replaced with full Conceptual, Logical, and Physical data models (including DDL).
11. Section 6 integration table extended with Data Format, Frequency, Failure Handling, and Cost columns.
12. Section 7: STRIDE threat model (§7.6), incident response plan (§7.7), and compliance framework (§7.8) added.
13. Section 8: workload model, sizing derivation, object-storage clarification, scale-up path, and resilience added.

Edits land on `design-docs/solution-design-technical.md` and re-export to `final-docs/NBD Solution design document v0.2.pdf`.
