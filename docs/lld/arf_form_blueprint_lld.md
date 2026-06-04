# LLD — ARF Form Blueprint (Dynamic Form Structures)

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) | Target Location: `docs/lld/arf_form_blueprint_lld.md` | References: `docs/prd/arf_form_blueprint_prd.md`
> Status: `Draft`

---

## 1. Overview & Scope

**Component / Module**:
Dynamic Form Engine Schema & SQLAlchemy Models (`Form`, `QuestionGroup`, `Question`, `Option`, `FormPublishedVersion`).

**PRD References**:
FR-001, FR-002, FR-003, FR-004.

**Out of Scope for this LLD**:
- Ingestion models/workflows like `datapoints` and `answers` submissions.
- Form definition/validation editing API endpoints.

---

## 2. Component & Class Design

We design Layer C (Dynamic Form Engine) models to map the Django reference structure to SQLAlchemy ORM models.

```mermaid
classDiagram
    class Form {
        +int id PK
        +string name
        +int version
        +uuid uuid
        +int parent_id FK
        +int type
        +int status
        +timestamp published_at
        +int previous_version_id FK
        +int active_version_id FK
    }

    class QuestionGroup {
        +int id PK
        +int form_id FK
        +string name
        +string label
        +bigint order
        +boolean repeatable
        +string repeat_text
        +timestamp deleted_at
    }

    class Question {
        +int id PK
        +int form_id FK
        +int question_group_id FK
        +bigint order
        +string label
        +string short_label
        +string name
        +int type
        +boolean meta
        +boolean required
        +jsonb rule
        +jsonb dependency
        +string dependency_rule
        +jsonb api
        +jsonb extra
        +jsonb tooltip
        +jsonb fn
        +jsonb pre
        +boolean display_only
        +timestamp deleted_at
    }

    class Option {
        +int id PK
        +int question_id FK
        +bigint order
        +string label
        +string value
        +boolean other
        +string color
    }

    class FormPublishedVersion {
        +int id PK
        +int form_id FK
        +int version
        +jsonb schema
        +timestamp published_at
        +uuid published_by_id FK
    }

    Form "1" *-- "many" QuestionGroup : contains
    QuestionGroup "1" *-- "many" Question : contains
    Question "1" *-- "many" Option : has choices
    Form "1" *-- "many" FormPublishedVersion : versions
```

### Class Responsibilities
- `Form`: Stores form-level metadata, status state machine, version counters, and historical chain tracking.
- `QuestionGroup`: Group sections inside forms. Supports soft delete tracking via `deleted_at`.
- `Question`: Question details, field validators, input rules, dependencies, and soft delete tracking.
- `Option`: Select choices unique per question value.
- `FormPublishedVersion`: Deep immutable copies of form questions configurations.

---

## 3. Sequence Diagrams

### 3.1 Retrieve Form Schema
```mermaid
sequenceDiagram
    actor Client
    participant Router as form_router
    participant DB as PostgreSQL
    Client->>Router: GET /api/v1/forms/{form_id}
    Router->>DB: Query Form (where deleted_at is null on associations)
    DB-->>Router: Form, Groups, Questions, Options
    Router-->>Client: 200 OK (Form Definition Schema JSON)
```

---

## 4. API Contracts

### `POST /api/v1/forms` (Admin only)
**Purpose**: Create a draft form.
**Request Body**:
```json
{
  "name": "Physico-Chemical Water Probe Form",
  "type": 1,
  "status": 1
}
```
**Success Response** `201 Created`:
```json
{
  "id": 1,
  "name": "Physico-Chemical Water Probe Form",
  "version": 1,
  "uuid": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "type": 1,
  "status": 1
}
```

---

## 5. Database Schema & Index Strategy

### Schema ER Diagram
```mermaid
erDiagram
    form ||--o{ question_group : contains
    question_group ||--o{ question : contains
    question ||--o{ option : has
    form ||--o{ form_published_version : publishes

    form {
        integer id PK
        text name
        integer version
        uuid uuid
        integer parent_id FK
        integer type
        integer status
        timestamp published_at
        integer previous_version_id FK
        integer active_version_id FK
    }
    question_group {
        integer id PK
        integer form_id FK
        varchar name
        text label
        bigint order
        boolean repeatable
        varchar repeat_text
        timestamp deleted_at
    }
    question {
        integer id PK
        integer form_id FK
        integer question_group_id FK
        bigint order
        text label
        text short_label
        varchar name
        integer type
        boolean meta
        boolean required
        jsonb rule
        jsonb dependency
        varchar dependency_rule
        jsonb api
        jsonb extra
        jsonb tooltip
        jsonb fn
        jsonb pre
        boolean display_only
        timestamp deleted_at
    }
    option {
        integer id PK
        integer question_id FK
        bigint order
        text label
        varchar value
        boolean other
        text color
    }
    form_published_version {
        integer id PK
        integer form_id FK
        integer version
        jsonb schema
        timestamp published_at
        uuid published_by_id FK
    }
```

### Index Strategy

| Table | Index | Type | Rationale |
|---|---|---|---|
| `form` | `(uuid)` | Unique | UUID-based queries |
| `question_group` | `(form_id, name)` WHERE `deleted_at IS NULL` | Unique B-Tree | Allows recreating groups with same name if deleted |
| `question` | `(form_id, name)` WHERE `deleted_at IS NULL` | Unique B-Tree | Allows recreating questions with same name if deleted |
| `option` | `(question_id, value)` | Unique B-Tree | Enforce option uniqueness per question value |
| `form_published_version` | `(form_id, version)` | Unique B-Tree | Fast lookup of version snapshots |

---

## 6. Logic & Algorithms

### Soft Delete Queries
SQLAlchemy queries on `QuestionGroup` and `Question` must default to adding `deleted_at IS NULL` in their filters to prevent returning deleted elements.
```python
# Query pattern helper
db.query(QuestionGroup).filter(
    QuestionGroup.form_id == form_id,
    QuestionGroup.deleted_at.is_(None)
).all()
```

---

## 7. Error Handling & Edge Cases

| Scenario | Detection | Response | Fallback |
|---|---|---|---|
| Creating duplicate question name | Conditional index violation | 400 Bad Request ("Question name already active") | — |
| Fetching retired schema version | Snapshot version check | Load matching `form_published_version.schema` | Fail gracefully |

---

## Exit Criterion

> [!IMPORTANT]
> This LLD MUST be reviewed in a tech design review session before implementing.

**Design Review Checklist**:
- [ ] All FR-xxx references from the PRD are addressed
- [ ] Database schema mapped accurately to SQLAlchemy types
- [ ] Uniqueness constraints and indices configured
- [ ] Soft deletion queries defined
