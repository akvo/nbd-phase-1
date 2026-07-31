# Low-Level Design (LLD): Admin Workspace Layout & Module Integration

**Status:** Approved | **Date:** 2026-06-24 | **Author:** Winston (Architect) / Sally (UX)

---

## 1. Executive Summary

This document specifies the low-level design for the **Admin Workspace Layout & Module Structure** (`/admin/*`). It establishes a unified, responsive admin shell featuring top-level navigation, sub-navigation tabs, breadcrumb context, and responsive container constraints.

---

## 2. Component Architecture & Directory Layout

```
frontend/src/
├── app/
│   └── admin/
│       ├── layout.tsx                # Primary Admin Layout Shell (Nav + Subnav)
│       ├── page.tsx                  # /admin root redirect -> /admin/data
│       ├── data/
│       │   └── page.tsx              # Data Ingestion & Approvals View
│       ├── analytics/
│       │   └── page.tsx              # Water Quality & Scoring Analytics View
│       ├── users/
│       │   └── page.tsx              # User Management & RBAC View
│       ├── forms/
│       │   └── page.tsx              # Dynamic Form Builder & Seeder View
│       └── audit/
│           └── page.tsx              # Audit Log & Security Logs View
```

---

## 3. Top Navigation & Subnav Specifications

### 3.1 Header Navigation
The admin layout incorporates a sticky top header with:
- **Brand Identity**: NBD Wetland Watch Logo + Admin Badge.
- **Global Search**: Search bar for filtering datasets, users, or audit logs.
- **Profile / Actions**: User avatar, role display, logout trigger.

### 3.2 Sub-Navigation Tabs
- **Data Approvals** (`/admin/data`) — Ingestion queue, pending submissions, inline approve/reject controls.
- **Analytics & Scoring** (`/admin/analytics`) — WQI trends, defuzzification metrics, ecological indicators.
- **User Management** (`/admin/users`) — Roles, permissions, team assignments.
- **Forms & Blueprints** (`/admin/forms`) — Form blueprint versions, seeder triggers.
- **Audit Logs** (`/admin/audit`) — Security event logs, API activity.

---

## 4. State & UI Component Design

- **Filter criteria**: Tracked in component state (`formFilter`, `statusFilter`, `basinFilter`).
- **Record list state**: Tracked in `submissions` array. Approvals and rejections perform inline mutations returning a new state reference, triggering view re-renders:
  - `handleApprove(id)`: Maps `status` to `'Active'`.
  - `handleReject(id)`: Maps `status` to `'Rejected'`.

---

## 5. Verification Plan

### Automated Tests
- Run the Vitest test suite via `./dc.sh exec frontend yarn test` to verify render reliability.
- Key test coverage:
  - `frontend/src/app/admin/__tests__/layout.test.tsx` - Asserts header navigation highlights, tab switching presence, title rendering, and sub-page nesting correctness.

### Manual Verification
- Simulate viewport widths of 375px, 768px, and 1200px in browser dev tools to verify navigation menu responsive alignment.
- Verify status changes in the submissions grid when click interactions occur on "Approve" and "Reject" buttons.
