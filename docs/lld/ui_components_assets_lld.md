# LLD — NBD UI Components & Style Assets

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) + Amelia (Developer) | Target Location: `docs/lld/ui_components_assets_lld.md` | References: `docs/prd/ui_components_assets_prd.md`
> Status: `Approved`

---

## 1. Overview & Scope

**Component / Module**:
This LLD defines the styling variables and component primitives for the custom NBD Platform. All styling utilizes Next.js with Tailwind CSS v4 and standard TypeScript/React properties.

**PRD References**:
- FR-001 (Theme design tokens definition)
- FR-002 (Base interactive UI components)
- FR-003 (TypeScript interfaces)
- FR-004 (Focus/Accessible visual states)

**Out of Scope**:
- Advanced complex component composition (such as interactive datepickers, multi-select search tags).
- Direct state integration with business API schemas.

---

## 2. Component Design & Prop Specifications

We will define 10 core component files in `src/components/ui/`.

### 2.1 Button (`button.tsx`)
Updates the existing button to support custom NBD tokens.
```typescript
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'tertiary' | 'ghost';
  size?: 'xs' | 'sm' | 'md' | 'lg';
  iconLeft?: React.ReactNode;
  iconRight?: React.ReactNode;
}
```
**Styles mapped from Figma**:
- `primary`: Background `nbd-primary` (`#38b1dd`), Hover `nbd-primary-hover` (`#27a0cd`), text white.
- `secondary`: Background `nbd-secondary` (`#c5eefd`), Hover `#98dff9`, text `#141414`.
- `tertiary`: Border `nbd-primary` (`#38b1dd`), background white, Hover background `nbd-light-bg` (`#f5fcff`), text `nbd-primary`.
- `ghost`: Background transparent, Hover background `nbd-light-bg` (`#f5fcff`), text `nbd-primary`.

---

### 2.2 Toggle (`toggle.tsx`)
A switch component mapping the switch logic.
```typescript
export interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  disabled?: boolean;
}
```

---

### 2.3 Checkbox (`checkbox.tsx`)
Styled checkbox component using standard SVG checkmarks.
```typescript
export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  label?: string;
  checked?: boolean;
  onChange?: (checked: boolean) => void;
}
```

---

### 2.4 Progress (`progress.tsx`)
Progress indicator bar.
```typescript
export interface ProgressProps {
  value: number; // 0 to 100
  max?: number;
  className?: string;
}
```

---

### 2.5 Badge (`badge.tsx`)
Small badge to show status values.
```typescript
export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'neutral';
}
```

---

### 2.6 Card (`card.tsx`)
Extends existing `card.tsx` with standard NBD padding and borders.
```typescript
export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
}
```

---

### 2.7 Input (`input.tsx`)
Updates existing input to match NBD's custom borders, focus rings, and icon positions.
```typescript
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  iconLeft?: React.ReactNode;
  iconRight?: React.ReactNode;
}
```

---

### 2.8 Dropdown (`dropdown.tsx`)
Select control component.
```typescript
export interface DropdownOption {
  value: string;
  label: string;
}
export interface DropdownProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'value' | 'onChange'> {
  options: DropdownOption[];
  value?: string;
  onChange?: (value: string) => void;
  label?: string;
}
```

---

### 2.9 Message Note (`message-note.tsx`)
Alert notes with custom headers and status borders.
```typescript
export interface MessageNoteProps extends React.HTMLAttributes<HTMLDivElement> {
  type?: 'info' | 'success' | 'warning' | 'error';
  title?: string;
}
```

---

### 2.10 Table (`table.tsx`)
Styled layout component for tabular datasets.
```typescript
export interface TableProps extends React.TableHTMLAttributes<HTMLTableElement> {}
```

---

## 3. Styling & Theme Tokens (`src/app/globals.css`)

We will add the custom theme properties under the `@theme` block in `globals.css`:
```css
@theme {
  --color-nbd-primary: #38b1dd;
  --color-nbd-primary-hover: #27a0cd;
  --color-nbd-secondary: #c5eefd;
  --color-nbd-secondary-hover: #98dff9;
  --color-nbd-light-bg: #f5fcff;
  --color-nbd-disabled: #f6f6f6;
  --color-nbd-disabled-text: #afafaf;
  
  --radius-nbd: 8px;
}
```

---

## 4. Verification Plan

### Manual Verification
- We will construct a dashboard under `src/app/page.tsx` displaying all components:
  1. Buttons in all variants and states (default, hover, active/pressed, disabled).
  2. Toggle and Checkbox with active interactive states.
  3. Progress bars showing percentage completion.
  4. Badges mapping different status colors.
  5. Cards demonstrating basic content structure.
  6. Text Inputs with optional left/right placeholder icons.
  7. Dropdown selection lists.
  8. Message Notes showing info, success, warning, and error colors.
  9. Table rendering sample data.

### Automated Checks
- Verify type definitions and compile using `yarn lint`.
