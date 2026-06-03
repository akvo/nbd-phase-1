# PRD — Testing Infrastructure & Coverage Setup

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: PM + Winston (Architect) | Target Location: `docs/prd/testing_infrastructure_prd.md`
> Status: `Approved`


---

## 1. Overview

**One-liner**:
A unified testing setup for both backend (Pytest + coverage) and frontend (Vitest + coverage) environments to ensure code stability, regression prevention, and trace test coverage metrics.

**What we are building** (What):
We are establishing the testing framework and coverage configuration for both stacks:
1. **Backend Testing & Coverage**: Integrating `pytest-cov` to measure coverage in our FastAPI application, configure reports, and assert thresholds.
2. **Frontend Testing & Coverage**: Adding `vitest` along with `@testing-library/react`, `jsdom`, and `@vitest/coverage-v8` to run React component tests and gather coverage statistics.
3. **Local commands**: Updating package commands to make test execution simple for developers.

**Why now**:
As the platform expands with KoboToolbox ingestion, indigenous knowledge fuzzy logic calculations, and email notification routines, having robust unit test suites and visible code coverage metrics is crucial to prevent regressions and keep the code quality high.

---

## 2. Goals & Success Metrics

| Goal | Success Metric | Baseline | Target | Owner |
|------|---------------|----------|--------|-------|
| Backend Coverage | Backend line coverage report generated | None | >80% coverage | Tester |
| Frontend Testing | Frontend tests runner configured | None | Complete Vitest execution | Tester |
| Frontend Coverage | Frontend line coverage report generated | None | >50% coverage | Tester |

---

## 3. Target Users & Personas

| Persona | Job-to-be-Done | Key Frustration | v1 Priority |
|---------|---------------|-----------------|-------------|
| Amelia (Developer) | Run tests quickly and see line coverage metrics | Complex testing setups, slow feedback loop | Primary |
| Murat (Tester) | Ensure tests cover edge cases and logic paths | Missing metrics to identify untested code paths | Primary |

---

## 4. User Stories

| ID | User Story | Priority (MoSCoW) | FR Reference |
|----|-----------|-------------------|--------------|
| US-001 | As a developer, I want to run backend tests with coverage so that I can see which lines of my Python application are not tested. | Must Have | FR-001 |
| US-002 | As a developer, I want to run frontend tests with coverage so that I can verify React component integrity and view coverage reports. | Must Have | FR-002, FR-003 |

---

## 5. Functional Requirements

| ID | Requirement | User Story | Priority |
|----|-------------|------------|----------|
| FR-001 | The backend container MUST support running pytest with coverage tracing using `pytest-cov`, ignoring external site-packages. | US-001 | Must Have |
| FR-002 | The frontend container MUST support running `vitest` tests with coverage using `@vitest/coverage-v8`. | US-002 | Must Have |
| FR-003 | The frontend testing environment MUST support testing React 19 components using `@testing-library/react` and `jsdom`. | US-002 | Must Have |
| FR-004 | The system MUST include basic test cases demonstrating how to write and run tests for both backend modules and frontend pages/components. | US-001, US-002 | Must Have |

---

## 6. Non-Functional Requirements

| Category | Requirement | Metric |
|----------|-------------|--------|
| **Performance** | Local test execution speed | Backend: < 10 seconds, Frontend: < 10 seconds |
| **Integrity** | Coverage report format | Generate both console text summary and HTML reports (for local dev viewing) |
| **Frameworks** | Frontend test runner | Vitest (compatible with React 19 and Vite/Next.js) |

---

## 7. Scope

**v1 — In Scope**:
- Adding `pytest-cov==4.1.0` and `httpx` to backend dependencies and configuring them.
- Installing `vitest`, `@vitest/coverage-v8`, `@testing-library/react`, `@testing-library/jest-dom`, and `jsdom` to the frontend.
- Implementing dedicated unit tests for all backend endpoints in `backend/app/main.py` (`test_main.py`).
- Implementing unit tests for the APScheduler daemon and job functions in `backend/app/scheduler.py` (`test_scheduler.py`).
- Adding component unit tests in the frontend for `button.tsx`, `card.tsx`, `input.tsx`, `loader.tsx`, and `progress.tsx` under their respective local `__tests__` folders.
- Ensuring backend coverage reaches >80% and frontend coverage reaches >50%.

**v1 — Explicitly Out of Scope**:
- Full end-to-end testing with Playwright or Cypress (will be addressed in a future QA phase).
- Integrating test coverage reporting to external SaaS services (e.g. Codecov) during local phase.

---

## 8. Assumptions & Constraints

- Next.js project is fully compatible with Vitest runner.
- Docker execution is the preferred method for running both backend and frontend tests.

