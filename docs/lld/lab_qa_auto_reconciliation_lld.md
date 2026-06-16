# Low-Level Design (LLD) — Lab QA Auto-Reconciliation Engine

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) | Target Location: `docs/lld/lab_qa_auto_reconciliation_lld.md` | References: `docs/prd/lab_qa_auto_reconciliation_prd.md`, `docs/lld/dynamic_datapoints_lld.md`
> Status: `Approved`

---

## 1. Physical Database Schema

To support automated control comparison and retraining auditing, we define the following schema.

### 1.1 `reconciliation_log` Table
- `id`: UUID (Primary Key, default=uuid4)
- `citizen_id`: UUID (Foreign Key -> `citizens.id`, ON DELETE CASCADE, Not Null)
- `citizen_datapoint_id`: UUID (Foreign Key -> `sampling_records.id`, ON DELETE CASCADE, Not Null)
- `lab_datapoint_id`: INT (Foreign Key -> `datapoint.id`, ON DELETE CASCADE, Not Null)
- `parameter_name`: VARCHAR(50) (Not Null) — e.g., `'ph_value'`, `'temp_value'`, `'do_value'`
- `citizen_value`: NUMERIC(6, 2) (Not Null)
- `lab_value`: NUMERIC(6, 2) (Not Null)
- `calculated_variance`: NUMERIC(6, 2) (Not Null) — calculated as percentage variance
- `status`: VARCHAR(20) (Not Null) — `'DISCREPANT'` or `'RECONCILIATION_OK'`
- `reconciled_at`: TIMESTAMP (Default=now(), Not Null)

**Indices & Constraints**:
- Index: `idx_reconciliation_log_citizen_id` on `citizen_id`
- Index: `idx_reconciliation_log_status` on `status`
- Unique Constraint: `uq_reconciliation_log_pair` on `(citizen_datapoint_id, lab_datapoint_id, parameter_name)` to prevent duplicate comparisons of the same parameter between the same two datapoints.

---

## 2. Model Modifications & Extensions

### 2.1 `Citizen` Model (`app/models/citizen.py`)
Add a dynamic SQLAlchemy hybrid property / expression resolver to calculate `needs_retraining` on the fly without adding a column to the `citizens` table.

```python
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import exists, and_

class Citizen(Base):
    # ... existing columns ...

    @hybrid_property
    def needs_retraining(self) -> bool:
        """
        Dynamically returns True if there are any active 'DISCREPANT'
        records for this citizen in the reconciliation log.
        """
        from app.models.reconciliation import ReconciliationLog
        # Inline lookup / object-level property resolver
        return any(log.status == "DISCREPANT" for log in self.reconciliation_logs)

    @needs_retraining.expression
    def needs_retraining(cls):
        """
        SQL-level expression mapping for queries/filtering.
        """
        from app.models.reconciliation import ReconciliationLog
        return exists().where(
            and_(
                ReconciliationLog.citizen_id == cls.id,
                ReconciliationLog.status == "DISCREPANT"
            )
        )
```

Add the corresponding relationship in `Citizen`:
```python
reconciliation_logs = relationship(
    "ReconciliationLog",
    back_populates="citizen",
    cascade="all, delete-orphan",
)
```

---

## 3. Reconciliation Service Logic

### 3.1 Parameter Names Mapping
Since citizen sampling records have fixed columns (`ph_value`, `temp_value`, `do_value`) and Lab QA submissions have dynamic questions/answers, the service maps parameters by checking if the Lab QA question `name` or `label` contains specific substrings (case-insensitive):
- **pH**: matches `"ph"` (e.g. `"ph"`, `"pH Level"`, `"ph_value"`)
- **Temperature**: matches `"temp"` or `"temperature"` (e.g. `"temp"`, `"temp_value"`, `"Water Temperature (°C)"`)
- **Dissolved Oxygen**: matches `"do"`, `"dissolved"`, or `"oxygen"` (e.g. `"do"`, `"do_value"`, `"Dissolved Oxygen (mg/L)"`)

### 3.2 Comparison Pipeline & Mathematical Model
The service runs in a transaction context:
1. **Lab Datapoint Retrieval**: Retrieve the newly approved Lab QA `Datapoint` and its associated `Answer` entries.
2. **Citizen Record Lookup**: Query for citizen `SamplingRecord`s where:
   - `SamplingRecord.site_id == LabQA.site_id`
   - `abs(SamplingRecord.sampled_at - LabQA.created_at) <= 90 days`
3. **Citizen Identification**: For each matched `SamplingRecord`, find the registered `Citizen`(s) associated with that `site_id`.
4. **Calculations & Logging**:
   - For each parameter (pH, Temp, DO) present in both records:
     - If `lab_val == 0.0` or `lab_val is None`, skip comparison to avoid division by zero.
     - Calculate variance:
       $$\text{variance} = \frac{|\text{citizen\_val} - \text{lab\_val}|}{\text{lab\_val}} \times 100$$
     - Compare against threshold `RECONCILIATION_VARIANCE_THRESHOLD` (default: `20.0`).
     - Set status to `'DISCREPANT'` if variance > threshold, else `'RECONCILIATION_OK'`.
     - Insert a new `ReconciliationLog` entry.

---

## 4. Integration Details

### 4.1 Trigger Point
The reconciliation process will be triggered directly within the `/api/v1/internal/lab-qa` endpoint in `app/routers/internal_router.py` after the Lab QA datapoint and answers are successfully committed to the database.

---

## 5. Verification Plan

### 5.1 Unit Tests
- Test exact match (0% variance -> `RECONCILIATION_OK`)
- Test high variance (>20% variance -> `DISCREPANT` and updates `needs_retraining = true` dynamically)
- Test handling of 90-day time window boundaries
- Test division-by-zero prevention when lab value is `0.0`
