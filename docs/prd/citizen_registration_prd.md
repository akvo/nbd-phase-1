# PRD — Citizen Registration & Management

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: PM + Design Lead | Target Location: `docs/prd/citizen_registration_prd.md` | References: `docs/product_brief.md`, `docs/database_schema.md`
> Status: `Draft`

---

## 1. Overview

**One-liner**:
A secure backend service and API endpoint interface allowing administrators to invite and manage community-based Citizen Watchers and Scientists, storing their phone numbers (PII) separated from public telemetry.

**Brief / Problem Reference**:
Refers to Section 8 (Data Governance and Security) and Section 4.1 (Actor Matrix) of `docs/product_brief.md`.

**What we are building** (What):
We are building the registration endpoints (`POST /api/v1/citizens`) and lookup matching features. When admins invite citizens, we store their phone numbers and link them to their default sampling sites (`site_id`) and roles. Ingestion pipelines (like USSD/WhatsApp) check this table to verify reporter registration status.

**Why now** (Strategic context):
To enforce legal transboundary data protection laws (e.g. Kenya Data Protection Act 2019), citizen phone numbers (PII) must be kept strictly separated from public reporting logs. Admin moderation needs a structured database registry to manage user profiles and map inbound phone alerts to registered home sites.

---

## 2. Goals & Success Metrics

| Goal | Success Metric | Baseline | Target | Owner |
|------|---------------|----------|--------|-------|
| Prevent unauthorized PII access | Zero exposure of raw phone numbers to public API layer | 0% compliance | 100% compliance | Tester |
| Administrative oversight | Admin ability to invite, update, and search citizen profiles | Manual seeds only | Web UI dashboard ready | PM |

---

## 3. Target Users & Personas

| Persona | Job-to-be-Done | Key Frustration | v1 Priority |
|---------|---------------|-----------------|-------------|
| Administrator | Create, invite, and inspect registered watchers and scientists. | Dealing with complex privacy policies and manual SQL updates for telco details. | Primary |

---

## 4. User Stories

| ID | User Story | Priority (MoSCoW) | FR Reference |
|----|-----------|-------------------|--------------|
| US-001 | As an **Admin**, I want to register a citizen's phone number, default site, and role so that they are indexed as authorized monitors. | Must Have | FR-001 |
| US-002 | As an **Admin**, I want to query registered citizens without exposing raw phone numbers to standard users. | Must Have | FR-002, FR-003 |

---

## 5. Functional Requirements

| ID | Requirement | User Story | Priority |
|----|-------------|------------|----------|
| FR-001 | The system MUST expose a POST `/api/v1/citizens` endpoint restricted to `Admin` role to register new watchers/scientists. | US-001 | Must Have |
| FR-002 | The system MUST validate that the phone number format is valid (E.164 standard) and that the referenced `site_id` exists. | US-001 | Must Have |
| FR-003 | The system MUST expose a GET `/api/v1/citizens` list and GET `/api/v1/citizens/{id}` details endpoint restricted to `Admin` and `Reviewer` roles. | US-002 | Must Have |

---

## 6. Non-Functional Requirements

| Category | Requirement | Metric |
|----------|-------------|--------|
| **Security** | Role-Based Access Control (RBAC) verification | Only `Admin` can create/invite; only `Admin/Reviewer` can read. |
| **Performance** | Lookup match duration during webhook ingestion | < 10ms (cached or indexed) |

---

## 7. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-05 | Winston | Initial PRD draft |
