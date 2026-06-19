# LLD — Scoring Engine and WQI Calculator

> **Stage 3 of 3 — Low-Level Design**
> Owner: Winston (Architect) / Developer | Target Location: `docs/lld/scoring_engine_lld.md` | References: `docs/prd/scoring_engine_prd.md`, `docs/Final_SDD.md`
> Status: `Approved`

---

## 1. Component Design

We will introduce a new service layer module `backend/app/services/scoring.py` containing the core mathematical equations, and integrate it into the `PATCH /api/v1/submissions/{id}/status` endpoint located in `backend/app/routers/submission_router.py`.

### 1.1 `backend/app/services/scoring.py`
This module will export the following function and helper functions:

```python
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.health_score import HealthScore

def calculate_wqi_and_scores(ph: Decimal, do: Decimal, water_level: str, invasive_macrophytes: Decimal) -> dict:
    """
    Computes quality ratings, weights, WQI score, and group-level means.
    Returns a dictionary containing:
      - wqi_score (physico-chemical group score between 0.00 and 1.00)
      - catchment_score (between 0.00 and 1.00)
      - ecological_score (between 0.00 and 1.00)
      - composite_score (average of the three group scores)
      - health_class ('A', 'B', 'C', 'D', or 'E')
    """
```

#### WQI Formula Implementation Details:
- **Constants**:
  - $S_{\text{pH}} = 8.5$, $S_{\text{DO}} = 5.0$
  - $V_{io,\text{pH}} = 7.0$, $V_{io,\text{DO}} = 14.6$
  - $K = 3.148148$ (derived from $1 / (1/8.5 + 1/5.0)$)
  - $W_{\text{pH}} = 0.3704$, $W_{\text{DO}} = 0.6297$ (adjusted to sum to 1.0001, normalized internally or kept constant)
- **Quality Ratings ($q_n$)**:
  - $q_{\text{pH}} = 100 \times \frac{\text{ph} - 7.0}{1.5}$
  - $q_{\text{DO}} = 100 \times \frac{\text{do} - 14.6}{-9.6}$
- **Physico-chemical Score**:
  - $\text{WQI} = W_{\text{pH}} \times q_{\text{pH}} + W_{\text{DO}} \times q_{\text{DO}}$
  - $\text{Physico-chemical Score} = 1.0 - \frac{\text{WQI}}{100}$
  - Clamped between `0.00` and `1.00`.

- **Catchment Score**:
  - Maps `water_level` values:
    - `"MEDIUM"` &rarr; `1.00`
    - `"HIGH"` &rarr; `0.60`
    - `"LOW"` &rarr; `0.30`
    - Any invalid input default &rarr; `1.00`

- **Ecological Score**:
  - $\text{Ecological Score} = 1.0 - \frac{\text{invasive\_macrophytes}}{100.0}$
  - Clamped between `0.00` and `1.00`.

- **Composite Score & Class**:
  - $\text{Composite Score} = \frac{\text{Physico-chemical Score} + \text{Catchment Score} + \text{Ecological Score}}{3.0}$
  - **Health Class mappings**:
    - $\ge 0.8$ &rarr; `"A"`
    - $\ge 0.6$ and $< 0.8$ &rarr; `"B"`
    - $\ge 0.4$ and $< 0.6$ &rarr; `"C"`
    - $\ge 0.2$ and $< 0.4$ &rarr; `"D"`
    - $< 0.2$ &rarr; `"E"`

### 1.2 Form Type Roles in the Scoring Pipeline

Only certain form types participate in or trigger calculations within the platform's scoring engine:
- **`FormType.CITIZEN_SCIENTIST` (Type 2)**: **[Primary Trigger]** Approving submissions of this type extracts raw pH, DO, water level, and invasive macrophytes percentage to compute the base physico-chemical, catchment, and ecological scores.
- **`FormType.INDIGENOUS_KNOWLEDGE` (Type 3)**: FGD surveys submitted here are aggregated into an **Indigenous Knowledge (IK) Signal** that acts as a soft fuzzy logic adjustment to modify the base scores computed from Type 2.
- **`FormType.CITIZEN_REPORTER` (Type 1)**: Citizen pollution reports are mapped visually but do not trigger scientific or composite scoring calculations.
- **`FormType.LAB_QA` (Type 4)**: Professional lab shadow tests trigger auto-reconciliation check logs against nearby Type 2 data but do not affect baseline health scores.
- **`FormType.EXTERNAL_SATELLITE` (Type 5)**: Ingests external satellite indices for comparison overlays.

---

## 2. Ingestion Integration Flow

In `backend/app/routers/submission_router.py`, inside the `update_submission_status` router (triggered when a submission status updates to `APPROVED` for Form Type 2):

```python
# 1. Insert the raw parameters into sampling_records (existing behavior)
# 2. Run the WQI and Composite scoring computations
from app.services.scoring import calculate_wqi_and_scores

scores = calculate_wqi_and_scores(
    ph=ph_val,
    do=do_val,
    water_level=water_lvl,
    invasive_macrophytes=inv_percent
)

# 3. Create a new HealthScore record and persist to DB
health_score_rec = HealthScore(
    site_id=dp.site_id,
    wqi_score=scores["wqi_score"],
    composite_score=scores["composite_score"],
    ik_signal_value=Decimal("0.00"),  # Placeholder for Phase 2
    adjusted_score=scores["composite_score"],  # Placeholder for Phase 2
    health_class=scores["health_class"]
)
db.add(health_score_rec)
db.flush()
```

---

## 3. Verification Plan

### Automated Tests
Create a new test file `backend/tests/test_scoring.py` containing unit and integration tests verifying:
- **`test_wqi_math_equations`**: Asserts the exact proportionality constant, weights, and quality rating outcomes (e.g. pH=7.8, DO=4.77 returns WQI=84.23 and Physico-chemical score=0.16).
- **`test_group_score_mappings`**: Verifies that Catchment and Ecological group scores are mapped correctly from water levels and macrophyte percentages.
- **`test_composite_score_mean`**: Confirms the simple average aggregate of the three groups.
- **`test_approval_pipeline_scoring_trigger`**: Approves a mock Form Type 2 datapoint and verifies that a new `HealthScore` row is correctly persisted in the database.

### Manual Verification
- Deploy containers and trigger submission approval via the Admin Web UI or Swagger docs, verifying that a `HealthScore` database entry is created for the site with matching calculations.
