# LLD — Defuzzification & Event-Driven Classification

> **Stage 3 of 3 — Low-Level Design**
> Owner: Winston (Architect) / Developer | Target Location: `docs/lld/defuzzification_lld.md` | References: `docs/prd/defuzzification_prd.md`, `docs/Final_SDD.md`
> Status: `Approved`

---

## 1. Score-to-Color Mappings & Classifications

Defuzzified output score $S$ (the `adjusted_score` from `HealthScore` table) is mapped to Health Class ratings and Traffic Light status colors as follows:

| Score Range | Health Class | Traffic Light (status_color) |
|-------------|--------------|-----------------------------|
| $S \ge 0.80$ | `A` | `GREEN` |
| $S \ge 0.60$ and $S < 0.80$ | `B` | `GREEN` |
| $S \ge 0.40$ and $S < 0.60$ | `C` | `YELLOW` |
| $S \ge 0.20$ and $S < 0.40$ | `D` | `YELLOW` |
| $S < 0.20$ | `E` | `RED` |

---

## 2. Real-time Event-Driven Action Mapping

During the validation/approval flow of a `Datapoint` (inside `WetlandScoringHandler.score_submission`):
1. The scoring engine calculates the `adjusted_score`, `health_class`, and maps the status color (`GREEN`, `YELLOW`, or `RED`).
2. We query the `management_actions` table for the site and matching `status_color`.
3. If no recommendations exist for that site and status color, we fall back to a default set of action recommendations (or an empty list).
4. The resolved list of action recommendations is fetched dynamically when querying the site details or site status.

### 2.1 Pydantic Schema Extension
In `backend/app/schemas/spatial.py`, we define the details and management action schemas to match the API contract:

```python
class ManagementActionResponse(BaseModel):
    label: str
    description: str

    model_config = ConfigDict(from_attributes=True)

class SiteStatus(BaseModel):
    composite_score: float
    ik_adjusted_score: float
    traffic_light: str
    health_class: str

class SiteDetailResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    status: SiteStatus | None
    management_actions: list[ManagementActionResponse]
```

---

## 3. Native Execution Integration

All computations run synchronously inside the `update_submission_status` transaction context or using FastAPI `BackgroundTasks`.

```python
# Synchronous native invocation inside submission_router.py
if payload.status == "APPROVED":
    handler = get_handler(FormType(dp.form.type))
    if handler:
        handler.score_submission(db, dp)
```

---

## 4. Verification Plan

### Automated Tests
- `test_defuzzification_classification_mappings`: Verify that different adjusted scores return the correct health class and status color.
- `test_management_actions_linkage`: Seed management actions for a site, approve a submission, and verify the correct actions are linked and returned by the endpoint.
- `test_native_fastapi_execution`: Verify that approving a submission triggers the calculation instantly without Celery.
