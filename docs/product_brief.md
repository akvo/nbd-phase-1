# Product Brief — NBD Citizen-Led Wetland Monitoring Platform

> **Stage 1 of 3 — Documentation Hierarchy**
> Owner: PM / Product Lead | Target Location: `docs/product_brief.md`
> Status: `Approved`
> Approved by: NBD Stakeholders, June 2026

---

## 1. Project Foundation and Objectives

The primary mission of the platform is to provide a formal channel for daily community observations of ecological changes to reach decision-making systems, ensuring the equitable and sustainable management of shared water resources in the Nile Basin.

### 1.1 Pilot Context

| Pilot Basin | Participating Countries |
| :--- | :--- |
| **Mara Basin** | Kenya and Tanzania |
| **Sio-Siteko Basin** | Kenya and Uganda |

### 1.1.2 Spatial Infrastructure Hierarchy

The platform organizes environmental monitoring, qualitative indigenous reports, and quantitative sampling records across a three-tier geographic hierarchy:
* **Basin**: The primary watershed boundary (e.g., Mara Basin, Sio-Siteko Basin), represented as PostGIS `MultiPolygon` geometries.
* **Wetland**: Distinct wetland regions (e.g., Mara Floodplain) contained within a Basin, represented as PostGIS `Polygon` geometries.
* **Site**: Fixed physical monitoring stations (e.g., Lower Mara Bridge point) contained within a Wetland, represented as PostGIS `Point` geometries.

### 1.2 Architectural Vision

This deployment represents Phase 1 of a broader digital strategy. The architecture mandates a **reusable shell design**; while the initial forms and scoring rules are wetland-specific, the core ingest channels, moderation workflows, and identity models are domain-agnostic to support future thematic scaling.

### 1.3 Success Indicators

The platform shall be considered successful if it reliably delivers the following:
1. Pollution reports ingested and published to the portal per basin per month.
2. Sampling submissions received per active site per month.
3. Wetland health classes (A–E) published per site per month.
4. Portal uptime and public API availability at a **99% target**.
5. Portal data accessible to the public without a login.

---

## 2. Problem Statement: Current State vs. Proposed Solution

### 2.1 The Data Gap (User Pain Point)
Wetland managers currently operate with restricted visibility. Formal monitoring is infrequent, expensive, and conducted by specialists who are rarely present during ephemeral pollution events. Critical community observations—such as unusual water colour or fish kills—are typically shared only verbally with local leaders, failing to reach authorities within an actionable window. Furthermore, existing data is often siloed in static PDFs, rendering it inaccessible for real-time decision-making.

### 2.2 Strategic Shift

| Dimension | Current State | Proposed State |
| :--- | :--- | :--- |
| **Pollution Reporting** | Ad hoc; verbal/informal; rarely reaches authority in an actionable window. | Same-day digital report via USSD or WhatsApp; visible on public portal. |
| **Wetland Health Assessment** | Specialist surveys, annual or rarer; results siloed in PDFs. | Monthly citizen sampling at fixed sites; quarterly academic validation; results published as live scores. |
| **Data Accessibility** | Held by individual agencies; format varies; data is often unavailable. | Live Public Portal with health scores, trends, incident maps, and downloadable reports. |
| **Indigenous Knowledge** | Captured informally/verbally at Monthly Barazas; not aggregated. | Captured through a Structured FGD form; aggregated into an IK signal to adjust health scores. |

---

## 3. Strict Project Boundaries (Product Scope)

### 3.1 In-Scope Features
* **Pollution Reporting (Kenya)**: Dual-channel reporting via USSD (feature phones) and WhatsApp (smartphones).
* **Structured Sampling**: Monthly data collection via KoboCollect for physico-chemical, ecological, and hydrological parameters.
* **Admin Moderation Workflow**: A four-step internal pipeline: Ingest, Clean, Approve, and Score.
* **Public Portal**: A Next.js-based web interface featuring health scores (A–E), interactive incident maps, and trend charts.
* **Fuzzy Logic Integration**: Use of Indigenous Knowledge (IK) signals to adjust composite health scores.
* **Satellite Data Ingestion**: Integration of Sentinel 1 & 2 and CHIRPS precipitation data via Google Earth Engine.

### 3.2 Strictly Prohibited
* **No Self-Registration**: All accounts must be created by an Admin via invite.
* **No Password Management for Internal Staff**: Authentication must rely solely on SSO (Google/Microsoft) to eliminate the security overhead of password rotation and local credential storage.
* **No PII Exposure**: Phone numbers must remain restricted to the admin tier and shall never reach public endpoints.
* **No Heavy Commercial Map Engines**: The architecture mandates the use of Leaflet.js to avoid proprietary vendor lock-in and the significant tile-loading costs associated with Mapbox.

---

## 4. Target Audience & Access Model

### 4.1 Actor Matrix

| Role | Device Requirement | Connectivity Level | Description / Primary Goal |
| :--- | :--- | :--- | :--- |
| **Citizen Reporter** | Feature phone / Smartphone | GSM voice or Intermittent data | Report pollution events and anomalous environmental conditions quickly. |
| **Citizen Scientist** | Android 7.0+ Smartphone | Offline-first (Sync on reconnect) | Conduct monthly technical water quality and ecological sampling at fixed sites. |
| **CSO Staff (Reviewer)** | Laptop or Tablet | Medium bandwidth | Capture qualitative community feedback (FGD entry), moderate and approve records. |
| **Academic Partner** | Laptop or Tablet | Reliable internet | Conduct quarterly shadow sampling and professional laboratory QA testing. |
| **Admin** | Laptop or Tablet | Reliable internet | Full Reviewer permissions plus user management, site creation, and record deletion. |

### 4.2 Admin Permissions
* **Reviewer**: Responsible for the data pipeline (Clean/Approve records).
* **Admin**: Strict superset of Reviewer. Manages users, invites, site management, and record deletion.

---

## 5. Strategic Alignment

* **OKR / Business Goal**: Facilitate critical cooperation between civil society, academia, and government bodies to ensure the sustainable management of shared water resources in the Nile Basin.
* **Product Vision Fit**: This platform acts as a channel that converts local community observations into actionable, context-aware environmental intelligence, bridging the gap between formal science and indigenous knowledge.
* **Priority Justification**: Local observation provides high-frequency, ground-level data that documents degradation in real-time, allowing action before critical ecological tipping points are passed.

---

## 6. The Technology Stack

### 6.1 Component Specification

| Component | Chosen Technology | Rationale |
| :--- | :--- | :--- |
| **Frontend** | Next.js | Fast mobile first-paint; React skills are widely available in East Africa. |
| **Backend API** | FastAPI (Python) | Lightweight; native support for GeoAlchemy2 and Shapely for geospatial workloads. |
| **Database** | PostgreSQL + PostGIS | De-facto standard for geospatial relational data. |
| **Mapping** | Leaflet.js | Open-source; avoids proprietary tile-loading costs and vendor lock-in. |
| **Visualisation** | ECharts | Efficient rendering of trends and health scores. |
| **Infrastructure** | Docker / Compose | Ensures portable, reproducible, and clean deployments. |
| **CI/CD** | GitHub Actions | Automated testing and deployment pipeline. |
| **Secrets Management** | GCP Secret Manager | Centralized, secure injection of API keys and credentials. |
| **Telco Gateway** | Africa’s Talking | Dominant East African operator for USSD and WhatsApp API. |
| **External Compute** | Google Earth Engine | Pre-computed satellite catalogues with a generous non-commercial tier. |

### 6.2 Open Source Commitment
All custom components are built under open-source licenses. Excepting Africa's Talking and Google Earth Engine, the stack is fully open-source to ensure sustainability and handover.

---

## 7. Data Collection and Processing Workflows

### 7.1 Pollution Pipeline
The platform utilizes a dual-channel approach for Kenya-based reporting:
* **USSD**: For feature phone users dialing the short code (`*123#`) over GSM networks.
* **WhatsApp**: For smartphone users, allowing for photo and voice note attachments.
* **Incident Types**: Users report water colour changes, bad smells, animal kills, and water level extremes (High Flow / Low Flow).

### 7.2 Monthly Sampling Pipeline
Citizen scientists use KoboCollect for offline-first data entry. The system enforces the following constraints:
* **Physico-chemical**: pH (2–10), Temperature (5–50 °C), Dissolved Oxygen (0.5–35 mg/L).
* **Spatial Accuracy**: The system mandates a GPS accuracy of $\le 20\text{m}$.

### 7.3 Water Quality Index (WQI) Calculation
1. **Proportionality Constant ($K$)**:
   $$K = \frac{1}{\sum (1/S_n)}$$
   where $S_n$ is the permissible limit for parameter $n$.
2. **Unit Weights ($W_n$)**:
   $$W_n = \frac{K}{S_n}$$
   (e.g., $W_{\text{pH}} \approx 0.3704$ and $W_{\text{DO}} \approx 0.6297$).
3. **Quality Ratings ($q_n$)**:
   $$q_n = 100 \times \frac{V_n - V_{io}}{S_n - V_{io}}$$
   where $V_n$ is the observed value, and $V_{io}$ is the ideal value (7.0 for pH, 14.6 mg/L for DO).
4. **Aggregation**:
   $$\text{WQI} = \sum (W_n \times q_n)$$
   The raw score is mapped to a 0.0–1.0 health scale.

### 7.4 Fuzzy Logic Scoring
The platform integrates qualitative community insights (from Focus Group Discussions/FGDs) into quantitative scores via four steps:
1. **Encode IK Signal**: Mapping structured FGD responses across three dimensions: Fish Abundance, Water Clarity, and Vegetation Cover.
2. **Encoding Logic**: The architecture mandates the use of the average of these three encoded dimensions to create the final IK signal.
3. **Fuzzy Sets & Rules**: Assigning membership values (Low, Medium, High) and applying If-Then rules.
4. **Defuzzify**: Converting fuzzy outputs into a precise adjusted score.
   * *Example*: A "Green" composite score (e.g., 0.63) shall be adjusted to a "Yellow" traffic light (0.55) if the IK signal indicates significant ecological decline.

---

## 8. Wetland Health Classification and Management Actions

### 8.1 Health Class Tiers

| Class | Label | Score Range | Description |
| :---: | :--- | :---: | :--- |
| **A** | Very Good / Natural | 0.8–1.0 | Unmodified; very high ecological integrity. |
| **B** | Good / Slightly modified | 0.6–0.8 | Largely natural; small loss of habitat. |
| **C** | Moderate / Moderately modified | 0.4–0.6 | Moderate change in ecosystem processes. |
| **D** | Poor / Largely modified | 0.2–0.4 | Large change; serious loss of habitat/biota. |
| **E** | Very Poor / Critically modified | 0.0–0.2 | Processes completely altered. |

### 8.2 Traffic Light Responses
UI prioritization mandates the use of **3-word labels** as primary display elements.

* **Green (> 0.6)**: No action required; regular monitoring continues.
* **Yellow (0.4–0.6)**:
  * *Silt Trap Install*: Install vegetative filters to catch sediment and nutrient runoff.
  * *Constructed Wetland Build*: Man-made wetlands for tertiary domestic greywater treatment.
  * *Livelihood Promotion*: Transition to low-impact activities like beekeeping (apiculture).
  * *Riparian Re-vegetation*: Planting indigenous species (e.g., *Ficus sycomorus*).
  * *Community Conservation Areas*: Designate no-catch zones.
  * *Co-Management Groups*: Form Beach Management Units (BMUs).
* **Red (0–0.4)**: Immediate escalation. Violations must be reported under the Environment Management & Coordination Act.
  * *Effluent Incident Report*: Prompt reporting of discharge to the Ministry of Environment.
  * *STP Interceptor Setup*: Setting up interceptor STPs to direct sewage to treatment plants.
  * *Buffer Zone Enactment*: Preventing encroachment via protected area regulation.
  * *Gear Size Policy*: Fishermen should switch to better, lower meshed gillnets to increase catch per unit effort.

---

## 9. Non-Functional Requirements and Security

### 9.1 Performance and Availability
* **Availability**: 99% monthly uptime target.
* **Load Times**: 2 seconds on a 3G connection.
* **Recovery**: Recovery Point Objective (RPO) of 24 hours and Recovery Time Objective (RTO) of 4 hours.

### 9.2 Security Zones
Trust boundaries are defined as:
1. Public (Web Portal access without login)
2. Partner (SSO authenticated)
3. Admin (SSO authenticated)
4. Data Storage (PostgreSQL database)
5. Secrets (GCP Secret Manager)

### 9.3 Data Sovereignty and PII
The platform shall comply with the Kenya Data Protection Act 2019, Uganda Data Protection Act 2019, and Tanzania Data Protection Act 2022. Due to the lack of local GCP regions, data is hosted in GCP `europe-west1` (Belgium), adhering to cross-border transfer protections.

---

## 10. Implementation Roadmap

* [ ] Design Sign-off: 2nd June 2026
* [ ] Platform Development: 25th May – 26th June 2026
* [ ] Training (ToT Workshops): End of June 2026
* [ ] Data Collection Launch: Early July 2026

---

## Exit Criterion

> [!IMPORTANT]
> This brief MUST be reviewed and approved by at least one stakeholder **outside** the product team before a PRD is written. No PRD work begins until this approval is recorded below.

**Stakeholder Sign-off Checklist**:
- [ ] PM reviewed and agrees on problem statement
- [ ] Engineering Lead consulted on constraints
- [ ] Design Lead consulted on user context
- [ ] External stakeholder approved (Name: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_, Date: \_\_\_\_\_\_\_\_\_\_\_)
