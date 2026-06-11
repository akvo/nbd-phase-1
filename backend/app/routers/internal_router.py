from typing import List, Union, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.submission import Datapoint, Answer

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])

# Weight mapping for qualitative values
IK_WEIGHTS = {
    "GOOD": 1.0,
    "INCREASED": 1.0,
    "HIGH": 1.0,
    "MODERATE": 0.5,
    "STABLE": 0.5,
    "MEDIUM": 0.5,
    "POOR": 0.0,
    "DECLINED": 0.0,
    "LOW": 0.0,
}


class AnswerPayload(BaseModel):
    question_id: int
    value: Union[float, str]


class FgdPayload(BaseModel):
    wetland_id: UUID
    form_id: int
    answers: List[AnswerPayload]


class LabQaPayload(BaseModel):
    site_id: UUID
    sampling_period: str
    form_id: int
    answers: List[AnswerPayload]


class GenericPayload(BaseModel):
    form_id: int
    basin_id: Optional[UUID] = None
    wetland_id: Optional[UUID] = None
    site_id: Optional[UUID] = None
    answers: List[AnswerPayload]


@router.post("/fgd")
def submit_fgd(
    payload: FgdPayload,
    db: Session = Depends(get_db),
):
    try:
        user = db.query(User).first()
        user_id = user.id if user else None

        # Create Datapoint
        dp = Datapoint(
            form_id=payload.form_id,
            wetland_id=payload.wetland_id,
            status="APPROVED",
            created_by_id=user_id,
        )
        db.add(dp)
        db.flush()  # get dp.id

        # Map answers and calculate average
        qualitative_weights = []
        for ans in payload.answers:
            val_str = str(ans.value).upper().strip()
            # If answer matches a weight, collect it for average
            if val_str in IK_WEIGHTS:
                qualitative_weights.append(IK_WEIGHTS[val_str])

            # Save raw answer
            answer_record = Answer(
                datapoint_id=dp.id,
                question_id=ans.question_id,
                name=str(ans.value),
                created_by_id=user_id,
            )
            db.add(answer_record)

        # Average weights for calculated IK signal
        if qualitative_weights:
            avg_weight = sum(qualitative_weights) / len(qualitative_weights)
            # Special calculated answer row in the answers table
            # question_id=0 or custom placeholder can be used for computed values
            avg_answer = Answer(
                datapoint_id=dp.id,
                question_id=payload.answers[
                    0
                ].question_id,  # associate with FGD group
                name="calculated_ik_signal",
                value=round(avg_weight, 2),
                created_by_id=user_id,
                index=999,  # unique indicator index for calculated values
            )
            db.add(avg_answer)

        db.commit()
        return {"status": "success", "datapoint_id": dp.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/lab-qa")
def submit_lab_qa(
    payload: LabQaPayload,
    db: Session = Depends(get_db),
):
    try:
        user = db.query(User).first()
        user_id = user.id if user else None

        # Create Datapoint
        dp = Datapoint(
            form_id=payload.form_id,
            site_id=payload.site_id,
            submitter=payload.sampling_period,  # store period in submitter or meta columns
            status="APPROVED",
            created_by_id=user_id,
        )
        db.add(dp)
        db.flush()

        # Save all academic answers
        for ans in payload.answers:
            val_num = (
                float(ans.value)
                if isinstance(ans.value, (int, float))
                else None
            )
            val_str = str(ans.value) if val_num is None else None
            answer_record = Answer(
                datapoint_id=dp.id,
                question_id=ans.question_id,
                value=val_num,
                name=val_str,
                created_by_id=user_id,
            )
            db.add(answer_record)

        db.commit()
        return {"status": "success", "datapoint_id": dp.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/submit")
def submit_generic(
    payload: GenericPayload,
    db: Session = Depends(get_db),
):
    # Enforce exactly one anchor populated
    anchors_count = sum(
        1
        for v in [payload.basin_id, payload.wetland_id, payload.site_id]
        if v is not None
    )
    if anchors_count != 1:
        raise HTTPException(
            status_code=400,
            detail="Exactly one of basin_id, wetland_id, or site_id must be populated",
        )

    try:
        user = db.query(User).first()
        user_id = user.id if user else None

        # Create Datapoint under PENDING status
        dp = Datapoint(
            form_id=payload.form_id,
            basin_id=payload.basin_id,
            wetland_id=payload.wetland_id,
            site_id=payload.site_id,
            status="PENDING",
            created_by_id=user_id,
        )
        db.add(dp)
        db.flush()

        # Save all dynamic answers
        for ans in payload.answers:
            val_num = (
                float(ans.value)
                if isinstance(ans.value, (int, float))
                else None
            )
            val_str = str(ans.value) if val_num is None else None
            answer_record = Answer(
                datapoint_id=dp.id,
                question_id=ans.question_id,
                value=val_num,
                name=val_str,
                created_by_id=user_id,
            )
            db.add(answer_record)

        db.commit()
        return {"status": "success", "datapoint_id": dp.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
