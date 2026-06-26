import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user, RoleChecker
from app.models.audit_log import AuditLog
from app.models.submission import Datapoint, Answer
from app.models.form import Form, FormType
from app.models.user import User
from app.models.dead_letter import DeadLetter
from app.schemas import submission as schemas
from app.schemas import dead_letter as dl_schemas
from app.routers.internal_router import (
    resolve_answers_and_anchors,
    FgdPayload,
    LabQaPayload,
    IK_WEIGHTS,
)

import logging

logger = logging.getLogger(__name__)

# Global router dependency for get_current_user
# ensures all routes are auth-guarded
router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/submissions",
    response_model=List[schemas.DatapointResponse],
)
def list_admin_submissions(
    form_type: Optional[int] = None,
    status: Optional[str] = None,
    basin: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Datapoint).outerjoin(Form, Datapoint.form_id == Form.id)

    if form_type is not None:
        query = query.filter(Form.type == form_type)
    if status is not None:
        query = query.filter(Datapoint.status == status)
    if basin is not None:
        from app.models.spatial import Basin

        # Case-insensitive name match on Basin
        query = query.join(Basin, Datapoint.basin_id == Basin.id).filter(
            Basin.name.ilike(f"%{basin}%")
        )

    query = query.order_by(Datapoint.created_at.asc())
    results = query.all()
    try:
        from app.services.storage import StorageService
        from app.services.option_resolver import (
            populate_answers_option_labels,
        )

        StorageService().populate_answers_read_urls(results)
        populate_answers_option_labels(results, db)
    except Exception:
        pass
    return results


@router.get(
    "/submissions/{id}",
    response_model=schemas.DatapointResponse,
)
def get_submission(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dp = db.query(Datapoint).filter(Datapoint.id == id).first()
    if not dp:
        raise HTTPException(
            status_code=404, detail=f"Submission with ID {id} not found."
        )

    try:
        from app.services.storage import StorageService
        from app.services.option_resolver import (
            populate_answers_option_labels,
        )

        StorageService().populate_answers_read_urls([dp])
        populate_answers_option_labels([dp], db)
    except Exception:
        pass
    return dp


@router.patch("/submissions/{id}/status")
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

    if dp.status in ("APPROVED", "REJECTED"):
        raise HTTPException(
            status_code=400, detail=f"Submission is already {dp.status}."
        )

    dp.status = payload.status

    if payload.status == "APPROVED":
        # Check if site_id is present for forms that require it (type 2 and 4)
        if dp.form and dp.form.type in (2, 4):
            if dp.site_id is None:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot approve a submission without a site_id.",
                )

        if dp.form:
            from app.services.scoring import get_handler

            handler = get_handler(FormType(dp.form.type))
            if handler:
                handler.score_submission(db, dp)

            # Trigger auto-reconciliation for matching approved Lab QA reports
            lab_reports = (
                db.query(Datapoint)
                .join(Form)
                .filter(
                    Form.type == 4,
                    Datapoint.site_id == dp.site_id,
                    Datapoint.status == "APPROVED",
                )
                .all()
            )

            for report in lab_reports:
                try:
                    reconcile_lab_datapoint(db, report.id)
                except Exception as e:
                    logger.error(
                        f"Failed to reconcile Lab QA report {report.id}: {e}"
                    )

        elif dp.form and dp.form.type == 4:
            # Trigger reconciliation for this newly approved Lab QA report
            # against existing approved citizen records
            try:
                reconcile_lab_datapoint(db, dp.id)
            except Exception as e:
                logger.error(
                    f"Failed to reconcile new Lab QA report {dp.id}: {e}"
                )

    try:
        # Log the action
        action = "APPROVE" if payload.status == "APPROVED" else "REJECT"
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


@router.delete("/submissions/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_submission(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin"])),
):
    dp = db.query(Datapoint).filter(Datapoint.id == id).first()
    if not dp:
        raise HTTPException(
            status_code=404, detail=f"Submission with ID {id} not found."
        )

    try:
        # Delete the datapoint (cascades to answers table)
        db.delete(dp)

        # Log the delete action
        audit_log = AuditLog(
            actor_id=current_user.id,
            action="DELETE",
            entity_type="submission",
            entity_id=str(id),
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/submissions/{id}")
def edit_submission(
    id: int,
    payload: schemas.SubmissionEditPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.form import Question, QuestionType

    dp = db.query(Datapoint).filter(Datapoint.id == id).first()
    if not dp:
        raise HTTPException(
            status_code=404, detail=f"Submission with ID {id} not found."
        )

    # Fetch questions to identify types
    questions = db.query(Question).filter(Question.form_id == dp.form_id).all()
    q_map = {q.id: q for q in questions}

    # Update or insert answers
    for ans_data in payload.answers:
        q = q_map.get(ans_data.question_id)
        name = None
        value = None
        option = None

        if q:
            if q.type in (
                QuestionType.geo,
                QuestionType.option,
                QuestionType.multiple_option,
            ):
                if ans_data.options is not None:
                    option = ans_data.options
                elif ans_data.value is not None:
                    option = (
                        ans_data.options
                        if isinstance(ans_data.options, list)
                        else [ans_data.value]
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
                    str(ans_data.value)
                    if ans_data.value is not None
                    else ans_data.name
                )
            elif q.type == QuestionType.cascade:
                val_id = (
                    ans_data.value
                    if ans_data.value is not None
                    else (ans_data.options[0] if ans_data.options else None)
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
                    name = ans_data.name
            else:
                value = (
                    str(ans_data.value) if ans_data.value is not None else None
                )
        else:
            # Fallback if question not found
            if ans_data.options is not None:
                option = ans_data.options
            else:
                try:
                    value = (
                        float(ans_data.value)
                        if ans_data.value is not None
                        else None
                    )
                except (ValueError, TypeError):
                    name = (
                        str(ans_data.value)
                        if ans_data.value is not None
                        else ans_data.name
                    )

        # Check if answer already exists
        ans = (
            db.query(Answer)
            .filter(
                Answer.datapoint_id == dp.id,
                Answer.question_id == ans_data.question_id,
                Answer.index == ans_data.index,
            )
            .first()
        )
        if ans:
            ans.name = name
            ans.value = value
            ans.options = option
        else:
            ans = Answer(
                datapoint_id=dp.id,
                question_id=ans_data.question_id,
                name=name,
                value=value,
                options=option,
                index=ans_data.index,
            )
            db.add(ans)

    try:
        # Log edit action
        audit_log = AuditLog(
            actor_id=current_user.id,
            action="EDIT",
            entity_type="submission",
            entity_id=str(id),
        )
        db.add(audit_log)
        db.commit()
        return {"id": dp.id, "message": "Submission updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/dead-letters", response_model=List[dl_schemas.DeadLetterResponse]
)
def list_admin_dead_letters(
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


@router.patch(
    "/dead-letters/{dead_letter_id}",
    response_model=dl_schemas.DeadLetterResponse,
)
def update_admin_dead_letter(
    dead_letter_id: uuid.UUID,
    payload: dl_schemas.DeadLetterUpdate,
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
        # Log the triage update action
        audit_log = AuditLog(
            actor_id=current_user.id,
            action=(
                "ACKNOWLEDGE" if payload.status == "Acknowledged" else "Update"
            ),
            entity_type="dead_letter",
            entity_id=str(db_dead_letter.id),
        )
        db.add(audit_log)

        db.commit()
        db.refresh(db_dead_letter)
        return db_dead_letter
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.post("/submissions/fgd")
def submit_fgd(
    payload: FgdPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        answers, wetland_id, site_id, basin_id = resolve_answers_and_anchors(
            payload, db
        )
        if not wetland_id:
            raise ValueError("wetland_id is required")

        # Create Datapoint
        dp = Datapoint(
            form_id=payload.form_id,
            wetland_id=wetland_id,
            status="APPROVED",
            created_by_id=current_user.id,
        )
        db.add(dp)
        db.flush()

        # Map answers and calculate average
        qualitative_weights = []
        for ans in answers:
            val_str = ans.name if ans.name is not None else str(ans.value)
            val_str_upper = val_str.upper().strip()
            if val_str_upper in IK_WEIGHTS:
                qualitative_weights.append(IK_WEIGHTS[val_str_upper])

            # Save raw answer
            answer_record = Answer(
                datapoint_id=dp.id,
                question_id=ans.question_id,
                name=val_str,
                options=ans.options,
                created_by_id=current_user.id,
            )
            db.add(answer_record)

        # Average weights for calculated IK signal
        if qualitative_weights:
            avg_weight = sum(qualitative_weights) / len(qualitative_weights)
            avg_answer = Answer(
                datapoint_id=dp.id,
                question_id=answers[0].question_id,
                name="calculated_ik_signal",
                value=round(avg_weight, 2),
                created_by_id=current_user.id,
                index=999,
            )
            db.add(avg_answer)

        # Log the manual submission creation
        audit_log = AuditLog(
            actor_id=current_user.id,
            action="CREATE",
            entity_type="submission",
            entity_id=str(dp.id),
        )
        db.add(audit_log)

        db.commit()

        # Trigger FGD handler to create the FgdRecord row in the database
        from app.services.scoring import get_handler

        handler = get_handler(FormType.INDIGENOUS_KNOWLEDGE)
        if handler:
            try:
                handler.score_submission(db, dp)
                db.commit()
            except Exception as e:
                logger.error("Failed to execute FGD scoring handler: %s", e)

        return {"status": "success", "datapoint_id": dp.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/submissions/lab-qa")
def submit_lab_qa(
    payload: LabQaPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        answers, wetland_id, site_id, basin_id = resolve_answers_and_anchors(
            payload, db
        )
        if not site_id:
            raise ValueError("site_id is required")

        sampling_period = payload.sampling_period or "2026-Q2"

        # Create Datapoint
        dp = Datapoint(
            form_id=payload.form_id,
            site_id=site_id,
            submitter=sampling_period,
            status="APPROVED",
            created_by_id=current_user.id,
        )
        db.add(dp)
        db.flush()

        # Save all academic answers
        for ans in answers:
            if (
                ans.name is not None
                or ans.val_num is not None
                or ans.options is not None
            ):
                val_num = ans.val_num
                val_str = ans.name
                val_opts = ans.options
            else:
                try:
                    val_num = float(ans.value)
                except ValueError:
                    val_num = None
                val_str = str(ans.value) if val_num is None else None
                val_opts = None

            answer_record = Answer(
                datapoint_id=dp.id,
                question_id=ans.question_id,
                value=val_num,
                name=val_str,
                options=val_opts,
                created_by_id=current_user.id,
            )
            db.add(answer_record)

        # Log the manual submission creation
        audit_log = AuditLog(
            actor_id=current_user.id,
            action="CREATE",
            entity_type="submission",
            entity_id=str(dp.id),
        )
        db.add(audit_log)

        db.commit()

        # Trigger auto-reconciliation check
        from app.services.reconciliation import reconcile_lab_datapoint

        try:
            reconcile_lab_datapoint(db, dp.id)
        except Exception as recon_err:
            logger.error(
                "Reconciliation failed for lab datapoint "
                f"{dp.id}: {recon_err}",
                exc_info=True,
            )

        return {"status": "success", "datapoint_id": dp.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
