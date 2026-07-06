# PRD — Decoupled & Domain-Agnostic Analysis Layer

- **Stage 2 of 3 — Documentation Hierarchy**
- **Owner**: John (Product Manager) & Winston (Architect)
- **Status**: Proposed

---

## I. Overview & Goal

### Problem Statement

Currently, the platform's analysis, scoring engine, database schemas, API routes, and user interface are tightly coupled to the **Wetland** monitoring domain. Hardcoded references to physico-chemical metrics (pH, dissolved oxygen, temperature, water level) and specific wetland scoring breakdown parameters make it difficult to introduce other domain-specific monitoring systems (e.g. Forest, Trees, Soil quality) without major code modifications and disruptions.

### Core Metric

Reduce the developer effort to introduce a new monitoring domain from **~40 developer hours** (requiring extensive route, schema, database, and UI updates) to **<2 developer hours** (requiring only writing a scoring handler and registering it).

---

## II. User Stories & Flows

### Personas

- **Domain Administrator**: Wants to add a new domain (e.g., Forest Monitoring) with unique metrics, scoring logic, and UI display configurations.
- **Portal User**: Wants to open different monitoring stations (Wetland vs. Forest) and see relevant parameters, breakdown categories, and qualitative signals automatically rendered.

---

## III. Scope Guardrails

### Must-Have

1. **Database Schema Expansion**:
   - Add a `domain` column (string or enum, defaulting to `"wetland"`) to the `wetlands` table (which represents parent monitoring areas) to associate sites and scoring models with specific domains.
   - Add a `domain` column (string or enum, defaulting to `"wetland"`) to the `Form` model (representing the forms table) to categorize forms and form submissions by domain.
2. **Centralized Domain Constants**:
   - Backend: Define a central Python `enum` or Class constant (e.g., `MonitoringDomain`) in the codebase containing `WETLAND = "wetland"`, `FOREST = "forest"`, etc., to manage domain keys centrally.
   - Frontend: Define a corresponding TypeScript `enum` or constant mapping to ensure type-safe domain checks.
3. **Dynamic Scoring Engine Registry**: Modify the scoring registry to lookup handlers using a compound key of `(domain, form_type)` (e.g. `("wetland", FormType.CITIZEN_SCIENTIST)` vs `("forest", FormType.CITIZEN_SCIENTIST)`). This allows different domains to trigger custom mathematical analysis flows for both shared and domain-specific form types.
4. **Decoupled API Response**: Update the site details routes to return a dynamic `ui_config` configuration describing:
   - Category progress bars (label, icon, key, default scores).
   - Parameters table (labels, units, statuses).
   - Qualitative grids (indicators, status mappings).
5. **Dynamic Frontend Rendering**: Update `SiteDrawer` to read the backend `ui_config` layout and dynamically map and render elements instead of referencing hardcoded wetland properties.
6. **Domain-Agnostic Calculations & Reconciliation**:
   - Refactor `backend/app/services/reconciliation.py` to compare citizen scientist and lab parameters dynamically via JSONB keys rather than hardcoded columns.
   - Refactor the scoring handlers (`app/services/scoring/handlers/wetland.py`) to instantiate the updated models (`SamplingRecord`, `FgdRecord`, `HealthScore`) using JSONB payloads.
   - Refactor seed script `backend/app/seeds/seed_fake_submissions.py` to instantiate `HealthScore` using the new JSONB `breakdown` schema.
   - Refactor backend test suites (`test_public_api.py`, `test_scoring.py`, `test_remaining_schemas.py`, `test_reconciliation.py`, `test_submission_moderation.py`) to verify the updated JSONB models.

### Out of Scope (Phase 1)

- Creating admin-facing forms to build custom layouts dynamically via UI.
- Fully migrating the `wetlands` table name to `monitoring_areas` (this will be handled as an alias/virtual transition to maintain database compatibility).

---

## IV. Technical Architecture & Data Model

### Data Model & Fallback Architecture

To decouple the platform from the wetland domain while maintaining compatibility with existing ingestion pipelines, seeders, and tests, we implement a **SQLAlchemy Hybrid Property Fallback Strategy**.

The tables are refactored to generic JSONB fields at the database layer. However, the ORM models expose the legacy properties using getter/setter hybrid properties that map values dynamically.

1. **Add `domain` to `wetlands`**:

```python
domain = Column(String(50), nullable=False, server_default="wetland")
```

2. **Add `domain` to `forms`**:

```python
domain = Column(String(50), nullable=False, server_default="wetland")
```

3. **`SamplingRecord` Table (`sampling_records`)**:
   - Database column: `parameters = Column(JSONB, nullable=False)`
   - Legacy Compatibility: Retain legacy flat columns (`ph_value`, `temp_value`, etc.) as nullable, deprecated columns. Implement a hybrid getter/setter fallback strategy where getters read from JSONB but fall back to the legacy columns if JSONB is empty, ensuring that existing tests and ingest pipelines continue functioning without interruption.
   - ORM Hybrid properties: `ph_value`, `temp_value`, `do_value`, `water_level`, `invasive_macrophytes`, `cpue_value` mapping to keys inside `parameters`.

```python
class SamplingRecord(Base):
    __tablename__ = "sampling_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="RESTRICT"), nullable=False)
    parameters = Column(JSONB, nullable=False)
    sampled_at = Column(DateTime, nullable=False)

    @hybrid_property
    def ph_value(self):
        return float(self.parameters.get("ph")) if self.parameters and "ph" in self.parameters else None

    @ph_value.setter
    def ph_value(self, value):
        if not self.parameters: self.parameters = {}
        self.parameters["ph"] = value
```

4. **`HealthScore` Table (`health_scores`)**:
   - Keep core scores as database columns: `composite_score`, `adjusted_score`, `health_class`.
   - Add database column: `breakdown = Column(JSONB, nullable=False)`
   - ORM Hybrid property: `wqi_score` pointing to `breakdown["wqi"]`.

```python
class HealthScore(Base):
    __tablename__ = "health_scores"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    composite_score = Column(Numeric(3, 2), nullable=False)
    ik_signal_value = Column(Numeric(3, 2), nullable=False)
    adjusted_score = Column(Numeric(3, 2), nullable=False)
    health_class = Column(String(1), nullable=False)
    breakdown = Column(JSONB, nullable=False)
    calculated_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
```

5. **`FgdRecord` Table (`fgd_records`)**:
   - Database column: `indicators = Column(JSONB, nullable=False)`
   - ORM Hybrid properties: `fish_abundance`, `water_clarity`, `vegetation_cover` mapping to `indicators`.

```python
class FgdRecord(Base):
    __tablename__ = "fgd_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wetland_id = Column(UUID(as_uuid=True), ForeignKey("wetlands.id", ondelete="RESTRICT"), nullable=False)
    indicators = Column(JSONB, nullable=False)
    conducted_at = Column(DateTime, nullable=False)
```

6. **Centralized Constants (e.g. `app/models/domain.py`)**:

```python
class MonitoringDomain(str, enum.Enum):
    WETLAND = "wetland"
    FOREST = "forest"
```

7. **Compound Scoring Registry**:

```python
# app/services/scoring/registry.py
_registry: Dict[Tuple[str, FormType], Type[BaseScoringHandler]] = {}
```

### Alembic Data Migration Plan (Handling Existing Saved Values)

To ensure that existing saved records in the database are not lost during the schema transition, the Alembic migration script will execute a three-step **Data Migration** sequence during `upgrade()`:

1. **Schema Expansion (Step 1)**: Add the new JSONB columns (`parameters`, `breakdown`, `indicators`) as **nullable** fields first to prevent inserts/updates from failing while the tables are populated.
2. **Data Migration (Step 2)**: Execute SQL update statements to transform the existing flat column data into JSON structure and save it inside the new JSONB fields.
3. **Column Cutover & Constraints (Step 3)**:
   - Alter the new JSONB columns to `nullable=False`.
   - Drop the legacy flat columns (`ph_value`, `temp_value`, `do_value`, `wqi_score`, etc.) and their associated check constraints.

#### Sample Migration SQL execution:

```python
def upgrade():
    # 1. Add new JSONB columns as nullable
    op.add_column('sampling_records', sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('health_scores', sa.Column('breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('fgd_records', sa.Column('indicators', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # 2. Map existing flat values to JSONB keys
    op.execute("""
        UPDATE sampling_records
        SET parameters = json_build_object(
            'ph', ph_value,
            'temperature', temp_value,
            'dissolved_oxygen', do_value,
            'water_level', water_level,
            'invasive_macrophytes', invasive_macrophytes,
            'cpue', cpue_value
        )
    """)
    op.execute("""
        UPDATE health_scores
        SET breakdown = json_build_object(
            'wqi', wqi_score
        )
    """)
    op.execute("""
        UPDATE fgd_records
        SET indicators = json_build_object(
            'fish_abundance', fish_abundance,
            'water_clarity', water_clarity,
            'vegetation_cover', vegetation_cover
        )
    """)

    # 3. Alter columns to non-nullable
    op.alter_column('sampling_records', 'parameters', nullable=False)
    op.alter_column('health_scores', 'breakdown', nullable=False)
    op.alter_column('fgd_records', 'indicators', nullable=False)

    # 4. Drop legacy columns
    op.drop_column('sampling_records', 'ph_value')
    op.drop_column('sampling_records', 'temp_value')
    op.drop_column('sampling_records', 'do_value')
    op.drop_column('sampling_records', 'invasive_macrophytes')
    op.drop_column('sampling_records', 'cpue_value')
    op.drop_column('sampling_records', 'water_level')
    op.drop_column('health_scores', 'wqi_score')
    op.drop_column('fgd_records', 'fish_abundance')
    op.drop_column('fgd_records', 'water_clarity')
    op.drop_column('fgd_records', 'vegetation_cover')
```

### Dynamic API Response Payload (`ui_config`)

The `/api/v1/spatial/sites/{site_id}` endpoint will include:

```json
{
  "ui_config": {
    "score_breakdown": [
      {
        "key": "physico_chemical",
        "label": "Physico-chemical",
        "icon": "FlaskConical"
      },
      {
        "key": "catchment_hydrological",
        "label": "Catchment / hydro",
        "icon": "Waves"
      },
      { "key": "ecological", "label": "Ecological", "icon": "Leaf" }
    ],
    "qualitative_grid": [
      { "label": "Fish Abundance", "key": "fish_abundance", "icon": "🐟" },
      { "label": "Water Quality", "key": "water_clarity", "icon": "💧" },
      { "label": "Vegetation Cover", "key": "vegetation_cover", "icon": "🌱" }
    ]
  }
}
```

---

## V. Acceptance Criteria

### User Acceptance Criteria (UAC)

- **UAC-1 (Dynamic View Switcher)**: Given a user opens a site detail drawer, When the site belongs to the `"wetland"` domain, Then they must see the standard wetland scoring breakdown and FGD grids.
- **UAC-2 (New Domain Extensibility)**: Given a new domain `"forest"` is added, When a user opens a forest station, Then they must see the forest parameters (e.g. canopy density, soil moisture) and custom qualitative grid.

### Technical Acceptance Criteria (TAC)

- **TAC-1**: The backend scoring engine executes domain-specific handlers lookup from the scoring registry by `site.wetland.domain`.
- **TAC-2**: Frontend `SiteDrawer` contains zero hardcoded checks for `"physico_chemical"` or `"ik_signal"` fields, and maps the components dynamically from `site.details.ui_config`.

---

## VI. Epic & Ballpark Estimation

- **Backend Migrations & Models**: Simple | 2 hours
- **Scoring Handler Refactoring**: Medium | 4 hours
- **Dynamic API UI Config Ingestion**: Medium | 3 hours
- **Frontend SiteDrawer Decoupling**: Complex | 6 hours
- **Total Ballpark Estimate**: **15 hours / 2 Story Points**
