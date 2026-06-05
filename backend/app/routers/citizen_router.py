import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.citizen import Citizen
from app.models.spatial import Site
from app.schemas import citizen as schemas
from app.dependencies.auth import RoleChecker

router = APIRouter(prefix="/api/v1/citizens", tags=["citizens"])


@router.post(
    "",
    response_model=schemas.CitizenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["Admin"]))],
)
def create_citizen(
    payload: schemas.CitizenCreate,
    db: Session = Depends(get_db),
):
    # Verify site exists
    site = db.query(Site).filter(Site.id == payload.site_id).first()
    if not site:
        raise HTTPException(
            status_code=404,
            detail=f"Site with ID {payload.site_id} not found.",
        )

    # Validate phone format (simple check or regex)
    if (
        not payload.phone_number.startswith("+")
        or len(payload.phone_number) < 8
    ):
        raise HTTPException(
            status_code=400,
            detail="Phone number must be in E.164 format (e.g. +254...)",
        )

    db_citizen = Citizen(
        phone_number=payload.phone_number,
        site_id=payload.site_id,
        role=payload.role,
    )
    try:
        db.add(db_citizen)
        db.commit()
        db.refresh(db_citizen)
        return db_citizen
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=List[schemas.CitizenResponse],
    dependencies=[Depends(RoleChecker(["Admin", "Reviewer"]))],
)
def list_citizens(
    role: Optional[str] = None,
    site_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Citizen)
    if role:
        query = query.filter(Citizen.role == role)
    if site_id:
        query = query.filter(Citizen.site_id == site_id)
    return query.all()


@router.get(
    "/{citizen_id}",
    response_model=schemas.CitizenResponse,
    dependencies=[Depends(RoleChecker(["Admin", "Reviewer"]))],
)
def get_citizen(
    citizen_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    db_citizen = db.query(Citizen).filter(Citizen.id == citizen_id).first()
    if not db_citizen:
        raise HTTPException(
            status_code=404,
            detail=f"Citizen with ID '{citizen_id}' not found.",
        )
    return db_citizen
