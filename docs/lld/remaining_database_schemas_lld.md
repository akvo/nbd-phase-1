# LLD — Remaining Database Schemas Implementation

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) / Amelia (Developer) | Target Location: `docs/lld/remaining_database_schemas_lld.md`
> Initiative/Epic: Remaining Database Schemas Implementation

---

## 1. Database Schema & ORM Model Designs
We will define five new SQLAlchemy models in `backend/app/models/` and export them via `backend/app/models/__init__.py`.

### 1.1 `Citizen` Table (`citizens`)
- **Columns**:
  - `id`: UUID (Primary Key, default uuid.uuid4)
  - `phone_number`: String(20) (Unique, Index, Non-nullable)
  - `name`: String(100) (Nullable)
  - `role`: String(20) (Non-nullable, Watcher/Scientist constraint)
  - `home_site_id`: UUID (Foreign Key `sites.id`, nullable)
- **Relationships**:
  - `home_site`: relationship to `Site`

### 1.2 `SamplingRecord` Table (`sampling_records`)
- **Columns**:
  - `id`: UUID (Primary Key, default uuid.uuid4)
  - `site_id`: UUID (Foreign Key `sites.id` ON DELETE CASCADE, index, non-nullable)
  - `ph`: Float (Nullable, check constraint: `0.0 <= ph <= 14.0`)
  - `temperature`: Float (Nullable, check constraint: `-10.0 <= temperature <= 60.0`)
  - `dissolved_oxygen`: Float (Nullable, check constraint: `0.0 <= dissolved_oxygen <= 30.0`)
  - `water_level`: String(20) (Nullable)
  - `sampling_date`: DateTime (Non-nullable, default func.now())
- **Relationships**:
  - `site`: relationship to `Site`

### 1.3 `FGDRecord` Table (`fgd_records`)
- **Columns**:
  - `id`: UUID (Primary Key, default uuid.uuid4)
  - `wetland_id`: UUID (Foreign Key `wetlands.id` ON DELETE CASCADE, index, non-nullable)
  - `group_size`: Integer (Non-nullable, check constraint: `group_size >= 1`)
  - `assessment_date`: Date (Non-nullable)
  - `answers_json`: JSONB (Non-nullable)
- **Relationships**:
  - `wetland`: relationship to `Wetland`

### 1.4 `HealthScore` Table (`health_scores`)
- **Columns**:
  - `id`: UUID (Primary Key, default uuid.uuid4)
  - `site_id`: UUID (Foreign Key `sites.id` ON DELETE CASCADE, index, non-nullable)
  - `composite_score`: Float (Non-nullable, check constraint: `0.0 <= composite_score <= 1.0`)
  - `ik_adjusted_score`: Float (Nullable, check constraint: `0.0 <= ik_adjusted_score <= 1.0`)
  - `traffic_light`: String(10) (Non-nullable, Red/Yellow/Green constraint)
  - `health_class`: String(2) (Non-nullable)
  - `calculated_at`: DateTime (Non-nullable, default func.now())
- **Relationships**:
  - `site`: relationship to `Site`

### 1.5 `ManagementAction` Table (`management_actions`)
- **Columns**:
  - `id`: UUID (Primary Key, default uuid.uuid4)
  - `site_id`: UUID (Foreign Key `sites.id` ON DELETE CASCADE, index, non-nullable)
  - `label`: String(150) (Non-nullable)
  - `description`: Text (Non-nullable)
  - `status_color`: String(10) (Non-nullable, Red/Yellow/Green constraint)
  - `created_at`: DateTime (Non-nullable, default func.now())
- **Relationships**:
  - `site`: relationship to `Site`

---

## 2. Alembic Migrations Strategy
- Create a single database migration file under `backend/alembic/versions/`.
- Ensure appropriate naming conventions and table mapping inside `env.py`.

---

## 3. Verification & Testing Plan
- Implement test suites in `backend/tests/test_models.py` verifying constraints, foreign keys, and unique indexes on all five new models.
- Run migrations and confirm local database seeding.
