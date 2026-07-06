# PRD — Frontend Static Data Caching

## I. Overview & Goal

### Problem Statement

The Nile Voice landing page (`frontend/src/app/page.tsx`) queries several static or semi-static resources (basins, sites, forms, and translation schemas) on mount. As the user navigates, toggles domains, or updates filters, these resources are repeatedly refetched from the FastAPI backend. This causes unnecessary server load and makes the user interface feel slow due to redundant network waterfalls.

### Core Metric

- **Client API Requests**: Reduce map load/view-toggle API calls for static assets (basins, forms) from multiple calls per session down to **one single fetch** per resource.
- **Latency/Load Speed**: Sub-second UI updates when switching domains and filters by serving data from local React memory.

---

## II. User Stories & Flows

### User Journey

- **User Personas**: Citizens and Portal Administrators
- **Journey**:
  1. The user opens the portal. The application initializes and queries the static database resources in the background.
  2. The user toggles the view between the "Wetlands Monitoring" and "Pollution Reporting" domains.
  3. Instead of seeing loading indicators or waiting for new API requests, the map forms and boundaries update instantly using the pre-cached memory.

---

## III. Requirements (Scope Guardrails)

### Must-Have

- **React Context Provider**: Create a `StaticDataContext` to hold cached lists of:
  - Basins (`basins`)
  - Sites (`sites`)
  - Forms (`forms` list and individual form translation details maps)
- **Single-Fetch Policy**: Data must be fetched exactly once on application mount and persisted in memory.
- **Dynamic Localized Mappings**: The context must cache form definitions by language (keyed by `'en'` / `'sw'`) to support instant translation toggling without network overhead.
- **Manual Eviction/Refresher**: Provide a `refreshData()` function to clear the cache and force-fetch the latest data from the backend if necessary.

### Nice-to-Have

- LocalStorage fallback to persist basin and form definitions across browser reloads.

### Out of Scope

- Real-time WebSockets synchronization for citizen submissions (submissions and incident alerts remain dynamic).

---

## IV. Acceptance Criteria

### User Acceptance Criteria (UAC)

- **UAC 1**: Toggling the domain (Wetland/Pollution) or language does not trigger new HTTP requests for basins or forms.
- **UAC 2**: The UI displays correct, up-to-date data matching the database seeder on first boot.

### Technical Acceptance Criteria (TAC)

- **TAC 1**: The network inspector must show exactly zero duplicate requests for `/basins` and `/forms` during map navigation.
- **TAC 2**: All React testing library assertions and vitest suites must pass with mock providers in place.
