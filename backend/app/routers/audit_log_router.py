from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_log import AuditLog
from app.schemas import audit_log as schemas

router = APIRouter(prefix="/api/v1/audit-logs", tags=["audit-logs"])


@router.post(
    "",
    response_model=schemas.AuditLogResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_audit_log(
    payload: schemas.AuditLogCreate, db: Session = Depends(get_db)
):
    db_audit_log = AuditLog(
        actor_id=payload.actor_id,
        action=payload.action,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
    )
    try:
        db.add(db_audit_log)
        db.commit()
        db.refresh(db_audit_log)
        return db_audit_log
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.get("", response_model=List[schemas.AuditLogResponse])
def list_audit_logs(
    actor_id: Optional[UUID] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if actor_id is not None:
        query = query.filter(AuditLog.actor_id == actor_id)
    if action is not None:
        query = query.filter(AuditLog.action == action)
    if entity_type is not None:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(AuditLog.entity_id == entity_id)
    return query.all()


@router.get("/{audit_log_id}", response_model=schemas.AuditLogResponse)
def get_audit_log(audit_log_id: UUID, db: Session = Depends(get_db)):
    db_audit_log = (
        db.query(AuditLog).filter(AuditLog.id == audit_log_id).first()
    )
    if not db_audit_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AuditLog with ID '{audit_log_id}' not found.",
        )
    return db_audit_log
