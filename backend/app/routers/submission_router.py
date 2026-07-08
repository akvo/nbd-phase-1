import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.audit_log import AuditLog
from app.models.submission import Datapoint, Answer, SubmissionStatus
from app.models.form import Form, Question, QuestionType
from app.models.user import User
from app.schemas import submission as schemas
from app.services.storage import StorageService
from app.services.option_resolver import resolve_datapoint_brief_attributes

router = APIRouter(prefix="/api/v1/submissions", tags=["submissions"])


@router.post(
    "",
    response_model=schemas.PublicDatapointResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_submission(
    payload: schemas.DatapointCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

        # Fetch questions to identify types
        questions = (
            db.query(Question)
            .filter(Question.form_id == payload.form_id)
            .all()
        )
        q_map = {q.id: q for q in questions}

        # Add answers
        for ans in payload.answers:
            q = q_map.get(ans.question_id)
            name = None
            value = None
            option = None

            if q:
                if q.type in (
                    QuestionType.geo,
                    QuestionType.option,
                    QuestionType.multiple_option,
                ):
                    if ans.options is not None:
                        option = ans.options
                    elif ans.value is not None:
                        option = (
                            ans.options
                            if isinstance(ans.options, list)
                            else [ans.value]
                        )
                elif q.type in (
                    QuestionType.input,
                    QuestionType.text,
                    QuestionType.image,
                    QuestionType.date,
                    QuestionType.autofield,
                    QuestionType.attachment,
                    QuestionType.signature,
                ):
                    name = (
                        str(ans.value) if ans.value is not None else ans.name
                    )
                elif q.type == QuestionType.cascade:
                    val_id = (
                        ans.value
                        if ans.value is not None
                        else (ans.options[0] if ans.options else None)
                    )
                    option = [str(val_id)] if val_id else None
                    from app.models.spatial import SpatialBoundary

                    boundary = None
                    if val_id:
                        boundary = (
                            db.query(SpatialBoundary)
                            .filter(SpatialBoundary.id == val_id)
                            .first()
                        )
                    if boundary:
                        name = boundary.name
                    else:
                        name = ans.name
                else:
                    value = str(ans.value) if ans.value is not None else None
            else:
                # Fallback if question not found
                if ans.options is not None:
                    option = ans.options
                else:
                    try:
                        value = (
                            float(ans.value) if ans.value is not None else None
                        )
                    except (ValueError, TypeError):
                        name = (
                            str(ans.value)
                            if ans.value is not None
                            else ans.name
                        )

            db_answer = Answer(
                datapoint_id=db_datapoint.id,
                question_id=ans.question_id,
                name=name,
                value=value,
                options=option,
                index=ans.index,
            )
            db.add(db_answer)

        db.commit()
        db.refresh(db_datapoint)
        try:
            StorageService().populate_answers_read_urls([db_datapoint])
            from app.services.option_resolver import (
                populate_answers_option_labels,
            )

            populate_answers_option_labels([db_datapoint], db)
        except Exception:
            pass
        return db_datapoint
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=List[schemas.PublicDatapointResponse],
)
def list_submissions(
    form_id: Optional[int] = None,
    domain: Optional[str] = None,
    basin_id: Optional[uuid.UUID] = None,
    wetland_id: Optional[uuid.UUID] = None,
    site_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    brief: bool = False,
    db: Session = Depends(get_db),
):
    from sqlalchemy.orm import joinedload

    query = db.query(Datapoint).options(
        joinedload(Datapoint.basin),
        joinedload(Datapoint.wetland),
        joinedload(Datapoint.site),
        joinedload(Datapoint.created_by),
    )
    if not brief:
        query = query.options(joinedload(Datapoint.answers))

    if form_id is not None:
        query = query.filter(Datapoint.form_id == form_id)
    if domain is not None:
        from app.models.form import Form, FormNames

        form_name = None
        if domain == "pollution":
            form_name = FormNames.POLLUTION_REPORTING
        elif domain == "wetland":
            form_name = FormNames.WETLAND_SAMPLING

        if form_name:
            query = query.join(Form).filter(Form.name == form_name)
    if basin_id is not None:
        query = query.filter(Datapoint.basin_id == basin_id)
    if wetland_id is not None:
        query = query.filter(Datapoint.wetland_id == wetland_id)
    if site_id is not None:
        query = query.filter(Datapoint.site_id == site_id)
    if status is not None:
        query = query.filter(Datapoint.status == status)
    results = query.all()

    if not brief:
        try:
            StorageService().populate_answers_read_urls(results)
            from app.services.option_resolver import (
                populate_answers_option_labels,
            )

            populate_answers_option_labels(results, db)
        except Exception:
            pass

    # Map database models to dictionary format safely resolving answers cache
    response_data = []
    for r in results:
        image_url, incident_type_name, incident_type_id, reported_location = (
            resolve_datapoint_brief_attributes(r, db, brief)
        )

        creator_name = None
        if r.created_by:
            creator_name = r.created_by.display_name or r.created_by.email

        response_data.append(
            {
                "id": r.id,
                "uuid": r.uuid,
                "form_id": r.form_id,
                "published_version_id": r.published_version_id,
                "name": r.name,
                "basin_id": r.basin_id,
                "wetland_id": r.wetland_id,
                "site_id": r.site_id,
                "geo": r.geo,
                "duration": r.duration,
                "submitter": r.submitter,
                "status": r.status,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "form_name": r.form.name if r.form else None,
                "basin_name": r.basin.name if r.basin else None,
                "wetland_name": r.wetland.name if r.wetland else None,
                "site_name": r.site.name if r.site else None,
                "creator_name": creator_name,
                "creator_email": r.created_by.email if r.created_by else None,
                "image_url": image_url,
                "incident_type_name": incident_type_name,
                "incident_type_id": incident_type_id,
                "reported_location": reported_location,
                "answers": [] if brief else r.answers,
            }
        )
    return response_data


@router.get(
    "/{id}",
    response_model=schemas.PublicDatapointResponse,
)
def get_submission_detail(
    id: int,
    db: Session = Depends(get_db),
):
    from sqlalchemy.orm import joinedload

    datapoint = (
        db.query(Datapoint)
        .options(
            joinedload(Datapoint.basin),
            joinedload(Datapoint.wetland),
            joinedload(Datapoint.site),
            joinedload(Datapoint.created_by),
            joinedload(Datapoint.answers),
        )
        .filter(Datapoint.id == id)
        .first()
    )
    if not datapoint:
        raise HTTPException(
            status_code=404,
            detail=f"Submission with ID {id} not found.",
        )

    try:
        StorageService().populate_answers_read_urls([datapoint])
        from app.services.option_resolver import (
            populate_answers_option_labels,
        )

        populate_answers_option_labels([datapoint], db)
    except Exception:
        pass

    # Extract first image URL and incident type name using shared helper
    image_url, incident_type_name, incident_type_id, reported_location = (
        resolve_datapoint_brief_attributes(datapoint, db, brief=False)
    )

    datapoint.image_url = image_url
    datapoint.incident_type_name = incident_type_name
    datapoint.incident_type_id = incident_type_id
    datapoint.reported_location = reported_location

    return datapoint


@router.patch("/{id}/status")
def update_submission_status(
    id: int,
    payload: schemas.SubmissionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.reconciliation import reconcile_lab_datapoint

    dp = db.query(Datapoint).filter(Datapoint.id == id).first()
    if not dp:
        raise HTTPException(
            status_code=404, detail=f"Submission with ID {id} not found."
        )

    if dp.status in (SubmissionStatus.APPROVED, SubmissionStatus.REJECTED):
        raise HTTPException(
            status_code=400, detail=f"Submission is already {dp.status}."
        )

    dp.status = payload.status

    if payload.status == SubmissionStatus.APPROVED:
        # Check if site_id is present for forms that require it (type 2 and 4)
        if dp.form and dp.form.type in (2, 4):
            if dp.site_id is None:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot approve a submission without a site_id.",
                )

        if dp.form:
            from app.services.scoring import get_handler
            from app.models.form import FormType

            handler = get_handler(FormType(dp.form.type))
            if handler:
                handler.score_submission(db, dp)

            # Trigger auto-reconciliation for matching approved Lab QA reports
            from app.models.form import Form

            lab_reports = (
                db.query(Datapoint)
                .join(Form)
                .filter(
                    Form.type == 4,
                    Datapoint.site_id == dp.site_id,
                    Datapoint.status == SubmissionStatus.APPROVED,
                )
                .all()
            )

            for report in lab_reports:
                try:
                    reconcile_lab_datapoint(db, report.id)
                except Exception as e:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.error(
                        f"Failed to reconcile Lab QA report {report.id}: {e}"
                    )

        elif dp.form and dp.form.type == 4:
            # Trigger reconciliation for this newly approved Lab QA report
            # against existing approved citizen records
            try:
                reconcile_lab_datapoint(db, dp.id)
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(
                    f"Failed to reconcile new Lab QA report {dp.id}: {e}"
                )

    try:
        # Log the action
        action = (
            "APPROVE"
            if payload.status == SubmissionStatus.APPROVED
            else "REJECT"
        )
        audit_log = AuditLog(
            actor_id=current_user.id,
            action=action,
            entity_type="submission",
            entity_id=str(dp.id),
        )
        db.add(audit_log)

        db.commit()
        return {
            "id": dp.id,
            "status": dp.status,
            "message": "Submission status updated successfully",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
