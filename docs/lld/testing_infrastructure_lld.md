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

## 3. Implementation Checklist & Files

#### [NEW] [pyproject.toml](file:///Users/galihpratama/Sites/nbd-phase-1/backend/pyproject.toml)
- Configuration file for pytest to automatically enable coverage reports.

#### [MODIFY] [requirements.txt](file:///Users/galihpratama/Sites/nbd-phase-1/backend/requirements.txt)
- Add `pytest-cov==4.1.0`.

#### [NEW] [vitest.config.ts](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/vitest.config.ts)
- Configure Vitest properties, jsdom environment, aliases, and coverage.

#### [NEW] [vitest.setup.ts](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/vitest.setup.ts)
- Custom matchers import for `@testing-library/jest-dom`.

#### [MODIFY] [package.json](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/package.json)
- Add test script aliases:
  - `"test": "vitest run"`
  - `"test:watch": "vitest"`
  - `"test:coverage": "vitest run --coverage"`

#### [NEW] [badge.test.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/__tests__/badge.test.tsx)
- A simple unit test validating React component rendering using TSX placed under the component's local `__tests__` directory.



