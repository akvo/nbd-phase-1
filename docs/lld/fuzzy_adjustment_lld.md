# LLD — Hierarchical IK Extraction & Fuzzy Rule Matrix

> **Stage 3 of 3 — Low-Level Design**
> Owner: Winston (Architect) / Developer | Target Location: `docs/lld/fuzzy_adjustment_lld.md` | References: `docs/prd/scoring_engine_prd.md`, `docs/Final_SDD.md`
> Status: `Approved`

---

## 1. Database Traversal (Spatial Join)

To fetch the community Focus Group Discussion (FGD) session for a given site, we query the `fgd_records` table by joining through the `sites` and `wetlands` tables.

```python
from sqlalchemy.orm import Session
from app.models.fgd_record import FgdRecord
from app.models.spatial import Site, Wetland

def get_latest_fgd_record(db: Session, site_id: str) -> FgdRecord:
    # 1. Enforce spatial hierarchy: Site -> Parent Wetland -> latest FgdRecord
    return (
        db.query(FgdRecord)
        .join(Wetland, Wetland.id == FgdRecord.wetland_id)
        .join(Site, Site.wetland_id == Wetland.id)
        .filter(Site.id == site_id)
        .order_by(FgdRecord.conducted_at.desc())
        .first()
    )
```

---

## 2. Parameter Encoding

Dropdown answers from `FgdRecord` are mapped to numerical indicators on a scale of `0.0` (optimal) to `1.0` (severe degradation). These options must be defined as type-safe Python Enums and Constant mappings:

### 2.1 Enums & Mappings Definition
```python
import enum
from decimal import Decimal

class FishAbundanceOption(str, enum.Enum):
    SAME = "Same"
    SLIGHT = "Slight"
    MODERATE = "Moderate"
    SEVERE = "Severe"

class WaterClarityOption(str, enum.Enum):
    SAME = "Same"
    SOMEWHAT_WORSE = "Somewhat Worse"
    MUCH_WORSE = "Much Worse"

class VegetationCoverOption(str, enum.Enum):
    SAME = "Same"
    PARTIAL_LOSS = "Partial Loss"
    SEVERE_LOSS = "Severe Loss"

FISH_ABUNDANCE_MAPPING = {
    FishAbundanceOption.SAME: Decimal("0.0"),
    FishAbundanceOption.SLIGHT: Decimal("0.3"),
    FishAbundanceOption.MODERATE: Decimal("0.6"),
    FishAbundanceOption.SEVERE: Decimal("1.0"),
}

WATER_CLARITY_MAPPING = {
    WaterClarityOption.SAME: Decimal("0.0"),
    WaterClarityOption.SOMEWHAT_WORSE: Decimal("0.5"),
    WaterClarityOption.MUCH_WORSE: Decimal("1.0"),
}

VEGETATION_COVER_MAPPING = {
    VegetationCoverOption.SAME: Decimal("0.0"),
    VegetationCoverOption.PARTIAL_LOSS: Decimal("0.4"),
    VegetationCoverOption.SEVERE_LOSS: Decimal("1.0"),
}
```

### 2.2 IK Signal Average
$$\text{IK Signal} = \frac{\text{fish\_abundance\_val} + \text{water\_clarity\_val} + \text{vegetation\_cover\_val}}{3.0}$$

---

## 3. Fuzzification & Membership Sets

### 3.1 Input Fuzzy Sets
*   **Composite Score ($C$)**:
    *   `Low`: $C \le 0.4$
    *   `Medium`: $0.4 < C \le 0.8$
    *   `High`: $C > 0.8$
*   **IK Signal ($IK$)**:
    *   `None`: $IK \le 0.2$
    *   `Moderate`: $0.2 < IK \le 0.7$
    *   `Strong`: $IK > 0.7$

---

## 4. Fuzzy Rule Matrix & Defuzzification

### 4.1 Rule Matrix

| Composite Score ($C$) | IK Signal ($IK$) | Output Fuzzy Set |
| :--- | :--- | :--- |
| High | None | High |
| High | Moderate | Medium |
| High | Strong | Medium |
| Medium | None | Medium |
| Medium | Moderate | Low |
| Medium | Strong | Low |
| Low | Any | Low |

### 4.2 Defuzzification (Centroid Method)
The fired rule set determines the target output category and its centroid value:
*   `High` Set Centroid: `0.90`
*   `Medium` Set Centroid: `0.70`
*   `Low` Set Centroid: `0.50`

For borderline cases (e.g., Composite Score = `0.638` (Medium) and IK Signal = `0.67` (Moderate)), the rule evaluates to a `Low` output fuzzy set. Centroid-based defuzzification adjusts the score downward to exactly `0.55` (falling into Health Class **C / Moderate**, triggering the yellow status color).

---

## 5. Strategy Pipeline Integration

The calculation is integrated directly inside `WetlandScoringHandler` under `app/services/scoring/handlers/wetland.py`:

```python
# 1. Fetch latest FGD record
fgd = get_latest_fgd_record(db, datapoint.site_id)

# 2. If present, compute IK Signal & run Fuzzification/Defuzzification
if fgd:
    ik_signal = calculate_ik_signal(fgd)
    adjusted_score = apply_fuzzy_rules(composite_score, ik_signal)
else:
    ik_signal = Decimal("0.00")
    adjusted_score = composite_score
```
