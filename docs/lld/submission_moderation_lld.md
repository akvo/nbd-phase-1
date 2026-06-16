# Low-Level Design (LLD) — Submission Moderation & Approval

Detailed technical specifications for implementing the submission moderation action and dynamic mapping to the `sampling_records` table.

---

## 1. API Specifications

### `PATCH /api/v1/submissions/{id}/status`

Admins will call this endpoint to approve or reject a generic submission datapoint.

* **Path Parameter**: `id` (integer) - The unique ID of the Datapoint.
* **Request Body**:

  ```json
  {
    "status": "APPROVED"
  }
  ```

  *(Status must be either `"APPROVED"` or `"REJECTED"`)*

* **Response**: `200 OK`

  ```json
  {
    "id": 123,
    "status": "APPROVED",
    "message": "Submission status updated successfully"
  }
  ```

* **Authentication**: Admin privileges required.

---

## 2. Database & Data Model Mapping

### Status Validation & Datapoint Update

1. Retrieve the `Datapoint` record by `id`.
2. Check current status. If it's already `'APPROVED'` or `'REJECTED'`, raise `400 Bad Request` to prevent redundant processing.
3. Update `Datapoint.status` column to the new status.

### Site ID & Answer Retention

* **Dual Storage**: For any submission (frontend or Kobo), the selected `site_id` is saved in two locations:
  1. **Answer Table**: Stored as a raw response value in the `answers` table under the corresponding site question ID/name for form auditability.
  2. **Datapoint Table**: Resolved to a database `Site` and assigned to the `site_id` foreign key on the `datapoint` table to support moderation mapping and relational queries.

### Dynamic Mapping to `SamplingRecord` (Only on `APPROVED`)

When the new status is `'APPROVED'`, query all `Answer` records linked to the `Datapoint` and map them to `SamplingRecord`:

| Answer Question Identifier | Target `SamplingRecord` Field | Type | Required/Optional |
| --- | --- | --- | --- |
| `ph` | `ph_value` | Numeric(4,2) | Optional (Null if missing) |
| `temp` | `temp_value` | Numeric(4,1) | Optional (Null if missing) |
| `do` | `do_value` | Numeric(4,1) | Optional (Null if missing) |
| `invasive_percent` | `invasive_macrophytes` | Numeric(5,2) | Optional (Null if missing, default 0.00) |
| `water_level` | `water_level` | String(10) | Optional (Default to `'MEDIUM'`) |

* **Metadata Fields**:
  * `site_id`: Derived directly from `Datapoint.site_id` (If missing, raise `400 Bad Request`).
  * `sampled_at`: Derived from `Datapoint.created_at`.

### Triggering Reconciliation

After saving the `SamplingRecord`:

1. Find any approved Lab QA Datapoints (`form.type == 4`) matching the same `site_id` within the 90-day window (`sampled_at - 90 days` to `sampled_at + 90 days`).
2. For each Lab QA datapoint found, execute `reconcile_lab_datapoint(db, lab_dp.id)` to recalculate and log any parameter discrepancies.

---

## 3. Frontend Integration

### Endpoint Call in `DataOverviewPage`

Replace the local state modifications in [page.tsx](../../frontend/src/app/admin/data/page.tsx):

```typescript
  const handleApprove = async (id: string) => {
    try {
      const cleanId = id.replace('DP-', '');
      await apiClient.patch(`/submissions/${cleanId}/status`, { status: 'APPROVED' });
      setSubmissions(prev =>
        prev.map(sub => (sub.id === id ? { ...sub, status: 'Approved' } : sub))
      );
    } catch (err) {
      console.error("Failed to approve submission", err);
    }
  };
```

---

## 4. Error Handling & Edge Cases

* **Missing Site ID**: If a citizen scientist submission somehow has `site_id` as NULL, the approval fails and returns an HTTP `400 Bad Request` because a `SamplingRecord` requires a site reference.
* **Invalid Option Value**: If `water_level` answer does not match `HIGH`, `MEDIUM`, or `LOW`, normalise the value or default it to `MEDIUM`.

---

## 5. KoboToolbox Integration Setup (TODO / Pending Dev)

For submissions ingested from KoboToolbox to correctly resolve `site_id` during sync, the corresponding Kobo XLSForm must show the site selection dropdown:

* **Option A (Media CSV File - Recommended)**: Export all monitoring sites from the database to a CSV (e.g. `sites.csv`) containing columns `name` (site code) and `label` (site name). Upload it as a Media file in Kobo settings, and define the XLSForm question type as `select_one_from_file sites.csv`.
* **Option B (Static Choices)**: Add static site records directly to the XLSForm `choices` sheet under list name `site_list` with values matching database site codes.
* **Payload Key Mapping**: In the XLSForm, the question key must be named `site_id` (or `site`, `site_code`, `location_id`) so the backend sync engine (`kobo.py`) successfully matches it and sets the `site_id` on the ingested datapoint.
