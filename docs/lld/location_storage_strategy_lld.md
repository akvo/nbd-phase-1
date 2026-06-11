# Low-Level Design (LLD) — Location ID Storage Strategy

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) | Target Location: `docs/lld/location_storage_strategy_lld.md` | References: `docs/prd/option_storage_strategy_prd.md`
> Status: `Approved`

---

## 1. Overview & Goal

Currently, for USSD and WhatsApp submissions, the incident reporting flow saves the selected sub-county's human-readable **name** (e.g. `["Emurua Dikirr"]`) into the `options` column of the `Answer` table for the `location_id` question.

This LLD proposes to change this to save the location's database **UUID string** (e.g. `["9c3e9812-70b9-48e2-bd12-f9038ba08cd1"]`).

---

## 2. Rationale & Comparison

| Criteria | Location Name (Current) | Location ID (UUID String) (Proposed) |
| :--- | :--- | :--- |
| **Data Integrity** | ❌ **Weak**. Renaming a location in the database orphans historical references in the `Answer` table. |  **Strong**. UUID is immutable; renaming a location updates the presentation layer dynamically without breaking references. |
| **Namespace Collisions** | ❌ **Risk**. Multiple sub-counties in different basins or counties could share the same name. |  **Perfect**. Each spatial boundary has a unique UUID. |
| **Cascade API Contract** | ❌ **Mismatched**. The question ID is `location_id` and references `/api/v1/reference/sub-counties`, which returns boundary objects. Storing names deviates from storing IDs. |  **Aligned**. Storing the UUID string directly matches the naming of `location_id`. |
| **Reporting / Export** |  **Simple**. Direct string display. | ⚠️ **Requires Query**. Needs a simple SQL JOIN or query resolution to display the name on export, but standard in relational models. |

### Recommendation

Store the location **UUID string** in `Answer.options` for the `location_id` question.

---

## 3. Detailed Component Changes

### 3.1 WhatsApp Service Changes

Modify `_save_report` in [whatsapp_service.py](file:///Users/galihpratama/Sites/nbd-phase-1/backend/app/services/whatsapp_service.py):

```python
    # Answer: location (store UUID string instead of name)
    ans_location = Answer(
        datapoint_id=dp.id,
        question_id=q_location.id if q_location else 0,
        name=None,
        options=[str(selected_sc.id)],  # Changed from selected_sc.name
    )
    db.add(ans_location)
```

### 3.2 USSD Router Changes

Modify `handle_ussd` in [ussd_router.py](file:///Users/galihpratama/Sites/nbd-phase-1/backend/app/routers/ussd_router.py):

```python
    ans_location = Answer(
        datapoint_id=dp.id,
        question_id=q_location.id if q_location else 0,
        name=None,
        options=[str(selected_sc.id)],  # Changed from selected_sc.name
    )
    db.add(ans_location)
```

---

## 4. Test Verification Updates

We will update our unit tests to resolve the expected `SpatialBoundary` UUID instead of hardcoded strings:

* **`backend/tests/test_ussd.py`**:

  ```python
  # Instead of:
  # assert ans_location.options == ["Emurua Dikirr"]
  # Use:
  assert ans_location.options == [str(expected_spatial_boundary_id)]
  ```

---

## 5. Estimation

* **Complexity**: Simple
* **Ballpark Estimate**: ~1 hour
