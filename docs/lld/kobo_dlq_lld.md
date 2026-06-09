# Low-Level Design (LLD) — KoboToolbox Payload Mapper & Dead-Letter Queue (DLQ)

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) | Target Location: `docs/lld/kobo_dlq_lld.md` | References: `docs/prd/kobo_dlq_prd.md`, `docs/database_schema.md`
> Status: `Approved`

---

## 1. Component Overview

This component implements a validation wrapper around the KoboToolbox ingestion pipeline. It enforces strict physical bounds on incoming citizen science data and catches schema mismatches. Rather than failing the synchronization task, corrupt payloads are quarantined in the `dead_letters` database table, and an aggregated email summary is sent to all users with the `'Admin'` role.

---

## 2. Ingestion & Validation Flow

### 2.1 Bounds Checks

For each mapped answer:
1. **pH Validation**: If the question machine name matches `'ph'` (case-insensitive), the system checks if the answer value is between `2.0` and `10.0` inclusive.
2. **Water Temperature Validation**: If the question machine name matches `'water_temp'` or `'water_temperature'` (case-insensitive), the system checks if the value is between `5.0` and `50.0` inclusive.

If any value violates these bounds, a `ValueError` is raised, triggering quarantine.

### 2.2 Ingestion Exception Handling

Within `sync_kobo_submissions` loop in `backend/app/services/kobo.py`:

```python
sync_failures = []  # Aggregates failures: [{"uuid": ..., "error": ..., "payload": ...}]

for sub in submissions:
    # ... idempotency & parsing ...
    try:
        # Establish savepoint or sub-transaction for safety
        with db.begin_nested():
            # Create Datapoint
            # Map questions & validate bounds
            # Add answers
            # Flush & nested commit
    except Exception as e:
        # Roll back nested transaction for this submission only
        logger.error(f"Ingestion failed for submission {sub_uuid}: {e}")

        # Capture raw payload and record in DeadLetter table
        dead_letter = DeadLetter(
            source_system="kobotoolbox",
            raw_payload=sub,
            error_reason=str(e),
            status="Pending Triage"
        )
        db.add(dead_letter)
        db.commit()

        sync_failures.append({
            "uuid": sub_uuid_str,
            "error": str(e),
            "submitted_by": sub.get("_submitted_by", "Unknown")
        })
```

---

## 3. Email Aggregation & Recipient Resolution

### 3.1 Resolving Admin Emails

To prevent hardcoded configurations, the alert recipients are queried dynamically from the `users` table:

```python
from app.models.user import User

admins = db.query(User.email).filter(
    func.lower(User.role) == "admin",
    User.is_active == True
).all()
admin_emails = [a.email for a in admins]
```

### 3.2 Aggregated Email Format

If `sync_failures` contains items, the service constructs a single summary email:

* **Subject**: `[NBD Portal] Kobo Ingestion Failures Alert`
* **Content**: An HTML table summarizing the failed submissions:
  - Submission UUID
  - Submitter Name
  - Reason / Validation Exception

This email is sent using the existing `EmailService.send_email_async` or synchronous equivalent.

---

## 4. Verification Plan

### 4.1 Automated Tests

We will write new tests in `backend/tests/test_kobo_sync.py`:
- `test_kobo_bounds_validation_failure`: Ingests a mock payload with out-of-bounds pH (e.g., `11.5`) and asserts that:
  - The datapoint is not persisted.
  - A `DeadLetter` record is created with `error_reason` containing the validation error.
  - Sync does not crash.
- `test_kobo_schema_mismatch_failure`: Ingests a mock payload with invalid types (e.g., string for a numeric field) and verifies quarantine.
- `test_kobo_sync_aggregated_email`: Mock the `EmailService` and assert that a single aggregated email listing all failures is sent to the active administrator emails.
