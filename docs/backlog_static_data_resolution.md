# Design Note: Backlog Resolution for Static Parameters (Phase 1 Scale-up)

**Status:** Proposed | **Date:** 2026-06-23 | **Author:** Amelia (Developer)

---

## 1. Context
During the Phase 1 implementation of **[FE Mobile] Task 3: Detail View - High-Level Metrics (4x Grid)**, we successfully migrated core parameters (pH, Temperature, Dissolved O₂, and Water Level) to a dynamic, domain-agnostic `metrics` dictionary. 

However, some parameters remain as static mock data in the user interface (specifically inside the score breakdown and raw sampling table) due to current database schema limitations. This document outlines the technical steps required to make these parameters dynamic in future tasks.

---

## 2. Dynamic Metric Resolution: Turbidity & Macroinvertebrates

Currently, the frontend [site-drawer.tsx](file:///Users/galihpratama/Sites/nbd-phase-1/frontend/src/components/ui/site-drawer.tsx) hardcodes **Turbidity** (`38 NTU`) and the **Macroinvertebrate** index (`0.48 index`) in the raw sampling method table because the `sampling_records` table does not contain fields for them.

Since the frontend is already refactored to dynamically render items inside `site.details.metrics`, we can resolve this with zero frontend code modifications:

### Step 2.1: Database Schema Expansion
Create a new Alembic migration to add the missing parameters to the `sampling_records` table:
```sql
ALTER TABLE sampling_records ADD COLUMN turbidity_value NUMERIC(5, 2) NULL;
ALTER TABLE sampling_records ADD COLUMN macroinvertebrates_value NUMERIC(4, 2) NULL;
```

### Step 2.2: Backend Model & Schema Updates
1. **SQLAlchemy Model**: Update `SamplingRecord` in `backend/app/models/sampling_record.py` to declare the new columns.
2. **Pydantic Schema**: Update `SamplingRecordBase` schemas to include and validate these optional values.
3. **Public Router**: Update `list_sites` and `get_site` in `backend/app/routers/public_router.py` to append the new metrics into the `metrics` map:
   ```python
   if latest_sampling.turbidity_value is not None:
       metrics_map["turbidity"] = {
           "value": float(latest_sampling.turbidity_value),
           "unit": "NTU",
           "status": "Normal", # or define threshold logic
           "label": "Turbidity",
           "icon": "Eye"
       }
   ```

---

## 3. Dynamic Score Resolution: Governance Index

The Governance Index progress bar inside the health breakdown card displays a hardcoded value of `0.55` because there is no corresponding database table or scoring engine pipeline for Governance.

### Step 3.1: Define Governance Survey Schema
Create a new database table and Pydantic schema for governance audits:
- **Table name**: `governance_records`
- **Columns**: `id` (UUID), `wetland_id` (UUID), `score` (Numeric), `audit_date` (DateTime).

### Step 3.2: Scoring Engine Integration
Update the composite scoring engine (`app/services/scoring.py`):
1. Query the latest `GovernanceRecord` for the wetland.
2. Compute the governance mean and incorporate it into the final fuzzy logic class classification.
3. Return the calculated governance score in the API response under `details.governance.group_score` instead of returning a static fallback.
