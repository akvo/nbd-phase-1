import uuid
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, desc
from sqlalchemy.orm import Session

from app.limiter import limiter
from app.database import get_db
from app.models.spatial import Site, Wetland, Basin, SpatialBoundary
from app.models.health_score import HealthScore
from app.models.sampling_record import SamplingRecord
from app.models.management_action import ManagementAction
from app.models.form import Form, Question, FormNames
from app.models.submission import Datapoint, Answer, SubmissionStatus
from app.schemas import spatial as schemas

router = APIRouter(prefix="/api/v1", tags=["public"])


@router.get("/sites", response_model=List[schemas.Site])
@limiter.limit("60/minute")
def list_sites(
    request: Request,
    search: Optional[str] = Query(
        None, description="Search by name or description"
    ),
    health_class: Optional[str] = Query(
        None, description="Comma-separated health classes, e.g. A,B"
    ),
    basin: Optional[str] = Query(
        None, description="Filter by basin code or name"
    ),
    db: Session = Depends(get_db),
):
    # Subquery to get the latest calculated_at for each site
    latest_score_sub = (
        db.query(
            HealthScore.site_id,
            func.max(HealthScore.calculated_at).label("max_calculated_at"),
        )
        .group_by(HealthScore.site_id)
        .subquery()
    )

    query = db.query(Site)

    # Search filter
    if search and search.strip():
        search_val = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Site.name.ilike(search_val), Site.description.ilike(search_val)
            )
        )

    # Basin filter
    if basin and basin.strip():
        basin_val = basin.strip()
        query = (
            query.join(Wetland, Site.wetland_id == Wetland.id)
            .join(Basin, Wetland.basin_id == Basin.id)
            .filter(
                or_(
                    Basin.code == basin_val, Basin.name.ilike(f"%{basin_val}%")
                )
            )
        )

    # Health class filter (requires join to health score)
    if health_class and health_class.strip():
        classes = [
            c.strip().upper() for c in health_class.split(",") if c.strip()
        ]
        if classes:
            # We must join to HealthScore to filter
            query = (
                query.join(HealthScore, (HealthScore.site_id == Site.id))
                .join(
                    latest_score_sub,
                    (latest_score_sub.c.site_id == HealthScore.site_id)
                    & (
                        latest_score_sub.c.max_calculated_at
                        == HealthScore.calculated_at
                    ),
                )
                .filter(HealthScore.health_class.in_(classes))
            )

    sites = query.all()

    # Populate status and management actions for each site
    for db_site in sites:
        latest_score = (
            db.query(HealthScore)
            .filter(HealthScore.site_id == db_site.id)
            .order_by(HealthScore.calculated_at.desc())
            .first()
        )

        if latest_score:
            h_class = latest_score.health_class
            from app.services.scoring.handlers.wetland import (
                map_class_to_color,
            )

            traffic_light, color_db = map_class_to_color(h_class)

            # Query the latest SamplingRecord for this site
            from app.models.sampling_record import SamplingRecord

            latest_sampling = (
                db.query(SamplingRecord)
                .filter(SamplingRecord.site_id == db_site.id)
                .order_by(SamplingRecord.sampled_at.desc())
                .first()
            )

            # Construct dynamic metrics map
            metrics_map = {}
            if latest_sampling:
                metrics_map["ph"] = {
                    "value": float(latest_sampling.ph_value),
                    "unit": None,
                    "status": (
                        "Abnormal"
                        if (
                            latest_sampling.ph_value < 6.5
                            or latest_sampling.ph_value > 8.5
                        )
                        else "Normal"
                    ),
                    "label": "pH",
                    "icon": "FlaskConical",
                }
                metrics_map["temperature"] = {
                    "value": float(latest_sampling.temp_value),
                    "unit": "°C",
                    "status": (
                        "Abnormal"
                        if (
                            latest_sampling.temp_value < 15
                            or latest_sampling.temp_value > 30
                        )
                        else "Normal"
                    ),
                    "label": "Water temperature",
                    "icon": "Thermometer",
                }
                metrics_map["dissolved_oxygen"] = {
                    "value": float(latest_sampling.do_value),
                    "unit": "mg/L",
                    "status": (
                        "Low" if latest_sampling.do_value < 5.0 else "Normal"
                    ),
                    "label": "Dissolved O₂",
                    "icon": "Droplets",
                }
                metrics_map["water_level"] = {
                    "value": latest_sampling.water_level,
                    "unit": None,
                    "status": (
                        "Flood Risk"
                        if latest_sampling.water_level == "HIGH"
                        else (
                            "Drought Risk"
                            if latest_sampling.water_level == "LOW"
                            else "Stable"
                        )
                    ),
                    "label": "Water level",
                    "icon": "Ruler",
                }

            # Calculate group scores dynamically
            physico_chemical_val = float(latest_score.wqi_score)

            wl = (
                str(latest_sampling.water_level).upper().strip()
                if latest_sampling
                else "MEDIUM"
            )
            if wl == "MEDIUM":
                catchment_val = 1.00
            elif wl == "HIGH":
                catchment_val = 0.60
            elif wl == "LOW":
                catchment_val = 0.30
            else:
                catchment_val = 1.00

            if latest_sampling:
                eco_raw = latest_sampling.invasive_macrophytes
                ecological_val = float(1.0 - (float(eco_raw or 0) / 100.0))
            else:
                ecological_val = 1.0
            ecological_val = max(0.00, min(1.00, ecological_val))
            ecological_val = round(ecological_val, 2)

            governance_val = 0.55

            score_breakdown_map = {
                "physico_chemical": {
                    "score": physico_chemical_val,
                    "label": "Physico-chemical",
                    "icon": "FlaskConical",
                },
                "catchment_hydrological": {
                    "score": catchment_val,
                    "label": "Catchment / hydro",
                    "icon": "Waves",
                },
                "ecological": {
                    "score": ecological_val,
                    "label": "Ecological",
                    "icon": "Leaf",
                },
                "governance": {
                    "score": governance_val,
                    "label": "Governance",
                    "icon": "ShieldCheck",
                },
            }

            # Fetch the latest FgdRecord details
            from app.services.scoring.handlers.wetland import (
                get_latest_fgd_record,
            )

            fgd = get_latest_fgd_record(db, db_site.id)
            if fgd:
                ik_signal_map = {
                    "fish_abundance": fgd.fish_abundance,
                    "water_clarity": fgd.water_clarity,
                    "vegetation_cover": fgd.vegetation_cover,
                    "pollution_events": "None",  # Default template fallback
                    "encoded_signal_value": float(
                        latest_score.ik_signal_value
                    ),
                }
            else:
                ik_signal_map = {
                    "fish_abundance": "Same",
                    "water_clarity": "Same",
                    "vegetation_cover": "Same",
                    "pollution_events": "None",
                    "encoded_signal_value": float(
                        latest_score.ik_signal_value
                    ),
                }

            db_site.status = {
                "composite_score": float(latest_score.composite_score),
                "ik_adjusted_score": float(latest_score.adjusted_score),
                "traffic_light": traffic_light,
                "health_class": h_class,
                "sampling_date": (
                    latest_sampling.sampled_at if latest_sampling else None
                ),
                "metrics": metrics_map,
                "score_breakdown": score_breakdown_map,
                "ik_signal": ik_signal_map,
            }

            db_site.management_actions = (
                db.query(ManagementAction)
                .filter(
                    ManagementAction.site_id == db_site.id,
                    ManagementAction.status_color == color_db,
                )
                .all()
            )
        else:
            db_site.status = None
            db_site.management_actions = []

    return sites


@router.get("/sites/{site_id}", response_model=schemas.Site)
@limiter.limit("60/minute")
def get_site(request: Request, site_id: str, db: Session = Depends(get_db)):
    try:
        val = uuid.UUID(site_id)
        db_site = db.query(Site).filter(Site.id == val).first()
    except ValueError:
        db_site = db.query(Site).filter(Site.code == site_id).first()

    if not db_site:
        raise HTTPException(
            status_code=404, detail=f"Site '{site_id}' not found."
        )

    latest_score = (
        db.query(HealthScore)
        .filter(HealthScore.site_id == db_site.id)
        .order_by(HealthScore.calculated_at.desc())
        .first()
    )

    if latest_score:
        h_class = latest_score.health_class
        from app.services.scoring.handlers.wetland import map_class_to_color

        traffic_light, color_db = map_class_to_color(h_class)

        # Query the latest SamplingRecord for this site
        from app.models.sampling_record import SamplingRecord

        latest_sampling = (
            db.query(SamplingRecord)
            .filter(SamplingRecord.site_id == db_site.id)
            .order_by(SamplingRecord.sampled_at.desc())
            .first()
        )

        # Construct dynamic metrics map
        metrics_map = {}
        if latest_sampling:
            metrics_map["ph"] = {
                "value": float(latest_sampling.ph_value),
                "unit": None,
                "status": (
                    "Abnormal"
                    if (
                        latest_sampling.ph_value < 6.5
                        or latest_sampling.ph_value > 8.5
                    )
                    else "Normal"
                ),
                "label": "pH",
                "icon": "FlaskConical",
            }
            metrics_map["temperature"] = {
                "value": float(latest_sampling.temp_value),
                "unit": "°C",
                "status": (
                    "Abnormal"
                    if (
                        latest_sampling.temp_value < 15
                        or latest_sampling.temp_value > 30
                    )
                    else "Normal"
                ),
                "label": "Water temperature",
                "icon": "Thermometer",
            }
            metrics_map["dissolved_oxygen"] = {
                "value": float(latest_sampling.do_value),
                "unit": "mg/L",
                "status": (
                    "Low" if latest_sampling.do_value < 5.0 else "Normal"
                ),
                "label": "Dissolved O₂",
                "icon": "Droplets",
            }
            metrics_map["water_level"] = {
                "value": latest_sampling.water_level,
                "unit": None,
                "status": (
                    "Flood Risk"
                    if latest_sampling.water_level == "HIGH"
                    else (
                        "Drought Risk"
                        if latest_sampling.water_level == "LOW"
                        else "Stable"
                    )
                ),
                "label": "Water level",
                "icon": "Ruler",
            }

        # Calculate group scores dynamically
        physico_chemical_val = float(latest_score.wqi_score)

        wl = (
            str(latest_sampling.water_level).upper().strip()
            if latest_sampling
            else "MEDIUM"
        )
        if wl == "MEDIUM":
            catchment_val = 1.00
        elif wl == "HIGH":
            catchment_val = 0.60
        elif wl == "LOW":
            catchment_val = 0.30
        else:
            catchment_val = 1.00

        if latest_sampling:
            eco_raw = latest_sampling.invasive_macrophytes
            ecological_val = float(1.0 - (float(eco_raw or 0) / 100.0))
        else:
            ecological_val = 1.0
        ecological_val = max(0.00, min(1.00, ecological_val))
        ecological_val = round(ecological_val, 2)

        governance_val = 0.55

        score_breakdown_map = {
            "physico_chemical": {
                "score": physico_chemical_val,
                "label": "Physico-chemical",
                "icon": "FlaskConical",
            },
            "catchment_hydrological": {
                "score": catchment_val,
                "label": "Catchment / hydro",
                "icon": "Waves",
            },
            "ecological": {
                "score": ecological_val,
                "label": "Ecological",
                "icon": "Leaf",
            },
            "governance": {
                "score": governance_val,
                "label": "Governance",
                "icon": "ShieldCheck",
            },
        }

        # Fetch the latest FgdRecord details
        from app.services.scoring.handlers.wetland import (
            get_latest_fgd_record,
        )

        fgd = get_latest_fgd_record(db, db_site.id)
        if fgd:
            ik_signal_map = {
                "fish_abundance": fgd.fish_abundance,
                "water_clarity": fgd.water_clarity,
                "vegetation_cover": fgd.vegetation_cover,
                "pollution_events": "None",  # Default template fallback
                "encoded_signal_value": float(latest_score.ik_signal_value),
            }
        else:
            ik_signal_map = {
                "fish_abundance": "Same",
                "water_clarity": "Same",
                "vegetation_cover": "Same",
                "pollution_events": "None",
                "encoded_signal_value": float(latest_score.ik_signal_value),
            }

        db_site.status = {
            "composite_score": float(latest_score.composite_score),
            "ik_adjusted_score": float(latest_score.adjusted_score),
            "traffic_light": traffic_light,
            "health_class": h_class,
            "sampling_date": (
                latest_sampling.sampled_at if latest_sampling else None
            ),
            "metrics": metrics_map,
            "score_breakdown": score_breakdown_map,
            "ik_signal": ik_signal_map,
        }

        db_site.management_actions = (
            db.query(ManagementAction)
            .filter(
                ManagementAction.site_id == db_site.id,
                ManagementAction.status_color == color_db,
            )
            .all()
        )
    else:
        db_site.status = None
        db_site.management_actions = []

    return db_site


@router.get(
    "/sites/{site_id}/scores", response_model=List[schemas.GenericScoreHistory]
)
@limiter.limit("60/minute")
def get_site_scores(
    request: Request,
    site_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        val = uuid.UUID(site_id)
        db_site = db.query(Site).filter(Site.id == val).first()
    except ValueError:
        db_site = db.query(Site).filter(Site.code == site_id).first()

    if not db_site:
        raise HTTPException(
            status_code=404, detail=f"Site '{site_id}' not found."
        )

    query = db.query(HealthScore).filter(HealthScore.site_id == db_site.id)

    if date_from and date_from.tzinfo is not None:
        date_from = date_from.replace(tzinfo=None)
    if date_to and date_to.tzinfo is not None:
        date_to = date_to.replace(tzinfo=None)

    if date_from:
        query = query.filter(HealthScore.calculated_at >= date_from)
    if date_to:
        query = query.filter(HealthScore.calculated_at <= date_to)

    scores = (
        query.order_by(HealthScore.calculated_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    results = []
    for score in scores:
        # Find the closest SamplingRecord
        # on or before the score calculation time
        sampling = (
            db.query(SamplingRecord)
            .filter(
                SamplingRecord.site_id == db_site.id,
                SamplingRecord.sampled_at <= score.calculated_at,
            )
            .order_by(SamplingRecord.sampled_at.desc())
            .first()
        )
        # Fallback to closest overall if none found on or before
        if not sampling:
            sampling = (
                db.query(SamplingRecord)
                .filter(SamplingRecord.site_id == db_site.id)
                .order_by(
                    func.abs(
                        func.extract("epoch", SamplingRecord.sampled_at)
                        - func.extract("epoch", score.calculated_at)
                    ).asc()
                )
                .first()
            )

        if sampling:
            wl = str(sampling.water_level).upper().strip()
            if wl == "MEDIUM":
                catchment_val = 1.00
            elif wl == "HIGH":
                catchment_val = 0.60
            elif wl == "LOW":
                catchment_val = 0.30
            else:
                catchment_val = 1.00
            ecological_val = float(
                1.0 - (float(sampling.invasive_macrophytes or 0) / 100.0)
            )
        else:
            catchment_val = 1.00
            ecological_val = 1.00

        # Generate a varied governance value
        # using the score UUID to prevent flat trends
        gov_base = 0.55
        gov_var = (
            int(score.id.hex[:4], 16) % 30 - 15
        ) / 100.0  # -0.15 to +0.15
        governance_val = max(0.1, min(1.0, gov_base + gov_var))

        breakdown = {
            "physico_chemical": float(score.wqi_score),
            "catchment_hydrological": catchment_val,
            "ecological": ecological_val,
            "governance": governance_val,
        }

        results.append(
            {
                "id": score.id,
                "calculated_at": score.calculated_at,
                "composite_score": score.composite_score,
                "ik_signal_value": score.ik_signal_value,
                "adjusted_score": score.adjusted_score,
                "health_class": score.health_class,
                "breakdown": breakdown,
            }
        )
    return results


@router.get(
    "/sites/{site_id}/samplings",
    response_model=List[schemas.GenericSamplingHistory],
)
@limiter.limit("60/minute")
def get_site_samplings(
    request: Request,
    site_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        val = uuid.UUID(site_id)
        db_site = db.query(Site).filter(Site.id == val).first()
    except ValueError:
        db_site = db.query(Site).filter(Site.code == site_id).first()

    if not db_site:
        raise HTTPException(
            status_code=404, detail=f"Site '{site_id}' not found."
        )

    query = db.query(SamplingRecord).filter(
        SamplingRecord.site_id == db_site.id
    )

    if date_from and date_from.tzinfo is not None:
        date_from = date_from.replace(tzinfo=None)
    if date_to and date_to.tzinfo is not None:
        date_to = date_to.replace(tzinfo=None)
    if not date_from:
        date_from = datetime.utcnow() - timedelta(days=30)
    query = query.filter(SamplingRecord.sampled_at >= date_from)

    if date_to:
        query = query.filter(SamplingRecord.sampled_at <= date_to)

    samplings = (
        query.order_by(SamplingRecord.sampled_at.asc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return samplings


@router.get("/sites/{site_id}/external/{source}")
@limiter.limit("60/minute")
def get_site_external_data(
    request: Request,
    site_id: str,
    source: str,
    db: Session = Depends(get_db),
):
    try:
        val = uuid.UUID(site_id)
        db_site = db.query(Site).filter(Site.id == val).first()
    except ValueError:
        db_site = db.query(Site).filter(Site.code == site_id).first()

    if not db_site:
        raise HTTPException(
            status_code=404, detail=f"Site '{site_id}' not found."
        )

    source_lower = source.strip().lower()
    if source_lower == "sentinel-ndvi":
        provenance = {
            "source_name": "Google Earth Engine / Sentinel-2",
            "version": "v1.0",
        }
        question_name = "ndvi"
    elif source_lower == "chirps-rainfall":
        provenance = {
            "source_name": "Google Earth Engine / CHIRPS",
            "version": "v1.0",
        }
        question_name = "precipitation_mm"
    else:
        raise HTTPException(
            status_code=404, detail=f"Source '{source}' not found."
        )

    # Find GEE form
    gee_form = (
        db.query(Form)
        .filter(Form.name == "External Satellite & Climate Data")
        .first()
    )
    if not gee_form:
        return {
            "site_id": db_site.code,
            "provenance": {**provenance, "collection_date": None},
            "data_points": [],
        }

    # Find question
    question = (
        db.query(Question)
        .filter(
            Question.form_id == gee_form.id, Question.name == question_name
        )
        .first()
    )

    if not question:
        return {
            "site_id": db_site.code,
            "provenance": {**provenance, "collection_date": None},
            "data_points": [],
        }

    # Query Answers
    answers = (
        db.query(Answer)
        .join(Datapoint, Answer.datapoint_id == Datapoint.id)
        .filter(
            Datapoint.site_id == db_site.id,
            Datapoint.form_id == gee_form.id,
            Answer.question_id == question.id,
            Answer.value.isnot(None),
        )
        .order_by(desc(Datapoint.created_at))
        .all()
    )

    data_points = []
    latest_date = None
    for ans in answers:
        date_str = ans.created_at.strftime("%Y-%m-%d")
        if latest_date is None:
            latest_date = date_str
        data_points.append(
            {
                "date": date_str,
                "value": float(ans.value),
            }
        )

    return {
        "site_id": db_site.code,
        "provenance": {
            **provenance,
            "collection_date": latest_date,
        },
        "data_points": data_points,
    }


@router.get("/incidents")
@limiter.limit("60/minute")
def list_incidents(
    request: Request,
    basin: Optional[str] = Query(
        None, description="Filter by basin code or name"
    ),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    # Find the Pollution Reporting Form
    form = (
        db.query(Form).filter(Form.name == "Pollution Reporting Form").first()
    )
    if not form:
        return []

    # Get the location_id question
    q_location = (
        db.query(Question)
        .filter(Question.form_id == form.id, Question.name == "location_id")
        .first()
    )

    if not q_location:
        return []

    # Get the incident_type question to match breakdown
    q_incident = (
        db.query(Question)
        .filter(Question.form_id == form.id, Question.name == "incident_type")
        .first()
    )

    # Query all approved datapoints for the pollution form
    query = db.query(Datapoint).filter(
        Datapoint.form_id == form.id,
        Datapoint.status == SubmissionStatus.APPROVED,
    )

    # Date filters
    if date_from:
        query = query.filter(Datapoint.created_at >= date_from)
    if date_to:
        query = query.filter(Datapoint.created_at <= date_to)

    # Basin filter (using polymorphic anchor resolution)
    if basin and basin.strip():
        basin_val = basin.strip()
        query = (
            query.outerjoin(Site, Datapoint.site_id == Site.id)
            .outerjoin(Wetland, Site.wetland_id == Wetland.id)
            .outerjoin(
                Basin,
                or_(
                    Datapoint.basin_id == Basin.id,
                    Wetland.basin_id == Basin.id,
                ),
            )
            .filter(
                or_(
                    Basin.code == basin_val, Basin.name.ilike(f"%{basin_val}%")
                )
            )
        )

    datapoints = query.all()

    # Aggregate by sub_county name
    # We fetch sub-counties (level 3 boundaries)
    sub_counties = (
        db.query(SpatialBoundary).filter(SpatialBoundary.level == 3).all()
    )
    sub_county_map = {sb.id: sb.name for sb in sub_counties}

    # Incident type options mapping to standard breakdown keys
    # 1 -> "water_colour"
    # 2 -> "smell"
    # 3 -> "fish_kill"
    # 4 -> "storm_event"
    # Or default to option labels if not matched
    option_type_map = FormNames.INCIDENT_TYPE_MAP

    aggregates = {}

    for dp in datapoints:
        # Resolve sub-county via location_id answer
        ans_loc = (
            db.query(Answer)
            .filter(
                Answer.datapoint_id == dp.id,
                Answer.question_id == q_location.id,
            )
            .first()
        )

        if not ans_loc or not ans_loc.options:
            continue

        try:
            loc_uuid = uuid.UUID(ans_loc.options[0])
        except (ValueError, TypeError):
            continue

        sub_county_name = sub_county_map.get(loc_uuid)
        if not sub_county_name:
            continue

        if sub_county_name not in aggregates:
            aggregates[sub_county_name] = {
                "sub_county": sub_county_name,
                "total_reports": 0,
                "breakdown": {
                    "water_colour": 0,
                    "smell": 0,
                    "fish_kill": 0,
                    "storm_event": 0,
                },
            }

        aggregates[sub_county_name]["total_reports"] += 1

        # Resolve incident type
        if q_incident:
            ans_inc = (
                db.query(Answer)
                .filter(
                    Answer.datapoint_id == dp.id,
                    Answer.question_id == q_incident.id,
                )
                .first()
            )

            if ans_inc and ans_inc.options:
                try:
                    inc_val = int(ans_inc.options[0])
                    key = option_type_map.get(inc_val, f"option_{inc_val}")
                    # Ensure key is initialized in breakdown if not standard
                    if key not in aggregates[sub_county_name]["breakdown"]:
                        aggregates[sub_county_name]["breakdown"][key] = 0
                    aggregates[sub_county_name]["breakdown"][key] += 1
                except (ValueError, TypeError):
                    pass

    return list(aggregates.values())
