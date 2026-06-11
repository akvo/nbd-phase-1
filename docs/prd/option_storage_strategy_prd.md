# PRD & Architectural Decision Plan: Option & Location Storage Strategy

## I. Overview & Goal

Currently, the `Answer.options` column (a `JSONB` array) stores option **labels** (e.g., `["Smell"]`) and location **names** (e.g., `["Emurua Dikirr"]`) for USSD and WhatsApp submissions. Meanwhile, KoboToolbox sync submissions store option **values/slugs** (e.g., `["smell"]`).

This mismatch and the practice of storing human-readable labels/names poses a major maintainability risk:
1. **Label & Name Mutations**: If an option label or location name is updated/corrected, historical data becomes decoupled from the reference definitions, resulting in orphaned records or outdated text.
2. **Localization & Multi-Language**: Storing static English or Swahili strings directly in the database prevents dynamic translation rendering.
3. **Data Consistency**: Submissions from different channels store different formats for the same questions.

The goal of this planning phase is to standardize the storage strategy:
* **Options**: Store machine-readable option values/slugs (e.g., `["2"]` or `["smell"]`).
* **Locations**: Store spatial boundary UUID strings (e.g., `["9c3e9812-70b9-48e2-bd12-f9038ba08cd1"]`).

---

## II. Comparative Analysis

### 1. Options Storage Comparison

| Criteria | Option Label (Current) | Option Value/Slug (e.g., `"smell"`) | Database Option ID (e.g., `123`) |
| :--- | :--- | :--- | :--- |
| **Robustness to Label Updates** | ❌ **Poor**. Any label update breaks historical references. |  **Excellent**. Labels are purely presentational; slugs remain constant. |  **Excellent**. Labels and slugs can both be changed. |
| **Multilingual Support** | ❌ **Poor**. Stored label is locked to the submission language. |  **Excellent**. Fetch translation dynamically by joining on the slug/value. |  **Excellent**. Fetch translation dynamically by joining on the ID. |
| **Channel Synchronization (Kobo)** | ❌ **Poor**. Requires mapping Kobo XML values back to labels. |  **Perfect**. Kobo uses XML values/slugs directly; zero translation mapping needed during sync. | ⚠️ **Medium**. Requires a DB query to translate Kobo XML value/slugs to database IDs on every import. |
| **Database Portability / Seeding** |  **Good**. Strings are self-contained. |  **Excellent**. Slugs are consistent across all environments (dev, staging, prod). | ❌ **Risk**. Auto-incremented IDs might differ between database instances if seeded in a different order. |

**Decision**: Store **Option Value/Slugs** (`Option.value`).

---

### 2. Location Storage Comparison

| Criteria | Location Name (Current) | Location ID (UUID String) (Proposed) |
| :--- | :--- | :--- |
| **Data Integrity** | ❌ **Weak**. Renaming a location in the database orphans historical references in the `Answer` table. |  **Strong**. UUID is immutable; renaming a location updates the presentation layer dynamically without breaking references. |
| **Namespace Collisions** | ❌ **Risk**. Multiple sub-counties in different basins or counties could share the same name. |  **Perfect**. Each spatial boundary has a unique UUID. |
| **Cascade API Contract** | ❌ **Mismatched**. The question ID is `location_id` and references `/api/v1/reference/sub-counties`, which returns boundary objects. Storing names deviates from storing IDs. |  **Aligned**. Storing the UUID string directly matches the naming of `location_id`. |
| **Reporting / Export** |  **Simple**. Direct string display. | ⚠️ **Requires Query**. Needs a simple SQL JOIN or query resolution to display the name on export, but standard in relational models. |

**Decision**: Store **Location UUID strings** (`SpatialBoundary.id`).

---

## III. Proposed Changes

### 1. Update WhatsApp Service Ingestion
Modify [whatsapp_service.py](file:///Users/galihpratama/Sites/nbd-phase-1/backend/app/services/whatsapp_service.py):
* Store `selected_option.value` in options for the incident answer.
* Store `str(selected_sc.id)` in options for the location answer.

### 2. Update USSD Router Ingestion
Modify [ussd_router.py](file:///Users/galihpratama/Sites/nbd-phase-1/backend/app/routers/ussd_router.py):
* Store `selected_option.value` in options for the incident answer.
* Store `str(selected_sc.id)` in options for the location answer.

### 3. Verification & Test Updates
Update assertions in [test_ussd.py](file:///Users/galihpratama/Sites/nbd-phase-1/backend/tests/test_ussd.py) to expect option slugs and location UUIDs.

---

## IV. Verification Plan

### Automated Tests
* Run full test suite:
  ```bash
  ./dc.sh exec backend python -m pytest tests/
  ```

---

## V. Estimation & Impact
* **Complexity**: Simple
* **Ballpark Estimate**: ~1-2 hours of development and test updates.
