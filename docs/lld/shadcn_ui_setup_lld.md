# LLD — shadcn/ui Design System Integration

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) / Amelia (Developer) | Target Location: `docs/lld/shadcn_ui_setup_lld.md` | References: `docs/prd/shadcn_ui_setup_prd.md`
> Status: `Approved`

---

## 1. Overview & Scope

**Component / Module**:
`shadcn/ui` components integration (`components/ui` folder, custom themes, and global tailwind configuration).

**PRD References**:
- FR-001 (CLI initialization)
- FR-002 (Components structure)
- FR-003 (Theme CSS variables)

---

## 2. Technical Strategy

We will configure `components.json` to define target paths for our Next.js project. We will use the Next.js `src/` directory convention:

### `components.json` configuration

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.js",
    "css": "src/app/globals.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui"
  }
}
```

---

## 3. Installation Steps

### 3.1 Initial Setup

We will run the shadcn init command inside the running frontend container:

```bash
./dc.sh exec frontend npx shadcn@latest init --defaults --yes --force
```

### 3.2 Add Primitives

We will install the basic components required for styling:

```bash
./dc.sh exec frontend npx shadcn@latest add button card input dialog --yes
```

---

## 4. Verification Plan

### Manual Verification

1. Verify that `components.json` is generated.
2. Verify that files are created in `frontend/src/components/ui/` (e.g., `button.tsx`).
3. Import the `Button` in `frontend/src/app/page.tsx` and run the development server to check visual compliance.
