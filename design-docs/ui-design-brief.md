# UI Design Brief
## Citizen-Led Wetland Monitoring Platform — NBD Phase 1

**Project:** Technical Support to Implement Citizen-Led Data Generation and Management Activities
**Client:** Nile Basin Discourse (NBD)
**Countries:** Kenya, Tanzania, Uganda

---

## What we are building

A single web application with two surfaces:

1. **Wetland Data Portal** — public-facing; shows wetland health, pollution incidents, and management actions
2. **Admin interface** — restricted section for staff to review, approve, and manage monitoring data

---

## Mobile first

**The portal is the primary public-facing product and most users will reach it on a phone.** Design mobile screens first. Desktop is a progressive enhancement, not the baseline.

The portal should feel native on a 375px screen — maps, health cards, traffic lights, and charts all need to work without pinching or horizontal scrolling.

The admin interface is used by staff on laptops and tablets. Design desktop-first for admin, but ensure it does not break below 768px.

---

## Users

### Portal users

| Who | Access | Typical device |
|-----|--------|---------------|
| General public, community members | No login | Phone |
| County / district officials | No login | Phone or laptop |
| Partner organisations, academic staff | SSO or email login | Laptop |

### Admin users

| Who | Device | Tech comfort |
|-----|--------|-------------|
| CSO staff (UWASNET / KEWASNET) | Laptop or tablet | Moderate |
| Academic partners (Makerere / UoN) | Laptop | High |
| NBD Secretariat admins | Laptop | High |

Two roles: **Reviewer** (approve / reject records) and **Admin** (superset — also manages users and sites).

---

## Design references

Lo-fi wireframes exist for both surfaces. They define layout and content structure — not visual design. Treat them as interaction blueprints.

- `admin-interface.html` — admin data review workspace
- `portal.html` — portal with three views: public, partner (logged in), login screen
- `architecture.html` — system overview (reference only)

Ask for a walkthrough if helpful.

---

## Design system

**There is no existing style guide from the client.** The designer defines the design system from scratch: colour palette, typography, spacing scale, component styles, and iconography.

The design system will be used in two ways:
- **Designer:** applies it to the primary dashboards (screens listed below)
- **AI-assisted design (Claude):** extends it to simpler secondary screens once the system is established

For this to work, the design system must be well-documented and systematic — token-based colours, consistent spacing, reusable components.

### One functional constraint

The **wetland health traffic light** is the core UI element. It appears on every site card, map pin, and dashboard. Three states:

| Class | Meaning | Action triggered |
|-------|---------|-----------------|
| A–B | Good / Fair | None |
| C | Moderate | Community response |
| D–E | Poor / Critical | Government escalation |

This component must be immediately legible at small sizes on a phone screen. Colour must always be paired with a label or icon — never colour alone.

### Technical compatibility

The design system must work with: **Next.js, ECharts** (charts), **Leaflet.js** (maps). Avoid design patterns that require custom animation libraries or heavy UI frameworks.

---

## Primary screens — designer scope

### Portal (mobile-first)

1. **Map view** — single screen with two states:
   - *Public (logged out):* interactive map with pollution incident markers and wetland site health badges. Satellite layer toggle.
   - *Partner (logged in):* same map, additional data layers unlocked — parameter group breakdown (Physico-chemical, Catchment/hydro, Ecological, Governance), IK-adjusted score indicator, raw sampling data table.
2. **Login screen** — Google SSO, email + password. Self-registration is not available.

**Component (not a separate screen):** Site health panel — opens when a site is tapped on the map. Shows health class (A–E), traffic light, 6-month trend chart, and management actions for Yellow and Red sites. Must work on mobile as a bottom sheet or drawer.

### Admin interface (desktop-first)

3. **Data screen** — default view; searchable table of incoming records filterable by Form type, Status, Basin, Date. Statuses: Pending / Approved / Rejected. Row expands to show full record detail and approve/reject actions. Add New modal opens four form types: Pollution report, Sampling record, Lab QA report, FGD session.
4. **Site Management** — searchable list of monitoring sites. Create/edit site in a popup. Expandable row shows attached documents (PDF, JPG, PNG).
5. **User Management** — searchable list of users with role badges. Invite and role-assign via popup. No self-registration.

---

## Constraints

- **Low bandwidth.** Users are often on slow mobile connections. No heavy images, no blocking assets. Maps tile on demand. Charts are data-driven.
- **PDF export.** Portal site health cards must be printable. Design with a clean print layout in mind. Sandra will help
- **No client branding.** NBD has not provided a logo or brand guidelines. Use a neutral placeholder — do not invest in a bespoke logo treatment at this stage.

---


