# PRD — NBD Platform Login Page

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: Sally (UX Designer) + John (Product Manager) | Target Location: `docs/prd/login_page_prd.md`
> Status: `Approved`

---

## 1. Overview

**One-liner**:
A clean, responsive, and secure Login page for the Nile Basin Discourse (NBD) Platform featuring standard credentials entry and Google Sign-In authentication.

**What we are building** (What):
We will implement the login screen matching the Figma specifications, including:
1. **Credentials Login Form**: Email input, Password input, Remember me checkbox, and a "Forgot password" link.
2. **Google Single Sign-On (SSO)**: A branded Google Sign-in Button compliant with Google's design rules.
3. **Responsive Layout**: Designed mobile-first, centering the login card beautifully with clean NBD branding.

**Why now** (Strategic context):
Establishing the entrance gateway is critical for authenticating citizen-led wetland monitoring users and securing platform data.

---

## 2. Goals & Success Metrics

| Goal | Success Metric | Baseline | Target | Owner |
|------|---------------|----------|--------|-------|
| Authenticate Users | Authentication success rate | 0% | 100% | Developer |
| Premium UX | Visual match to design guidelines | None | 100% match | UX Designer |
| Accessibility | Complete keyboard tab and focus flow | None | WCAG 2.1 AA Compliant | Developer |

**Anti-Goals**:
- Implementing full backend authentication endpoints or token storage strategies in this specific frontend UI layout task (mock auth flows only).

---

## 3. Target Users & Personas

| Persona | Job-to-be-Done | Key Frustration | v1 Priority |
|---------|---------------|-----------------|-------------|
| Wetland Monitor | Sign in securely to submit monitoring reports | Tedious login flow or broken OAuth flows on mobile | Primary |

---

## 4. User Stories

| ID | User Story | Priority (MoSCoW) | FR Reference |
|----|-----------|-------------------|--------------|
| US-001 | As a platform user, I want to login with my email and password so I can access my workspace. | Must Have | FR-001, FR-002 |
| US-002 | As a platform user, I want to login with my Google account for quick access. | Must Have | FR-003 |
| US-003 | As a user, I want to see clear visual validation if I enter invalid credentials. | Must Have | FR-004 |

---

## 5. Functional Requirements

| ID | Requirement | User Story | Priority |
|----|-------------|------------|----------|
| FR-001 | The system MUST display inputs for Email and Password. | US-001 | Must Have |
| FR-002 | The system MUST provide a "Remember me" checkbox and a "Forgot password" action. | US-001 | Must Have |
| FR-003 | The system MUST render a Google Sign-In button adhering strictly to the Google branding style guides (custom CSS and SVG). | US-002 | Must Have |
| FR-004 | The system MUST prevent form submission if the email format is invalid. | US-003 | Must Have |

---

## 6. Non-Functional Requirements

| Category | Requirement | Metric |
|----------|-------------|--------|
| **Branding** | Google Button CSS compatibility | Perfect alignment with Google branding guidelines |
| **Accessibility** | Focus indicator outline and labels | Full keyboard compliance, Lighthouse A11y ≥ 95 |

---

## 7. Folder Flow

```
frontend/
├── src/
│   ├── app/
│   │   └── login/
│   │       └── page.tsx        # Login Page component
```

---

## 8. Scope

**v1 — In Scope**:
- Creating the `/login` route.
- Building the login card with header, input form, and action buttons.
- Styling the Google Sign-in button with the specific SVG and CSS styles.
- Form field validation (checking for non-empty and email format).

**v1 — Explicitly Out of Scope**:
- Real backend authorization validation or database connection in this phase (handled in mock states).

---

## Exit Criterion

> This PRD must be approved by the user to proceed to LLD and implementation plan.
