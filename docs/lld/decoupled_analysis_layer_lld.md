# LLD — Decoupled & Domain-Agnostic Analysis Layer

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) / Amelia (Developer)
> Initiative/Epic: Decoupled Wetland & Forest Monitoring Platform
> Target Location: `docs/lld/decoupled_analysis_layer_lld.md`

---

## 1. Data Schema & Models

### 1.1 Database Migration & Cutover Strategy (Alembic)

The migration script will execute a safe transition using the following sequence inside the `upgrade()` method:
1. **Schema Expansion**: Add the new JSONB columns as nullable columns.
2. **Data Migration**: Copy existing flat values into the JSONB structures.
3. **Cutover**: Alter columns to `sa.Column('parameters', postgresql.JSONB, nullable=False)` and drop the legacy flat columns.

```python
def upgrade():
    # 1. Add new JSONB columns as nullable
    op.add_column('sampling_records', sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    sa_sampling = sa.sql.table('sampling_records',
        sa.Column('ph_value', sa.Numeric()), sa.Column('temp_value', sa.Numeric()),
        sa.Column('sa_do_value', sa.Numeric()), sa.Column('water_level', sa.String()),
        sa.Column('invasive_macrophytes', sa.Numeric()), sa.Column('cpue_value', sa.Numeric()),
        sa.Column('parameters', postgresql.JSONB)
    )
    # 2. Data Migration: build JSONB objects
    op.execute(
        sa_sampling.update().values(
            parameters=sa.func.json_build_object(
                'ph', sa_sampling.c.ph_value,
                'temperature', sa_sampling.c.temp_value,
                'dissolved_oxygen', sa_sampling.c.do_value,
                'water_level', sa_sampling.c.water_level,
                'invasive_macrophytes', sa_sampling.c.invasive_macrophytes,
                'cpue', sa_sampling.c.cpue_value
            )
        )
    )
    op.alter_column('sampling_records', 'parameters', nullable=False)
    op.drop_column('sampling_records', 'ph_value')
    # ... drop remaining flat columns
```

### 1.2 ORM Models & Hybrid Properties

- **`Wetland`** (`backend/app/models/spatial.py`):

  ```python
  domain = Column(String(50), nullable=False, default="wetland", server_default="wetland")
  ```

- **`Form`** (`backend/app/models/form.py`):

  ```python
  domain = Column(String(50), nullable=False, default="wetland", server_default="wetland")
  ```

- **`SamplingRecord`** (`backend/app/models/sampling_record.py`):

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
      
      # Similar hybrid properties mapped for temp_value, do_value, water_level, invasive_macrophytes, and cpue_value.
  ```

- **`FgdRecord`** (`backend/app/models/fgd_record.py`):

  ```python
  class FgdRecord(Base):
      __tablename__ = "fgd_records"
      id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      wetland_id = Column(UUID(as_uuid=True), ForeignKey("wetlands.id", ondelete="RESTRICT"), nullable=False)
      indicators = Column(JSONB, nullable=False)
      conducted_at = Column(DateTime, nullable=False)

      @hybrid_property
      def fish_abundance(self):
          return self.indicators.get("fish_abundance") if self.indicators else None

      @fish_abundance.setter
      def fish_abundance(self, value):
          if not self.indicators: self.indicators = {}
          self.indicators["fish_abundance"] = value
  ```

- **`HealthScore`** (`backend/app/models/health_score.py`):

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

      @hybrid_property
      def wqi_score(self):
          return float(self.breakdown.get("wqi")) if self.breakdown and "wqi" in self.breakdown else None

      @wqi_score.setter
      def wqi_score(self, value):
          if not self.breakdown: self.breakdown = {}
          self.breakdown["wqi"] = value
  ```

---

## 2. Centralized Registry & Compound Key Lookup

### 2.1 Refactoring `registry.py`

The scoring registry will match handlers via a tuple key `(domain, form_type)`.

```python
_registry: Dict[Tuple[str, FormType], Type[BaseScoringHandler]] = {}

def register_handler(domain: str, form_type: FormType):
    def decorator(cls: Type[BaseScoringHandler]):
        _registry[(domain, form_type)] = cls
        return cls
    return decorator

def get_handler(domain: str, form_type: FormType) -> Optional[Type[BaseScoringHandler]]:
    return _registry.get((domain, form_type))
```

### 2.2 Updating Router Resolution

When a data point is approved, the route maps the handler dynamically:

```python
domain = dp.form.domain if dp.form else "wetland"
handler = get_handler(domain, FormType(dp.form.type))
if handler:
    handler.score_submission(db, dp)
```

### 2.3 Reconciliation Refactoring (`reconciliation.py`)

Compare citizen sampling record values dynamically from JSONB using parameter names:

```python
# app/services/reconciliation.py
comparisons = [
    ("ph_value", Decimal(str(record.parameters.get("ph"))), lab_ph),
    ("temp_value", Decimal(str(record.parameters.get("temperature"))), lab_temp),
    ("do_value", Decimal(str(record.parameters.get("dissolved_oxygen"))), lab_do),
]
```

*(This maps parameter lookups directly to the JSONB schema, preventing compile-time coupling to database columns).*

---

## 3. Dynamic UI Layout Configurations

### 3.1 Pydantic UI Config Schemas

Define the layout schema inside `backend/app/schemas/spatial.py`:

```python
class MetricUIConfig(BaseModel):
    key: str
    label: str
    icon: str

class QualitativeUIConfig(BaseModel):
    label: str
    key: str
    icon: str

class UIConfigResponse(BaseModel):
    score_breakdown: list[MetricUIConfig]
    qualitative_grid: list[QualitativeUIConfig]
```

### 3.2 Dynamic Config Factory

The `/sites` and `/sites/{id}` routers will return the layout matching the domain:

```python
WETLAND_UI_CONFIG = {
    "score_breakdown": [
        {"key": "physico_chemical", "label": "Physico-chemical", "icon": "FlaskConical"},
        {"key": "catchment_hydrological", "label": "Catchment / hydro", "icon": "Waves"},
        {"key": "ecological", "label": "Ecological", "icon": "Leaf"}
    ],
    "qualitative_grid": [
        {"label": "Fish Abundance", "key": "fish_abundance", "icon": "🐟"},
        {"label": "Water Quality", "key": "water_clarity", "icon": "💧"},
        {"label": "Vegetation Cover", "key": "vegetation_cover", "icon": "🌱"},
        {"label": "Pollution Events", "key": "pollution_events", "icon": "⚠️"}
    ]
}
```

---

## 4. Frontend Dynamic Site Drawer

Update the `SiteDrawer` to iterate dynamically over `ui_config` lists for both progress bars and grids, removing hardcoded checks.
For example, instead of rendering hardcoded cards, it will iterate over `site.details.ui_config.score_breakdown`:

```tsx
{site.details.ui_config.score_breakdown.map((item) => (
  <div key={item.key}>
    <span>{item.label}</span>
    <Progress value={site.details.score_breakdown[item.key].score * 100} />
  </div>
))}
```

---

## 5. Verification Plan

### Seed Scripts & Test Suites Updates

Refactor the following code files to instantiate models using the new JSONB structures:
* **Seeder**: `backend/app/seeds/seed_fake_submissions.py` (instantiate `HealthScore` using `breakdown` dict).
* **Backend Tests**: Update all `SamplingRecord`, `FgdRecord`, and `HealthScore` instantiations in:
  * `backend/tests/test_public_api.py`
  * `backend/tests/test_scoring.py`
  * `backend/tests/test_remaining_schemas.py`
  * `backend/tests/test_reconciliation.py`
  * `backend/tests/test_submission_moderation.py`

### Automated Tests

- Run `pytest` backend tests to verify compound registry lookups and JSONB calculations.
- Run `vitest` frontend tests to verify dynamic grid rendering.
