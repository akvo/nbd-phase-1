# PRD — NBD Design System Assets & UI Components

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: Sally (UX Designer) + John (Product Manager) | Target Location: `docs/prd/ui_components_assets_prd.md`
> Status: `Approved`

---

## 1. Overview

**One-liner**:
Integration of the custom Nile Basin Discourse (NBD) Platform design system assets, theme variables, and UI components into the Next.js frontend using Tailwind CSS v4 and React primitives.

**What we are building** (What):
We are establishing the global styling tokens (Colors, Typography, Icons, Font family) and implementing/refining a set of highly premium, accessible, and responsive base UI components:
1. **Theme Tokens**: Global CSS variables in `globals.css` mapping Figma colors (Primary: `#38b1dd`, Secondary: `#c5eefd`, grey shades, typography sizes, Inter font-family).
2. **Interactive Components**: `Button` (primary, secondary, tertiary, ghost), `Toggle`, `Checkbox`, `Progress` bar, `Badge`, `Card`, `Input`, `Dropdown` selection, `Message Note` (alert/info banners), and styled `Table`.

**Why now** (Strategic context):
Standardizing UI components ensures visual coherence across the NBD platform, eliminates design debt, guarantees a mobile-responsive experience, and satisfies Antigravity's Premium Aesthetics standard.

---

## 2. Goals & Success Metrics

| Goal | Success Metric | Baseline | Target | Owner |
|------|---------------|----------|--------|-------|
| UI Standardisation | Coverage of base components from Figma | 4 partial components | 10 fully styled components | UX Designer |
| Premium Aesthetics | Zero visual regression compared to Figma specs | None | 100% alignment | UX Designer |
| Accessibility | Keyboard focus states & ARIA roles | Basic | WCAG 2.1 AA Compliant | Developer |

**Anti-Goals**:
- Building page layouts or business routing logic in this epic.

---

## 3. Target Users & Personas

| Persona | Job-to-be-Done | Key Frustration | v1 Priority |
|---------|---------------|-----------------|-------------|
| Frontend Developer | Build high-fidelity NBD platform pages rapidly | Creating customized styled components from scratch | Primary |
| End User | Interact with a premium, responsive portal | Clunky input controls or inconsistent UI styling on mobile | Secondary |

---

## 4. User Stories

| ID | User Story | Priority (MoSCoW) | FR Reference |
|----|-----------|-------------------|--------------|
| US-001 | As a developer, I want to use standard NBD design tokens and font variables so that all typography and colors match Figma automatically. | Must Have | FR-001 |
| US-002 | As a developer, I want custom-styled Tailwind components (Button, Card, Input, Checkbox, Toggle, Progress, Badge, Dropdown, Message note, Table) to match Figma dev-mode design specifications. | Must Have | FR-002, FR-003 |
| US-003 | As a keyboard-only user, I want focus states and tap targets on buttons and input fields to be clearly visible. | Must Have | FR-004 |

---

## 5. Functional Requirements

| ID | Requirement | User Story | Priority |
|----|-------------|------------|----------|
| FR-001 | The system MUST define NBD custom variables (colors, typography weight, border radius) in `globals.css` under the Tailwind CSS v4 `@theme` block. | US-001 | Must Have |
| FR-002 | The system MUST update/implement the components in `src/components/ui/` or generic utility libraries according to Figma dev-mode outputs. | US-002 | Must Have |
| FR-003 | The system MUST export clear TypeScript interfaces/props for each component. | US-002 | Must Have |
| FR-004 | Every interactive component (Button, Checkbox, Toggle, Dropdown, Input) MUST support visual `:focus-visible` or active states. | US-003 | Must Have |

---

## 6. Non-Functional Requirements

| Category | Requirement | Metric |
|----------|-------------|--------|
| **Performance** | Page speed impact | Bundle size overhead minimal, leveraging tree-shakable components |
| **Accessibility** | Focus indicators and screen-reader access | WCAG 2.1 AA compliant, Lighthouse A11y score ≥ 90 |
| **Responsiveness** | Mobile compatibility | Flawless rendering on both mobile (320px+) and desktop viewports |

---

## 7. Folder Flow

```
frontend/
├── src/
│   ├── app/
│   │   ├── globals.css      # NBD theme variables under @theme
│   └── components/
│       └── ui/              # Customized NBD component files
│           ├── button.tsx   # Updated NBD Button
│           ├── toggle.tsx   # New Toggle
│           ├── checkbox.tsx # New Checkbox
│           ├── progress.tsx # New Progress
│           ├── badge.tsx    # New Badge
│           ├── card.tsx     # Updated Card
│           ├── input.tsx    # Updated Input
│           ├── dropdown.tsx # New Dropdown
│           ├── message-note.tsx # New Message note
│           └── table.tsx    # New Table
```

---

## 8. Scope

**v1 — In Scope**:
- Configuring NBD global style tokens (Colors, typography sizes, family, weights) in `globals.css`.
- Creating/updating 10 key components: Button, Toggle, Checkbox, Progress, Badge, Card, Input, Dropdown, Message note, Table.
- Verification playground or story check in `src/app/page.tsx`.

**v1 — Explicitly Out of Scope**:
- Complex form validations (only structural input/select styling).
- Integration of backend data APIs.

---

## 9. Assumptions & Constraints

- Design inputs are taken from the provided Figma links.
- Uses Tailwind CSS v4 CSS-first config schema in Next.js 16.

---

## 10. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-06-01 | Amelia (Developer) | Initial draft for NBD UI Components |

---

## Exit Criterion

> This PRD must be approved by the user to proceed to LLD and implementation.
