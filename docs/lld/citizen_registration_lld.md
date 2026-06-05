# LLD — Citizen Registration & Management

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Tech Lead / Senior Engineer | Target Location: `docs/lld/citizen_registration_lld.md` | References: `docs/prd/citizen_registration_prd.md`
> Status: `Draft`

---

## 1. Overview & Scope

**Component / Module**:
`app.routers.citizen_router` and `app.schemas.citizen` schemas.

**PRD References**:
FR-001, FR-002, FR-003.

**SOLID Compliance**:
- **SRP**: The citizen router manages strictly citizen record registration and reading.
- **DIP**: Depends on the SQLAlchemy Session injection via `get_db`.

---

## 2. API Contracts

### `POST /api/v1/citizens`
- **Role Requirement**: `Admin`
- **Request Body**:
  ```json
  {
    "phone_number": "+254700000000",
    "site_id": "9bd4883b-ba50-42a7-8277-0fc5e44e0ffe",
    "role": "WATCHER"
  }
  ```
- **Success Response** `201 Created`:
  ```json
  {
    "id": "76ec2a00-1c3b-489e-9d22-1d54be2e0ffd",
    "phone_number": "+254700000000",
    "site_id": "9bd4883b-ba50-42a7-8277-0fc5e44e0ffe",
    "role": "WATCHER"
  }
  ```

### `GET /api/v1/citizens`
- **Role Requirement**: `Reviewer` or `Admin`
- **Query Parameters**:
  - `role` (Optional): Filter by role (`WATCHER` or `SCIENTIST`).
  - `site_id` (Optional): Filter by site UUID.
- **Success Response** `200 OK`:
  ```json
  [
    {
      "id": "76ec2a00-1c3b-489e-9d22-1d54be2e0ffd",
      "phone_number": "+254700000000",
      "site_id": "9bd4883b-ba50-42a7-8277-0fc5e44e0ffe",
      "role": "WATCHER"
    }
  ]
  ```

---

## 3. Database Indexing Strategy
To ensure that lookups during ingestion webhooks are fast and scale-adaptive:
- Create a B-Tree index on the `phone_number` column in the `citizens` table.

```sql
CREATE INDEX idx_citizens_phone ON citizens (phone_number);
```
