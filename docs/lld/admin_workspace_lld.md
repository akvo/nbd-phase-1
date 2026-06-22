# Low-Level Design (LLD) — Admin Data Workspace API (Sub-Task 2)

Detailed technical specifications for implementing the `/api/v1/admin/` endpoints, PII soft-deletes, dead-letter triaging, and frontend admin API integrations.

---

## 1. API Specifications

All endpoints under this namespace are isolated behind global JWT authentication (`get_current_user`).

### `GET /api/v1/admin/submissions`
Retrieves submissions with admin-specific filters.
* **Query Parameters**:
  - `form_type` (integer, optional) - FormType enum value.
  - `status` (string, optional) - `PENDING`, `APPROVED`, `REJECTED`.
  - `basin` (string, optional) - Case-insensitive filter on Basin name.
* **Response**: `200 OK` List of `DatapointResponse`.

### `PATCH /api/v1/admin/submissions/{id}/status`
Approve or reject a submission. Matches existing submission moderation but registered under the admin namespace.
* **Response**: `200 OK`

### `DELETE /api/v1/admin/submissions/{id}`
PII soft-delete scrub. Restricts to Admin role (`RoleChecker(["Admin"])`).
* **Response**: `204 No Content`
* **Algorithm**:
  1. Retrieve `Datapoint` by `id`. If not found, raise `404 Not Found`.
  2. If `Datapoint.submitter` is present:
     - Check if it represents a UUID. If so, fetch the `Citizen` record by `id == submitter` and nullify `phone_number`.
     - Otherwise, lookup the `Citizen` record by `phone_number == submitter` and nullify `phone_number`.
  3. Traverse all related `Answer` records. If the linked `Question.type` is `image`, `signature`, `attachment`, or `audio` (case-insensitive), nullify `Answer.name`.
  4. Write `AuditLog` row: `action="PII_DELETE"`, `entity_type="submission"`, `entity_id=str(datapoint.id)`.
  5. Commit transaction.

### `GET /api/v1/admin/dead-letters`
Fetch unprocessable/quarantined submissions.
* **Query Parameters**:
  - `status` (string, optional) - `Pending Triage`, `Resolved`, `Discarded`, `Acknowledged`.
  - `source_system` (string, optional) - e.g., `KoboToolbox`, `USSD`, `WHATSAPP`.
* **Response**: `200 OK` List of `DeadLetterResponse`.

### `PATCH /api/v1/admin/dead-letters/{id}`
Acknowledge or triage a quarantined record.
* **Request Body**:
  ```json
  {
    "status": "Acknowledged"
  }
  ```
* **Response**: `200 OK`

### `POST /api/v1/admin/submissions/fgd`
Direct-to-Approved FGD manual submission.
* **Response**: `200 OK`

### `POST /api/v1/admin/submissions/lab-qa`
Direct-to-Approved Lab QA manual submission.
* **Response**: `200 OK`

---

## 2. Frontend Client Specification

### `adminApiClient`
A second Axios client configured in `frontend/src/lib/api.ts`:
* **Base URL**: `/api/v1/admin`
* **Interceptors**: Includes credentials and automatically redirects 401 Unauthorized responses to the `/login` portal.
