# Low-Level Design (LLD) — Testing Infrastructure & Automated Suite

**Status**: Approved | **Date**: 2026-06-25 | **Author**: Murat (Test Architect) / Winston (Architect)

---

## 1. Overview & Objectives

This document specifies the automated testing framework setup across both backend and frontend layers:
- **Backend**: Pytest test suite executed inside Docker container (`./dc.sh exec backend tests`).
- **Frontend**: Vitest + React Testing Library test suite executed inside Docker container (`./dc.sh exec frontend yarn test`).

---

## 2. Test Architecture & Structure

```
backend/
└── tests/
    ├── conftest.py                   # Pytest fixtures & test DB session
    ├── test_main.py                  # API endpoints test suite
    ├── test_spatial_boundaries.py    # PostGIS & spatial reference APIs
    ├── test_ussd.py                  # USSD state machine & consent paging
    ├── test_whatsapp.py              # WhatsApp webhook & dynamic form router
    └── test_scheduler.py             # Ingestion & cron scheduler jobs

frontend/
└── src/
    └── components/
        └── ui/
            └── __tests__/            # Vitest component unit test suite
```

---

## 3. Implementation Checklist & Files

#### `backend/requirements.txt`
- Add `pytest-cov==4.1.0` and `httpx==0.27.0`.

#### `backend/tests/test_main.py`
- Unit tests verifying FastAPI routing endpoints and payload validation.

#### `backend/tests/test_scheduler.py`
- Unit tests verifying scheduler job scheduling, cron configs, and helper functions.

#### Frontend Component Tests (`frontend/src/components/ui/__tests__/`)
- `button.test.tsx`
- `card.test.tsx`
- `input.test.tsx`
- `loader.test.tsx`
- `progress.test.tsx`
- `checkbox.test.tsx`
- `dialog.test.tsx`
- `dropdown.test.tsx`
- `echarts-chart.test.tsx`
- `google-signin-button.test.tsx`
- `map-legend.test.tsx`
- `map-viewer.test.tsx`
- `message-note.test.tsx`
- `site-drawer.test.tsx`
- `site-header.test.tsx`
- `table.test.tsx`
- `toggle.test.tsx`

---

## 4. Verification Plan

- Backend test execution: `./dc.sh exec backend tests`
- Frontend test execution: `./dc.sh exec frontend yarn test`
