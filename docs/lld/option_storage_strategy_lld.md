# LLD — Option & Location Storage Strategy

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) / Amelia (Developer) | Target Location: `docs/lld/option_storage_strategy_lld.md`
> Initiative/Epic: Option & Location Storage Strategy

---

## 1. Data Contract Modifications

### 1.1 Answer Options Payload
- Submissions from WhatsApp, USSD, and Kobo channels must write standardized machine-readable Option Slugs/Values into `Answer.options` array column (e.g. `["smell"]` or `["2"]` instead of English/Swahili text labels `["Smell"]`).

### 1.2 Location Answers
- Location answers must write the `SpatialBoundary.id` UUID string (e.g., `["9c3e9812-70b9-48e2-bd12-f9038ba08cd1"]`) into the options database field rather than the raw sub-county string name.

---

## 2. Service Component Updates

### 2.1 WhatsApp Ingestion (`backend/app/services/whatsapp_service.py`)
- Locate where choices/options and spatial boundaries are mapped and ingested into answer records.
- Retrieve the option value slug (`option.value`) and location UUID (`str(boundary.id)`) and save them into the `Answer.options` JSONB list.

### 2.2 USSD Session Router (`backend/app/routers/ussd_router.py`)
- Locate option selection handler steps and replace saving raw user text choices with saving option slugs (`selected_option.value`).
- Map selected sub-county option ID selection back to database entity UUID string (`str(sub_county.id)`) before saving.

---

## 3. Verification & Testing Plan
- Update mock submission fixtures inside backend tests (`tests/test_ussd.py` and `tests/test_whatsapp.py`) to verify option value slugs and location UUID strings are correctly written to the database.
- Run tests via `./dc.sh exec backend python -m pytest tests/` to confirm.
