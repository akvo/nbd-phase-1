# PRD — shadcn/ui Design System Integration

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: PM + Sally (UX Designer) | Target Location: `docs/prd/shadcn_ui_setup_prd.md`
> Status: `Approved`

---

## 1. Overview

**One-liner**:
Integration of the `shadcn/ui` design system components into our Next.js 16 frontend stack to establish a robust, reusable component catalog.

**What we are building** (What):
We will install and configure `shadcn/ui` (including radix-ui primitive foundations) inside the `frontend` service. This provides an atomic design kit supporting key accessible components like Buttons, Dialogs, Cards, Inputs, and Forms aligned with our Mobile-First design system.

**Why now** (Strategic context):
Standardizing UI components ensures consistent visuals, shortens subsequent development times, enforces accessibility standards (aria-labels, focus indicators), and matches our Premium Aesthetics guidelines.

---

## 2. Goals & Success Metrics

| Goal | Success Metric | Baseline | Target | Owner |
|------|---------------|----------|--------|-------|
| Establish Component Base | Availability of foundational shadcn components | 0 | 5+ base components | UX |
| Accessible Interfaces | Keyboard navigation and focus compliance | Ad-hoc | WCAG 2.1 AA Compliant | Dev |

**Anti-Goals**:
- Implementing full application views (only setting up the design framework/primitives).

---

## 3. Target Personas

| Persona | Job-to-be-Done | Key Frustration | v1 Priority |
|---------|---------------|-----------------|-------------|
| Developer (Amelia) | Reuse well-tested, styled components instantly | Writing accessible components from scratch | Primary |

---

## 4. User Stories

| ID | User Story | Priority (MoSCoW) | FR Reference |
|----|-----------|-------------------|--------------|
| US-001 | As a developer, I want to use standard UI primitives (Button, Card, Input) so that I can implement views faster. | Must Have | FR-001 |
| US-002 | As a user, I want UI controls to be accessible and scale beautifully on mobile so that I can easily browse the platform. | Must Have | FR-002 |

---

## 5. Functional Requirements

| ID | Requirement | User Story | Priority |
|----|-------------|------------|----------|
| FR-001 | The system MUST initialize the `shadcn` config and dependencies (Tailwind components mapping, radix-ui) in the `frontend` container. | US-001 | Must Have |
| FR-002 | The system MUST configure components in `components/ui` folder for easy extension. | US-001 | Must Have |
| FR-003 | The system MUST support standard responsive theme variables (colors, borders, fonts) in global styles configuration. | US-002 | Must Have |

---

## 6. Non-Functional Requirements

| Category | Requirement | Metric |
|----------|-------------|--------|
| **Performance** | Tree-shakable components | Zero impact on bundle size for unused components |
| **Accessibility** | Built-in ARIA attributes and focus management | WCAG AA compliance out of the box |

---

## 7. Folder Flow

```
frontend/
├── components/
│   └── ui/             <-- Copied shadcn UI elements
├── src/
│   └── app/
│       ├── globals.css  <-- Theme CSS variables configuration
│       └── page.tsx
├── components.json     <-- shadcn CLI settings file
└── tailwind.config.ts  <-- theme definitions (if utilizing v3/v4 bridge)
```

---

## 8. Scope

**v1 — In Scope**:
- Initializing `shadcn@latest` CLI setup.
- Adding basic components: `Button`, `Card`, `Input`, `Dialog`.
- Verifying local UI importing in `frontend`.

**v1 — Explicitly Out of Scope**:
- Complex composite pages or components.

---

## 9. Assumptions & Constraints

- Requires execution inside the running Docker `frontend` container (via `yarn` / `npx`).
- Needs local installation for typescript/editor resolution.

---

## 10. Epic & Ballpark Estimation

| Component | Complexity | Ballpark Estimate | Assumptions |
|-----------|------------|-------------------|-------------|
| shadcn/ui Initialization | Simple | 0.2 Day | Standard init process |
| Primitive Components | Simple | 0.2 Day | Adding button, card, input |

---

## Exit Criterion

> This PRD must be verified by the user to proceed to LLD and implementation.
