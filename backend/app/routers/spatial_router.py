from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import shape

from app.database import get_db
from app.models.spatial import Basin, Wetland, Site
from app.schemas import spatial as schemas

router = APIRouter(prefix="/api/v1", tags=["spatial"])


@router.post(
    "/basins",
    response_model=schemas.Basin,
    status_code=status.HTTP_201_CREATED,
)
def create_basin(basin: schemas.BasinCreate, db: Session = Depends(get_db)):
    # Check if already exists
    existing = db.query(Basin).filter(Basin.basin_id == basin.basin_id).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Basin with ID '{basin.basin_id}' already exists.",
        )

    try:
        db_basin = Basin(
            basin_id=basin.basin_id,
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


@router.get("/basins/{basin_id}", response_model=schemas.Basin)
def get_basin(basin_id: str, db: Session = Depends(get_db)):
    db_basin = db.query(Basin).filter(Basin.basin_id == basin_id).first()
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
    wetland: schemas.WetlandCreate, db: Session = Depends(get_db)
):
    # Check if parent basin exists
    parent_basin = (
        db.query(Basin).filter(Basin.basin_id == wetland.basin_id).first()
    )
    if not parent_basin:
        raise HTTPException(
            status_code=400,
            detail=f"Parent Basin '{wetland.basin_id}' does not exist.",
        )

    # Check if already exists
    existing = (
        db.query(Wetland)
        .filter(Wetland.wetland_id == wetland.wetland_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Wetland with ID '{wetland.wetland_id}' already exists.",
        )

    try:
        db_wetland = Wetland(
            wetland_id=wetland.wetland_id,
            basin_id=wetland.basin_id,
            name=wetland.name,
            geom=from_shape(shape(wetland.geom), srid=4326),
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
    db_wetland = (
        db.query(Wetland).filter(Wetland.wetland_id == wetland_id).first()
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
def create_site(site: schemas.SiteCreate, db: Session = Depends(get_db)):
    # Check if parent wetland exists
    parent_wetland = (
        db.query(Wetland).filter(Wetland.wetland_id == site.wetland_id).first()
    )
    if not parent_wetland:
        raise HTTPException(
            status_code=400,
            detail=f"Parent Wetland '{site.wetland_id}' does not exist.",
        )

    # Check if already exists
    existing = db.query(Site).filter(Site.site_id == site.site_id).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Site with ID '{site.site_id}' already exists.",
        )

    try:
        db_site = Site(
            site_id=site.site_id,
            wetland_id=site.wetland_id,
            name=site.name,
            geom=from_shape(shape(site.geom), srid=4326),
        )
        db.add(db_site)
        db.commit()
        db.refresh(db_site)
        return db_site
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sites/{site_id}", response_model=schemas.Site)
def get_site(site_id: str, db: Session = Depends(get_db)):
    db_site = db.query(Site).filter(Site.site_id == site_id).first()
    if not db_site:
        raise HTTPException(
            status_code=404, detail=f"Site '{site_id}' not found."
        )
    return db_site
