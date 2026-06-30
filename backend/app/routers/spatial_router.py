import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import shape

from app.database import get_db
from app.dependencies.auth import RoleChecker
from app.models.audit_log import AuditLog
from app.models.health_score import HealthScore
from app.models.management_action import ManagementAction
from app.models.sampling_record import SamplingRecord
from app.models.spatial import Basin, Wetland, Site, SpatialBoundary
from app.models.user import User
from app.schemas import spatial as schemas
from app.services.scoring.handlers.wetland import (
    map_class_to_color,
    get_latest_fgd_record,
)

router = APIRouter(prefix="/api/v1", tags=["spatial"])

# Admin-only role checker for site management write operations
admin_only = RoleChecker(["Admin"])


def compute_site_status(db: Session, db_site: Site) -> None:
    """Compute and attach status data to a site object."""
    latest_score = (
        db.query(HealthScore)
        .filter(HealthScore.site_id == db_site.id)
        .order_by(HealthScore.calculated_at.desc())
        .first()
    )

    if not latest_score:
        db_site.status = None
        db_site.management_actions = []
        return

    h_class = latest_score.health_class
    traffic_light, color_db = map_class_to_color(h_class)

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
            "status": "Low" if latest_sampling.do_value < 5.0 else "Normal",
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

    # Calculate group scores
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
        ecological_val = float(1.0 - (float(eco_raw) / 100.0))
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

    # Fetch FGD record details
    fgd = get_latest_fgd_record(db, db_site.id)
    if fgd:
        ik_signal_map = {
            "fish_abundance": fgd.fish_abundance,
            "water_clarity": fgd.water_clarity,
            "vegetation_cover": fgd.vegetation_cover,
            "pollution_events": "None",
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


@router.post(
    "/basins",
    response_model=schemas.Basin,
    status_code=status.HTTP_201_CREATED,
)
def create_basin(
    basin: schemas.BasinCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    # Check if already exists by slug
    existing = db.query(Basin).filter(Basin.code == basin.code).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Basin with ID '{basin.code}' already exists.",
        )

    try:
        db_basin = Basin(
            code=basin.code,
            name=basin.name,
            geom=from_shape(shape(basin.geom), srid=4326),
        )
        db.add(db_basin)
        db.commit()
        db.refresh(db_basin)
        return db_basin
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/basins", response_model=list[schemas.Basin])
def list_basins(db: Session = Depends(get_db)):
    return db.query(Basin).all()


@router.get("/basins/{basin_id}", response_model=schemas.Basin)
def get_basin(basin_id: str, db: Session = Depends(get_db)):
    try:
        val = uuid.UUID(basin_id)
        db_basin = db.query(Basin).filter(Basin.id == val).first()
    except ValueError:
        db_basin = db.query(Basin).filter(Basin.code == basin_id).first()

    if not db_basin:
        raise HTTPException(
            status_code=404, detail=f"Basin '{basin_id}' not found."
        )
    return db_basin


@router.post(
    "/wetlands",
    response_model=schemas.Wetland,
    status_code=status.HTTP_201_CREATED,
)
def create_wetland(
    wetland: schemas.WetlandCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    # Check if parent basin exists
    parent_basin = db.query(Basin).filter(Basin.id == wetland.basin_id).first()
    if not parent_basin:
        raise HTTPException(
            status_code=400,
            detail=f"Parent Basin '{wetland.basin_id}' does not exist.",
        )

    # Check if already exists by slug
    existing = db.query(Wetland).filter(Wetland.code == wetland.code).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Wetland with ID '{wetland.code}' already exists.",
        )

    try:
        geom_shape = shape(wetland.geom)
        from shapely.geometry import Polygon, MultiPolygon

        if isinstance(geom_shape, Polygon):
            geom_shape = MultiPolygon([geom_shape])

        db_wetland = Wetland(
            code=wetland.code,
            basin_id=wetland.basin_id,
            name=wetland.name,
            geom=from_shape(geom_shape, srid=4326),
        )
        db.add(db_wetland)
        db.commit()
        db.refresh(db_wetland)
        return db_wetland
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/wetlands/{wetland_id}", response_model=schemas.Wetland)
def get_wetland(wetland_id: str, db: Session = Depends(get_db)):
    try:
        val = uuid.UUID(wetland_id)
        db_wetland = db.query(Wetland).filter(Wetland.id == val).first()
    except ValueError:
        db_wetland = (
            db.query(Wetland).filter(Wetland.code == wetland_id).first()
        )

    if not db_wetland:
        raise HTTPException(
            status_code=404, detail=f"Wetland '{wetland_id}' not found."
        )
    return db_wetland


@router.post(
    "/sites",
    response_model=schemas.Site,
    status_code=status.HTTP_201_CREATED,
)
def create_site(
    site: schemas.SiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    # Check if parent wetland exists
    parent_wetland = (
        db.query(Wetland).filter(Wetland.id == site.wetland_id).first()
    )
    if not parent_wetland:
        raise HTTPException(
            status_code=400,
            detail=f"Parent Wetland '{site.wetland_id}' does not exist.",
        )

    # Check if already exists
    existing = db.query(Site).filter(Site.code == site.code).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Site with ID '{site.code}' already exists.",
        )

    try:
        db_site = Site(
            code=site.code,
            wetland_id=site.wetland_id,
            name=site.name,
            description=site.description,
            geom=from_shape(shape(site.geom), srid=4326),
        )
        db.add(db_site)
        db.flush()

        # Log the create action
        audit_log = AuditLog(
            actor_id=current_user.id,
            action="CREATE",
            entity_type="site",
            entity_id=str(db_site.id),
        )
        db.add(audit_log)
        db.commit()
        db.refresh(db_site)
        return db_site
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/sites/{site_id}", response_model=schemas.Site)
def update_site(
    site_id: str,
    site: schemas.SiteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    # Find the site
    try:
        val = uuid.UUID(site_id)
        db_site = db.query(Site).filter(Site.id == val).first()
    except ValueError:
        db_site = db.query(Site).filter(Site.code == site_id).first()

    if not db_site:
        raise HTTPException(
            status_code=404, detail=f"Site '{site_id}' not found."
        )

    # Update fields if provided
    if site.code is not None:
        # Check for code uniqueness
        existing = (
            db.query(Site)
            .filter(Site.code == site.code, Site.id != db_site.id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Site with code '{site.code}' already exists.",
            )
        db_site.code = site.code

    if site.wetland_id is not None:
        # Check if parent wetland exists
        parent_wetland = (
            db.query(Wetland).filter(Wetland.id == site.wetland_id).first()
        )
        if not parent_wetland:
            raise HTTPException(
                status_code=400,
                detail=f"Parent Wetland '{site.wetland_id}' does not exist.",
            )
        db_site.wetland_id = site.wetland_id

    if site.name is not None:
        db_site.name = site.name

    if site.description is not None:
        db_site.description = site.description

    if site.geom is not None:
        db_site.geom = from_shape(shape(site.geom), srid=4326)

    try:
        # Log the update action
        audit_log = AuditLog(
            actor_id=current_user.id,
            action="UPDATE",
            entity_type="site",
            entity_id=str(db_site.id),
        )
        db.add(audit_log)
        db.commit()
        db.refresh(db_site)
        return db_site
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/sites/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(
    site_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    # Find the site
    try:
        val = uuid.UUID(site_id)
        db_site = db.query(Site).filter(Site.id == val).first()
    except ValueError:
        db_site = db.query(Site).filter(Site.code == site_id).first()

    if not db_site:
        raise HTTPException(
            status_code=404, detail=f"Site '{site_id}' not found."
        )

    site_id_str = str(db_site.id)

    try:
        db.delete(db_site)

        # Log the delete action
        audit_log = AuditLog(
            actor_id=current_user.id,
            action="DELETE",
            entity_type="site",
            entity_id=site_id_str,
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/reference/sub-counties",
    response_model=schemas.SpatialBoundary,
    status_code=status.HTTP_201_CREATED,
)
def create_sub_county(
    sb: schemas.SpatialBoundaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    # Check if parent basin exists
    parent_basin = db.query(Basin).filter(Basin.id == sb.basin_id).first()
    if not parent_basin:
        raise HTTPException(
            status_code=400,
            detail=f"Parent Basin '{sb.basin_id}' does not exist.",
        )

    try:
        db_sb = SpatialBoundary(
            name=sb.name,
            level=sb.level,
            parent_id=sb.parent_id,
            basin_id=sb.basin_id,
            centroid_geom=(
                from_shape(shape(sb.centroid_geom), srid=4326)
                if sb.centroid_geom
                else None
            ),
        )
        db.add(db_sb)
        db.commit()
        db.refresh(db_sb)
        return db_sb
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/reference/sub-counties",
    response_model=list[schemas.SpatialBoundary],
)
def list_all_sub_counties(db: Session = Depends(get_db)):
    return db.query(SpatialBoundary).all()


@router.get(
    "/reference/sub-counties/{parent_id}",
    response_model=list[schemas.SpatialBoundary],
)
def list_sub_counties(
    parent_id: Optional[str] = None, db: Session = Depends(get_db)
):
    if parent_id is None:
        return db.query(SpatialBoundary).all()
    if parent_id in ("0", 0, "null", "None", ""):
        # Root level: level = 1
        return (
            db.query(SpatialBoundary).filter(SpatialBoundary.level == 1).all()
        )
    try:
        parent_uuid = uuid.UUID(parent_id)
        return (
            db.query(SpatialBoundary)
            .filter(SpatialBoundary.parent_id == parent_uuid)
            .all()
        )
    except (ValueError, TypeError):
        return []


@router.get("/reference/wetlands")
def list_all_reference_wetlands(db: Session = Depends(get_db)):
    wetlands = db.query(Wetland).all()
    results = []
    for w in wetlands:
        results.append(
            {
                "id": str(w.id),
                "name": w.name,
                "parent_id": str(w.basin_id),
            }
        )
    return results


@router.get("/reference/wetlands/{parent_id}")
def list_reference_wetlands(
    parent_id: Optional[str] = None, db: Session = Depends(get_db)
):
    if parent_id is None or parent_id in ("0", 0, "null", "None", ""):
        wetlands = db.query(Wetland).all()
    else:
        try:
            parent_uuid = uuid.UUID(parent_id)
            wetlands = (
                db.query(Wetland).filter(Wetland.basin_id == parent_uuid).all()
            )
        except (ValueError, TypeError):
            return []

    results = []
    for w in wetlands:
        results.append(
            {
                "id": str(w.id),
                "name": w.name,
                "parent_id": str(w.basin_id),
            }
        )
    return results


@router.get("/reference/sites")
def list_all_reference_sites(db: Session = Depends(get_db)):
    sites = db.query(Site).all()
    results = []
    # Add Sites under Wetlands
    for site in sites:
        results.append(
            {
                "id": str(site.id),
                "name": site.name,
                "parent_id": str(site.wetland_id),
            }
        )
    return results


@router.get("/reference/sites/{parent_id}")
def list_reference_sites(
    parent_id: Optional[str] = None, db: Session = Depends(get_db)
):
    if parent_id is None or parent_id in ("0", 0, "null", "None", ""):
        sites = db.query(Site).all()
    else:
        try:
            parent_uuid = uuid.UUID(parent_id)
            sites = db.query(Site).filter(Site.wetland_id == parent_uuid).all()
        except (ValueError, TypeError):
            return []

    results = []
    # Add Sites under Wetlands
    for site in sites:
        results.append(
            {
                "id": str(site.id),
                "name": site.name,
                "parent_id": str(site.wetland_id),
            }
        )
    return results
