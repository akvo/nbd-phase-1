from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.submission import Datapoint, Answer
from app.models.form import Form
from app.schemas import submission as schemas

router = APIRouter(prefix="/api/v1/submissions", tags=["submissions"])


@router.post(
    "",
    response_model=schemas.DatapointResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_submission(
    payload: schemas.DatapointCreate, db: Session = Depends(get_db)
):
    # Verify form exists
    form = db.query(Form).filter(Form.id == payload.form_id).first()
    if not form:
        raise HTTPException(
            status_code=404,
            detail=f"Form with ID {payload.form_id} not found.",
        )

    # Prepare datapoint
    db_datapoint = Datapoint(
        form_id=payload.form_id,
        published_version_id=payload.published_version_id,
        name=payload.name,
        basin_id=payload.basin_id,
        wetland_id=payload.wetland_id,
        site_id=payload.site_id,
        geo=payload.geo,
        duration=payload.duration,
        submitter=payload.submitter,
        status=payload.status,
    )

    try:
        db.add(db_datapoint)
        db.flush()  # Generate ID for answers

        # Add answers
        for ans in payload.answers:
            db_answer = Answer(
                datapoint_id=db_datapoint.id,
                question_id=ans.question_id,
                name=ans.name,
                value=ans.value,
                options=ans.options,
                index=ans.index,
            )
            db.add(db_answer)

        db.commit()
        db.refresh(db_datapoint)
        return db_datapoint
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[schemas.DatapointResponse])
def list_submissions(
    form_id: Optional[int] = None,
    basin_id: Optional[str] = None,
    wetland_id: Optional[str] = None,
    site_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Datapoint)
    if form_id is not None:
        query = query.filter(Datapoint.form_id == form_id)
    if basin_id is not None:
        query = query.filter(Datapoint.basin_id == basin_id)
    if wetland_id is not None:
        query = query.filter(Datapoint.wetland_id == wetland_id)
    if site_id is not None:
        query = query.filter(Datapoint.site_id == site_id)
    if status is not None:
        query = query.filter(Datapoint.status == status)
    return query.all()
