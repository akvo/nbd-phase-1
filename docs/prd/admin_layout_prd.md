# PRD — NBD Platform Admin Layout

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: Sally (UX Designer) + John (Product Manager) | Target Location: `docs/prd/admin_layout_prd.md`
> Status: `Under Review`

--## 1. Overview

**One-liner**:
A clean, light-themed, and responsive administrative panel layout for the Nile Basin Discourse (NBD) platform, featuring a top navigation header and section-level tabs (Data, User Management, Site Management) to manage and moderate environmental submissions.

**What we are building** (What):
We will implement the main layout framework for all administrative and moderation pages, matching the attached design mockups. This layout includes:
1. **Top Navigation Header (Global)**:
   - Left branding navigation links: "Admin view" (active), "Projects", "Tasks".
   - Right utility actions: Settings gear icon, Notification bell, and an "Account" dropdown.
2. **Sub-Navigation Tabs (Admin View)**:
   - Inline tab pills situated below the main title:
     - *Data* (Active by default, routes to the moderation grid/submissions table).
     - *User management* (Routes to administrator invitations and roles list).
     - *Site management* (Routes to basin, wetland, and site configurations).
3. **Data Overview Frame**:
   - Header title indicating "Data overview" with total records badge (e.g. "240 instances").
   - Action controls: "Download CSV" outline button and "+ Add new" primary button.
   - Filter dropdown select controls: "Select a form", "Select status", "Select a basin", and a "Clear" button.
   - A clean white table/data list detailing ID, Form type, Basin/Site, Date, Submitted by, Status, and Actions (Reject/Approve).
4. **Light Visual Theme**:
   - Background: `bg-slate-50` with main panels wrapped in white cards (`bg-white` with fine borders).
   - Primary active states and buttons use the sky blue shade (`#38b1dd`).

**Why now** (Strategic context):
The administrative staff need a unified, clean portal to curate incoming observation data. Aligning the layout directly with the verified NBD top-nav mockup ensures consistent user experience.

---

## 2. Goals & Success Metrics

| Goal | Success Metric | Baseline | Target | Owner |
|------|---------------|----------|--------|-------|
| Figma Visual Match | Light theme compliance and correct typography alignment | Dark sidebar layout | 100% match with the design layout | UX Designer |
| Viewport Responsiveness | Fluid transition between desktop and mobile viewport scales | Hardcoded layouts | Zero horizontal scroll above 768px | Developer |
| Navigation Flow | Intact route mapping via top nav and inline admin tabs | Complex nested routes | Intuitive routing structure | Developer |

---

## 3. Target Users & Personas

| Persona | Job-to-be-Done | Key Frustration | v1 Priority |
|---------|---------------|-----------------|-------------|
| **NBD Secretariat** | Moderate incoming pollution reports and validate sampling records. | Multi-tier navigation layouts that waste screen space. | Primary |
| **System Administrator** | Manage user roles and site parameters. | Complex database interfaces that are hard to navigate. | Primary |

---

## 4. User Stories

| ID | User Story | Priority (MoSCoW) | FR Reference |
|----|-----------|-------------------|--------------|
| US-001 | As an admin/reviewer, I want a top navigation header so I can switch contexts between Admin views and other tools. | Must Have | FR-001 |
| US-002 | As an admin, I want to use sub-navigation tabs ("Data", "User management", "Site management") to navigate between admin-specific panels. | Must Have | FR-002 |
| US-003 | As an administrator, I want to see my account options and notifications clearly presented in the top header. | Must Have | FR-003, FR-004 |

---

## 5. Functional Requirements

| ID | Requirement | User Story | Priority |
|----|-------------|------------|----------|
| **FR-001** | The layout MUST render a global top navigation header with branding and links: "Admin view", "Projects", "Tasks". | US-001 | Must Have |
| **FR-002** | The active menu link (e.g., "Admin view") MUST be highlighted with the active style (e.g., light blue background). | US-001 | Must Have |
| **FR-003** | The layout MUST render sub-navigation tabs below the main view title: "Data", "User management", "Site management". | US-002 | Must Have |
| **FR-004** | The header MUST display utility actions on the right: Settings gear icon, Notifications bell icon, and the "Account" dropdown button. | US-003 | Must Have |
| **FR-005** | Clicking on sub-navigation tabs MUST switch content panels cleanly and preserve page context. | US-002 | Must Have |

---

## 6. Non-Functional Requirements

| Category | Requirement | Metric |
|----------|-------------|--------|
| **Aesthetics** | Premium dark-mode/glassmorphic administrative theme | Sidebar borders use HSL transparency overlays (`hsla(var(--border) / 0.1)`) |
| **Routing** | Native Next.js Layout Structure | Layout wrapper preserves state across sub-routes |
| **Accessibility** | ARIA-compliant navigation menus | Keyboard focus indicators, `nav` role wrappers, and descriptive labels |
| **Performance** | Layout loading overhead | Paint time < 300ms, zero layout shifts during render |

---

## 7. Next.js Routing & Layout Flow

The admin layout will be structured as a Next.js App Router root layout for the `/admin` route group:

```
frontend/
├── src/
│   ├── app/
│   │   └── admin/
│   │       ├── layout.tsx         # Universal Admin Shell (Top Header, Title block, and Tabs wrapper)
│   │       ├── page.tsx           # Custom Admin Landing Page / Dashboard Overview
│   │       ├── data/              # Submissions moderation grid and interactive status filters
│   │       ├── moderation/        # Moderation sub-route placeholder
│   │       ├── users/             # User Management sub-route placeholder
│   │       ├── sites/             # Site Management sub-route placeholder
│   │       └── ingestion/         # Ingestion / DLQ sub-route placeholder
│   └── components/
│       └── admin/
│           ├── header.tsx         # Global top header navigation links and profile widgets
│           └── tabs.tsx           # Sub-navigation tab selector pills for active admin sub-views
```

---

## 8. Scope

**v1 — In Scope**:
- Design and code of `frontend/src/app/admin/layout.tsx` enclosing admin pages.
- Global top header component (`header.tsx`) with active state routing highlights and user utilities.
- Sub-navigation tabs component (`tabs.tsx`) for switching active views within `/admin`.
- Interactive data moderation table and filters in `/admin/data/page.tsx` with reactively-updating state.
- Custom dashboard overview page under `/admin/page.tsx`.
- Standardized light-themed layout backgrounds matching Figma specification.

**v1 — Explicitly Out of Scope**:
- The actual implementation of individual moderation form schemas, user management detail actions, or site config forms (each will have a simple placeholder route).
- Real integration with OIDC SSO providers (user utilities/badges will be mock-rendered).

---

## 9. Epic & Ballpark Estimation

| Component | Task Description | Complexity | Ballpark Estimate (Hours) | Assumptions |
|-----------|------------------|------------|---------------------------|-------------|
| **Next.js Route Group** | Configure `/admin` folder routing and default nested layout | Simple | 2h | Next.js App Router works |
| **Sidebar Navigation** | Build list navigations, dynamic route matching, collapsible behavior | Medium | 6h | Brand assets are available |
| **Admin Header** | Integrate breadcrumbs, profile session info, role badges, logout | Simple | 4h | Session details mocked |
| **Responsive Wrapper** | Implement CSS/Tailwind responsiveness, mobile menu drawer | Medium | 5h | Mobile layout is tablet-friendly |
| **Unit Verification** | Write Vitest render and navigation tests for Admin Layout | Simple | 3h | Vitest setup is fully ready |

---

## Exit Criterion

> This PRD must be approved by the user to proceed to LLD and implementation plan.
