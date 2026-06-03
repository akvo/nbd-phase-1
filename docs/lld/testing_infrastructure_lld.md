# LLD — Testing Infrastructure & Coverage Setup

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) | Target Location: `docs/lld/testing_infrastructure_lld.md` | References: `docs/prd/testing_infrastructure_prd.md`
> Status: `Approved`

---

## 1. Overview & Scope

**Component / Module**:
Backend Pytest-cov configuration & Frontend Vitest test environment.

**PRD References**:
- FR-001, FR-002, FR-003, FR-004 in `docs/prd/testing_infrastructure_prd.md`

---

## 2. Technical Component Design

### 2.1 Backend Pytest Coverage Setup
- We will install `pytest-cov==4.1.0` in the backend python dependencies.
- Pytest configuration will be stored in `backend/pyproject.toml` or `backend/setup.cfg`. Let's create `backend/pyproject.toml` to define defaults for pytest:
```toml
[tool.pytest.ini_options]
minversion = "6.0"
addopts = "-ra -q --cov=app --cov-report=term-missing"
testpaths = [
    "tests",
]
```

### 2.2 Frontend Vitest Setup
- We will install:
  - `vitest` (Test Runner)
  - `@vitest/coverage-v8` (Coverage compiler)
  - `@testing-library/react` (Component assertions)
  - `@testing-library/jest-dom` (DOM matchers)
  - `jsdom` (Simulated browser environment)
- We will add `frontend/vitest.config.ts` to configure the testing environment:
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react'; // if using Vite or React configurations
import path from 'path';

export default defineConfig({
  plugins: [],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './vitest.setup.ts',
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
    coverage: {
      provider: 'v8',
      reporter: ['text'],
      reportsDirectory: '/tmp/coverage',
      exclude: ['node_modules/**', '.next/**'],
    },
  },
});
```
- We will create `frontend/vitest.setup.ts` to import `@testing-library/jest-dom`.


---

### 2.3 Proposed Test Coverage Target Expansion
1. **Backend Endpoint Tests (`backend/tests/test_main.py`)**:
   - We will utilize `fastapi.testclient.TestClient` to perform HTTP assertions against `/api`, `/api/healthz`, and `/api/v1/test/email`.
   - For `/api/v1/test/email`, we will mock the `EmailService.send_email_async` method to verify that `BackgroundTasks` successfully processes and schedules the email send execution.
2. **Backend Scheduler Tests (`backend/tests/test_scheduler.py`)**:
   - Test execution of `hourly_kobotoolbox_pull` and `monthly_gee_ingest` with mock timing (e.g. mocking `time.sleep`) to prevent tests from hanging.
   - Mock `BlockingScheduler` class to assert jobs are registered correctly with correct intervals (cron schedules) and verify the exception-handling path when starting the scheduler.
3. **Frontend UI Component Tests**:
   - For all UI components (`button.tsx`, `card.tsx`, `input.tsx`, `loader.tsx`, `progress.tsx`, `checkbox.tsx`, `dialog.tsx`, `dropdown.tsx`, `echarts-chart.tsx`, `google-signin-button.tsx`, `map-legend.tsx`, `map-viewer.tsx`, `message-note.tsx`, `site-drawer.tsx`, `site-header.tsx`, `table.tsx`, `toggle.tsx`), write unit tests under `frontend/src/components/ui/__tests__/` asserting rendering states, default properties, interaction behaviors, and disabled states.

---

## 3. Implementation Checklist & Files

#### [MODIFY] [requirements.txt](file:///Users/galihpratama/Sites/nbd-phase-1/backend/requirements.txt)
- Add `pytest-cov==4.1.0` and `httpx==0.27.0`.

#### [NEW] [test_main.py](file:///Users/galihpratama/Sites/nbd-phase-1/backend/tests/test_main.py)
- Unit tests verifying FastAPI routing endpoints and payload validation.

#### [NEW] [test_scheduler.py](file:///Users/galihpratama/Sites/nbd-phase-1/backend/tests/test_scheduler.py)
- Unit tests verifying scheduler job scheduling, cron configs, and helper functions.

#### [NEW] [button.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/button.test.tsx)
- Unit test for UI button component.

#### [NEW] [card.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/card.test.tsx)
- Unit test for UI card sub-components.

#### [NEW] [input.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/input.test.tsx)
- Unit test for UI input text input.

#### [NEW] [loader.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/loader.test.tsx)
- Unit test for UI spinning loader component.

#### [NEW] [progress.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/progress.test.tsx)
- Unit test for progress bar rendering and percentage completion.

#### [NEW] [checkbox.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/checkbox.test.tsx)
- Unit test for checkbox toggle and state changes.

#### [NEW] [dialog.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/dialog.test.tsx)
- Unit test for modal dialog opening, closing, and overlays.

#### [NEW] [dropdown.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/dropdown.test.tsx)
- Unit test for dropdown menus, options selection, and trigger states.

#### [NEW] [echarts-chart.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/echarts-chart.test.tsx)
- Unit test verifying canvas mounting and chart container structures.

#### [NEW] [google-signin-button.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/google-signin-button.test.tsx)
- Unit test for Google sign-in click actions and layout attributes.

#### [NEW] [map-legend.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/map-legend.test.tsx)
- Unit test for map legend legends layout and color scales.

#### [NEW] [map-viewer.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/map-viewer.test.tsx)
- Unit test checking map canvas placeholders and interactive layering.

#### [NEW] [message-note.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/message-note.test.tsx)
- Unit test for alerts, success/error notice blocks, and content strings.

#### [NEW] [site-drawer.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/site-drawer.test.tsx)
- Unit test for drawer layout panel slide-ins and navigation lists.

#### [NEW] [site-header.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/site-header.test.tsx)
- Unit test for site header navigation, logo titles, and branding slots.

#### [NEW] [table.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/table.test.tsx)
- Unit test verifying table grid rows, table headers, and data populating.

#### [NEW] [toggle.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/toggle.test.tsx)
- Unit test for switch/toggle triggers and selected values.





