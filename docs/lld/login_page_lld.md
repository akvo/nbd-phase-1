# LLD — NBD Platform Login Page

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Tech Lead / Winston (Architect) | Target Location: `docs/lld/login_page_lld.md` | References: `docs/prd/login_page_prd.md`
> Status: `Approved`

---

## 1. Overview & Scope

**Component / Module**:
Responsive mobile-first Login interface at `/login` (`src/app/login/page.tsx`), integrating the custom Google Sign-In branding CSS and custom input assets.

**PRD References**:
- FR-001 (Form Inputs)
- FR-002 (Remember Me & Forgot Password)
- FR-003 (Branded Google Button)
- FR-004 (Format Validation)

---

## 2. Component Design & Layout

We will create a clean Next.js client component at `src/app/login/page.tsx` containing:
- **HeaderNavigation**: A simple, mobile-optimized top bar mapping the logo and a mobile menu trigger icon.
- **LoginCard**: Center card containing:
  - Header titles.
  - Inputs (Email & Password using custom `Input` primitives).
  - Row displaying `Checkbox` for "Remember me" and a styled link for "Forgot password".
  - Actions containing the "Sign in" primary button and the branded "Sign in with Google" button.
  - Footer notice warning that self-registration is disabled.

---

## 3. Styling & Google Branded Button

We will include the exact custom CSS selectors for the Google Sign-In button directly inside the Tailwind theme structure or CSS variables:
- CSS rules for `.gsi-material-button`, `.gsi-material-button-icon`, `.gsi-material-button-content-wrapper`, `.gsi-material-button-contents`, `.gsi-material-button-state` will be appended to `src/app/globals.css`.

---

## 4. Verification Plan

### Manual Verification
- Render `/login` on a mobile viewport simulator (e.g. 375px wide) and desktop screen size.
- Test interactive focus states for input borders and button states.
- Enter invalid email format to verify validator blocks submission.
