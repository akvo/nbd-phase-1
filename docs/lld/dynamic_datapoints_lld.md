# Low-Level Design (LLD) — Dynamic Datapoints & Identity Model

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) | Target Location: `docs/lld/dynamic_datapoints_lld.md` | References: `docs/prd/dynamic_datapoints_prd.md`, `docs/database_schema.md`
> Status: `Approved`

---

## 1. Physical Database Schema

To support polymorphic survey/submission anchors and secure identity tier classification, we define the following tables:

### 1.1 `users` Table
- `id`: UUID (Primary Key, default=uuid4)
- `email`: VARCHAR(255) (Unique, Indexed, Not Null)
- `role`: VARCHAR(50) (Not Null) — Admin, Reviewer, or Partner
- `organization`: VARCHAR(255) (Nullable)
- `password_hash`: VARCHAR(255) (Nullable) — Only used for Partner tier email/password login
- `is_active`: BOOLEAN (Default=True, Not Null)

### 1.2 `datapoint` Table
- `id`: INT (Primary Key, Serial)
- `uuid`: UUID (Unique, Default=uuid4, Not Null)
- `form_id`: INT (Foreign Key -> `form.id`, ON DELETE RESTRICT, Not Null)
- `published_version_id`: INT (Foreign Key -> `form_published_version.id`, ON DELETE SET NULL, Nullable)
- `name`: TEXT (Nullable)
- `basin_id`: UUID (Foreign Key -> `basins.id`, ON DELETE SET NULL, Nullable)
- `wetland_id`: UUID (Foreign Key -> `wetlands.id`, ON DELETE SET NULL, Nullable)
- `site_id`: UUID (Foreign Key -> `sites.id`, ON DELETE SET NULL, Nullable)
- `geo`: JSONB (Nullable)
- `created_by_id`: UUID (Foreign Key -> `users.id`, ON DELETE SET NULL, Nullable)
- `created_at`: TIMESTAMP (Default=now(), Not Null)
- `updated_at`: TIMESTAMP (Nullable)
- `duration`: INT (Default=0, Not Null)
- `submitter`: VARCHAR(255) (Nullable)
- `status`: VARCHAR(20) (Default='PENDING', Not Null)
- **Check Constraint**: `chk_polymorphic_anchor` enforces that exactly one of `basin_id`, `wetland_id`, or `site_id` is specified.
  ```sql
  CHECK ( (basin_id IS NOT NULL)::int + (wetland_id IS NOT NULL)::int + (site_id IS NOT NULL)::int = 1 )
  ```

### 1.3 `answer` Table
- `id`: INT (Primary Key, Serial)
- `datapoint_id`: INT (Foreign Key -> `datapoint.id`, ON DELETE CASCADE, Not Null)
- `question_id`: INT (Foreign Key -> `question.id`, ON DELETE CASCADE, Not Null)
- `name`: TEXT (Nullable)
- `value`: DOUBLE PRECISION (Nullable)
- `options`: JSONB (Nullable)
- `created_by_id`: UUID (Foreign Key -> `users.id`, ON DELETE SET NULL, Nullable)
- `created_at`: TIMESTAMP (Default=now(), Not Null)
- `updated_at`: TIMESTAMP (Nullable)
- `index`: INT (Default=0, Not Null)
- **Unique Constraint**: `unique_datapoint_question_index` guarantees that answers for the same question within a repeatable block are uniquely indexed.
  ```sql
  UNIQUE (datapoint_id, question_id, index)
  ```

---

## 2. API Endpoints Contract

### 2.1 User Management
- `POST /api/v1/users`: Create a new user (with password hashing if password provided)
- `GET /api/v1/users`: List users (optional filter by email)
- `GET /api/v1/users/{user_id}`: Get user by ID
- `PUT /api/v1/users/{user_id}`: Update user attributes (role, active state, password, organization, email)

### 2.2 Ingestion & Retrieval
- `POST /api/v1/submissions`: Submit questionnaire answers anchored to exactly one geographic level.
  - Returns `201 Created` on success.
  - Returns `422 Unprocessable Entity` if 0 or multiple geographic anchors are provided.
- `GET /api/v1/submissions`: Retrieve / list submissions (supporting query filters by form_id, basin_id, wetland_id, site_id, and status).
