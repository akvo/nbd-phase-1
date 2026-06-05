# PRD — RBAC Security Gate (Authentication & Authorization)

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) | Target Location: `docs/prd/rbac_security_prd.md` | References: `docs/user_roles_rbac.md`, `docs/product_brief.md`
> Status: `Draft`

---

## 1. Overview

**One-liner**:
A role-based security enforcement layer (dependencies and authentication checks) matching NBD's RBAC matrix to authenticate users via JWT tokens and authorize endpoints based on role privileges.

**Brief / Problem Reference**:
Refers to Section 2 (Trust Boundaries and Authentication Architecture) of `docs/api_contract.md` and `docs/user_roles_rbac.md`.

**What we are building** (What):
A reusable security dependency layer in FastAPI that intercepts incoming HTTP requests, decodes/verifies the OIDC-issued JWT token from the `Authorization: Bearer <token>` header, extracts the user's role claim, and validates it against the route's permission requirements.

**Why now** (Strategic context):
Currently, all FastAPI routes are completely open and lack authentication. To protect administrative data curation, user management, and PII boundaries, we must deploy role validation before releasing Phase 1.

---

## 2. Goals & Success Metrics

| Goal | Success Metric | Baseline | Target | Owner |
|------|---------------|----------|--------|-------|
| Secure endpoints | Percentage of administrative/ partner endpoints protected by auth check | 0% | 100% | Architect |
| Correct role enforcement | Proper rejection of unauthorized requests (e.g. Partner accessing Admin route) | N/A (unprotected) | 100% (401/403 errors returned) | Tester |

---

## 3. Target Users & Personas

| Role | Operational Context | v1 Priority |
|------|--------------------|-------------|
| Administrator | Can manage users, create sites, update spatial schemas. | Primary |
| Reviewer | Can view data logs, clean and approve pending submissions. | Primary |
| Partner | Can submit Lab QA and FGD data. | Primary |
| General Public | Can access read-only portal map data without authentication. | Primary |

---

## 4. User Stories

| ID | User Story | Priority (MoSCoW) | FR Reference |
|----|-----------|-------------------|--------------|
| US-001 | As an **Admin/Reviewer**, I want to include my token in the header so that the platform recognizes my identity and grants my role permissions. | Must Have | FR-001 |
| US-002 | As the **System**, I want to block unauthenticated requests to protected routes with a `401 Unauthorized` response. | Must Have | FR-002 |
| US-003 | As the **System**, I want to reject authenticated users who do not have the required role for a route with a `403 Forbidden` response. | Must Have | FR-003 |

---

## 5. Functional Requirements

| ID | Requirement | User Story | Priority |
|----|-------------|------------|----------|
| FR-001 | The system MUST support parsing the `Authorization: Bearer <token>` header on all non-public endpoints. | US-001 | Must Have |
| FR-002 | The system MUST decode and validate the token signature, issuer, and expiration time. | US-002 | Must Have |
| FR-003 | The system MUST enforce role checks: `Admin` for administrative routes, `Reviewer` or `Admin` for curation routes, and `Partner` for partner forms. | US-003 | Must Have |
| FR-004 | The system MUST allow public routes (e.g. `GET /api/v1/sites`, `/api/healthz`, `/api/v1/ussd` webhook) to be accessed without authentication. | US-001 | Must Have |

---

## 6. Non-Functional Requirements

| Category | Requirement | Metric |
|----------|-------------|--------|
| **Performance** | Latency overhead of token verification | < 5ms per request (local signature check) |
| **Security** | Zero local storage of OIDC keys | Fetched dynamically from OIDC provider JWKS (or mock JWKS for testing) |

---

## 7. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-05 | Winston | Initial PRD draft |
