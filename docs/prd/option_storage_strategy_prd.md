# Product Requirements Document (PRD): Option & Location Storage Strategy

**Status**: Draft | **Date**: 2026-06-25 | **Author**: John (PM) / Winston (Architect)

---

## I. Problem Statement

When users complete reporting flows via **WhatsApp** or **USSD**, the system currently stores user choices in the `Answer.value` field as integer menu indices (e.g. `"1"`, `"2"`) or raw text strings.

- Storing integer menu choices (e.g. `"1"`) is ambiguous because menu options can change, be reordered, or differ across languages.
- Storing localized text strings (e.g. `"Industrial Dumping"`) prevents seamless multilingual reporting and analytics.

---

## II. Decision Matrix

| Metric | Option 1: Store Display Text | Option 2: Store Option Value & Location UUID |
| :--- | :--- | :--- |
| **Consistency** | ❌ Menu text can change or be translated into Swahili/English. | ✅ `Option.value` (slug) and `SpatialBoundary.id` (UUID) remain immutable. |
| **Localization** | ❌ Hard to translate historical reports. | ✅ Easy to localize on display by looking up option/boundary metadata. |
| **Reporting / Export** | Direct string display. | Requires SQL JOIN / query resolution (standard relational model). |

**Decision**: Store **Option Slugs** (`Option.value`) for option questions and **Location UUID strings** (`SpatialBoundary.id`) for location questions.

---

## III. Proposed Changes

### 1. Update WhatsApp Service Ingestion
Modify `backend/app/services/whatsapp_service.py`:
* Store `selected_option.value` in options for the incident answer.
* Store `str(selected_sc.id)` in options for the location answer.

### 2. Update USSD Router Ingestion
Modify `backend/app/routers/ussd_router.py`:
* Store `selected_option.value` in options for the incident answer.
* Store `str(selected_sc.id)` in options for the location answer.

### 3. Verification & Test Updates
Update assertions in `backend/tests/test_ussd.py` to expect option slugs and location UUIDs.

---

## IV. Verification Plan

### Automated Tests
Run backend tests via Docker runner:
```bash
./dc.sh exec backend tests
```
