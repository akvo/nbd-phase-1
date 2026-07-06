from decimal import Decimal
from datetime import datetime
from typing import Optional, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.form import FormType
from app.models.submission import Datapoint, Answer
from app.models.sampling_record import SamplingRecord
from app.models.health_score import HealthScore
from app.models.fgd_record import FgdRecord
from app.models.spatial import Site, Wetland
from app.services.scoring.base import BaseScoringHandler
from app.services.scoring.registry import register_handler

# Constants and Mappings
FISH_ABUNDANCE_MAPPING = {
    "Same": Decimal("0.0"),
    "Slight": Decimal("0.3"),
    "Moderate": Decimal("0.6"),
    "Severe": Decimal("1.0"),
}

WATER_CLARITY_MAPPING = {
    "Same": Decimal("0.0"),
    "Somewhat Worse": Decimal("0.5"),
    "Much Worse": Decimal("1.0"),
}

VEGETATION_COVER_MAPPING = {
    "Same": Decimal("0.0"),
    "Partial Loss": Decimal("0.4"),
    "Severe Loss": Decimal("1.0"),
}


def get_latest_fgd_record(db: Session, site_id: Any) -> Optional[FgdRecord]:
    """Enforces spatial hierarchy to retrieve the latest FGD record

    for the site's parent wetland.
    """
    return (
        db.query(FgdRecord)
        .join(Wetland, Wetland.id == FgdRecord.wetland_id)
        .join(Site, Site.wetland_id == Wetland.id)
        .filter(Site.id == site_id)
        .order_by(FgdRecord.conducted_at.desc())
        .first()
    )


def calculate_ik_signal(fgd: FgdRecord) -> Decimal:
    """Computes the average IK signal from qualitative FGD values."""
    fish_val = FISH_ABUNDANCE_MAPPING.get(fgd.fish_abundance, Decimal("0.0"))
    clarity_val = WATER_CLARITY_MAPPING.get(fgd.water_clarity, Decimal("0.0"))
    veg_val = VEGETATION_COVER_MAPPING.get(
        fgd.vegetation_cover, Decimal("0.0")
    )
    return (fish_val + clarity_val + veg_val) / Decimal("3.0")


def apply_fuzzy_rules(composite_score: Decimal, ik_signal: Decimal) -> Decimal:
    """Applies fuzzy membership set fuzzification and rule defuzzification."""
    # 1. Fuzzify Composite Score (C)
    if composite_score <= Decimal("0.4"):
        c_set = "Low"
    elif composite_score <= Decimal("0.8"):
        c_set = "Medium"
    else:
        c_set = "High"

    # 2. Fuzzify IK Signal (IK)
    if ik_signal <= Decimal("0.2"):
        ik_set = "None"
    elif ik_signal <= Decimal("0.7"):
        ik_set = "Moderate"
    else:
        ik_set = "Strong"

    # 3. Apply Rules Matrix to find output set centroid
    # Centroid values: High = 0.90, Medium = 0.70, Low = 0.50
    if c_set == "High":
        if ik_set == "None":
            centroid = Decimal("0.90")
        else:
            centroid = Decimal("0.70")
    elif c_set == "Medium":
        if ik_set == "None":
            centroid = Decimal("0.70")
        else:
            centroid = Decimal("0.50")
    else:
        centroid = Decimal("0.50")

    # 4. Defuzzify using weighted average formula
    adjusted = (Decimal("2.0") * centroid + composite_score) / Decimal("3.0")
    return adjusted.quantize(Decimal("0.01"))


def map_health_class(score: Decimal) -> str:
    """Maps a composite/adjusted score to its health class rating (A-E)."""
    if score >= Decimal("0.80"):
        return "A"
    elif score >= Decimal("0.60"):
        return "B"
    elif score >= Decimal("0.40"):
        return "C"
    elif score >= Decimal("0.20"):
        return "D"
    else:
        return "E"


def map_class_to_color(health_class: str) -> tuple[str, str]:
    """Maps a health class rating (A-E) to a status color tuple.

    Returns (display_name, database_value) e.g., ("Yellow", "YELLOW").
    """
    if health_class in ("A", "B"):
        return "Green", "GREEN"
    elif health_class in ("C", "D"):
        return "Yellow", "YELLOW"
    else:
        return "Red", "RED"


def calculate_wqi_and_scores(
    ph: Decimal,
    do: Decimal,
    water_level: str,
    invasive_macrophytes: Decimal,
) -> dict:
    """Calculates WQI parameters and aggregates group scores."""
    # 1. WQI calculations
    s_ph = Decimal("8.5")
    s_do = Decimal("5.0")

    v_io_ph = Decimal("7.0")
    v_io_do = Decimal("14.6")

    # K = 1 / (1/8.5 + 1/5.0)
    k = Decimal("1") / (Decimal("1") / s_ph + Decimal("1") / s_do)

    # Unit weights
    w_ph = k / s_ph
    w_do = k / s_do

    # Quality ratings (q_n)
    q_ph = Decimal("100") * (ph - v_io_ph) / (s_ph - v_io_ph)
    q_do = Decimal("100") * (do - v_io_do) / (s_do - v_io_do)

    # Total WQI
    wqi = w_ph * q_ph + w_do * q_do

    # Physico-chemical Score
    physico_chemical_score = Decimal("1.0") - wqi / Decimal("100")
    physico_chemical_score = max(
        Decimal("0.00"), min(Decimal("1.00"), physico_chemical_score)
    )
    physico_chemical_score = physico_chemical_score.quantize(Decimal("0.01"))

    # 2. Catchment score
    wl = str(water_level).upper().strip()
    if wl == "MEDIUM":
        catchment_score = Decimal("1.00")
    elif wl == "HIGH":
        catchment_score = Decimal("0.60")
    elif wl == "LOW":
        catchment_score = Decimal("0.30")
    else:
        catchment_score = Decimal("1.00")

    # 3. Ecological score
    eco_score = Decimal("1.0") - (invasive_macrophytes / Decimal("100.0"))
    ecological_score = max(Decimal("0.00"), min(Decimal("1.00"), eco_score))
    ecological_score = ecological_score.quantize(Decimal("0.01"))

    # 4. Composite score
    composite = (
        physico_chemical_score + catchment_score + ecological_score
    ) / Decimal("3.0")
    composite_score = composite.quantize(Decimal("0.01"))

    # 5. Health class mapping
    if composite_score >= Decimal("0.80"):
        health_class = "A"
    elif composite_score >= Decimal("0.60"):
        health_class = "B"
    elif composite_score >= Decimal("0.40"):
        health_class = "C"
    elif composite_score >= Decimal("0.20"):
        health_class = "D"
    else:
        health_class = "E"

    return {
        "wqi_score": physico_chemical_score,
        "catchment_score": catchment_score,
        "ecological_score": ecological_score,
        "composite_score": composite_score,
        "health_class": health_class,
    }


@register_handler(FormType.CITIZEN_SCIENTIST)
class WetlandScoringHandler(BaseScoringHandler):
    @classmethod
    def score_submission(cls, db: Session, datapoint: Datapoint) -> None:
        # Query all answers for this datapoint
        answers = (
            db.query(Answer).filter(Answer.datapoint_id == datapoint.id).all()
        )

        # Parse answers
        ph_val = None
        temp_val = None
        do_val = None
        inv_percent = Decimal("0.0")
        water_lvl = "MEDIUM"

        for ans in answers:
            if not ans.question:
                continue
            q_name = (ans.question.name or "").lower()

            if q_name == "ph":
                if ans.value is not None:
                    ph_val = Decimal(str(ans.value))
            elif q_name == "temp":
                if ans.value is not None:
                    temp_val = Decimal(str(ans.value))
            elif q_name == "do":
                if ans.value is not None:
                    do_val = Decimal(str(ans.value))
            elif q_name == "invasive_percent":
                if ans.value is not None:
                    inv_percent = Decimal(str(ans.value))
            elif q_name == "water_level":
                raw_val = ans.name or ans.value or "MEDIUM"
                val_str = str(raw_val).upper().strip()
                if val_str in ("HIGH", "MEDIUM", "LOW"):
                    water_lvl = val_str

        # Check constraints (non-nullable fields)
        if ph_val is None or temp_val is None or do_val is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Missing water quality parameters (pH, Temperature, "
                    "or Dissolved Oxygen) required to approve records."
                ),
            )

        sampling_rec = SamplingRecord(
            site_id=datapoint.site_id,
            ph_value=ph_val,
            temp_value=temp_val,
            do_value=do_val,
            invasive_macrophytes=inv_percent,
            water_level=water_lvl,
            sampled_at=datapoint.created_at or datetime.utcnow(),
        )
        db.add(sampling_rec)
        db.flush()

        # Calculate and save health score
        scores = calculate_wqi_and_scores(
            ph=ph_val,
            do=do_val,
            water_level=water_lvl,
            invasive_macrophytes=inv_percent,
        )

        # Retrieve parent wetland FGD record and run fuzzy logic adjustment
        fgd = get_latest_fgd_record(db, datapoint.site_id)
        if fgd:
            ik_signal_value = calculate_ik_signal(fgd)
            adjusted_score = apply_fuzzy_rules(
                scores["composite_score"], ik_signal_value
            )
            health_class = map_health_class(adjusted_score)
        else:
            ik_signal_value = Decimal("0.00")
            adjusted_score = scores["composite_score"]
            health_class = scores["health_class"]

        health_score_rec = HealthScore(
            site_id=datapoint.site_id,
            wqi_score=scores["wqi_score"],
            composite_score=scores["composite_score"],
            ik_signal_value=ik_signal_value,
            adjusted_score=adjusted_score,
            health_class=health_class,
            calculated_at=datapoint.created_at or datetime.utcnow(),
        )
        db.add(health_score_rec)
        db.flush()


@register_handler(FormType.INDIGENOUS_KNOWLEDGE)
class IndigenousKnowledgeScoringHandler(BaseScoringHandler):
    @classmethod
    def score_submission(cls, db: Session, datapoint: Datapoint) -> None:
        # Extract answers
        answers = (
            db.query(Answer).filter(Answer.datapoint_id == datapoint.id).all()
        )

        fish_abundance = "Same"
        water_clarity = "Same"
        vegetation_cover = "Same"

        for ans in answers:
            if not ans.question:
                continue
            q_name = (ans.question.name or "").lower()
            val_str = ans.name or str(ans.value)

            if q_name == "fish_abundance_change":
                fish_abundance = val_str
            elif q_name == "water_clarity_change":
                water_clarity = val_str
            elif q_name == "vegetation_cover_change":
                vegetation_cover = val_str

        # Create FgdRecord
        fgd_rec = FgdRecord(
            wetland_id=datapoint.wetland_id,
            fish_abundance=fish_abundance,
            water_clarity=water_clarity,
            vegetation_cover=vegetation_cover,
            conducted_at=datapoint.created_at or datetime.utcnow(),
        )
        db.add(fgd_rec)
        db.flush()
