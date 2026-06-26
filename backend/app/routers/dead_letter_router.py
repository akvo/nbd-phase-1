from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.dead_letter import DeadLetter
from app.schemas import dead_letter as schemas
from app.models.user import User
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/api/v1/dead-letters", tags=["dead-letters"])


@router.post(
    "",
    response_model=schemas.DeadLetterResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_dead_letter(
    payload: schemas.DeadLetterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_dead_letter = DeadLetter(
        source_system=payload.source_system,
        raw_payload=payload.raw_payload,
        error_reason=payload.error_reason,
        status=payload.status,
    )
    try:
        db.add(db_dead_letter)
        db.commit()
        db.refresh(db_dead_letter)
        return db_dead_letter
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.get("", response_model=List[schemas.DeadLetterResponse])
def list_dead_letters(
    status: Optional[str] = None,
    source_system: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(DeadLetter)
    if status is not None:
        query = query.filter(DeadLetter.status == status)
    if source_system is not None:
        query = query.filter(DeadLetter.source_system == source_system)
    return query.all()


@router.get("/{dead_letter_id}", response_model=schemas.DeadLetterResponse)
def get_dead_letter(dead_letter_id: UUID, db: Session = Depends(get_db)):
    db_dead_letter = (
        db.query(DeadLetter).filter(DeadLetter.id == dead_letter_id).first()
    )
    if not db_dead_letter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DeadLetter with ID '{dead_letter_id}' not found.",
        )
    return db_dead_letter


@router.put("/{dead_letter_id}", response_model=schemas.DeadLetterResponse)
def update_dead_letter(
    dead_letter_id: UUID,
    payload: schemas.DeadLetterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_dead_letter = (
        db.query(DeadLetter).filter(DeadLetter.id == dead_letter_id).first()
    )
    if not db_dead_letter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DeadLetter with ID '{dead_letter_id}' not found.",
        )

    db_dead_letter.status = payload.status
    try:
        db.commit()
        db.refresh(db_dead_letter)
        return db_dead_letter
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
