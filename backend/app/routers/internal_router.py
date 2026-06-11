from typing import List, Union, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.submission import Datapoint, Answer
from pydantic import BaseModel, Field, ConfigDict

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
    wetland_id: Optional[UUID] = None
    form_id: int
    answers: Optional[List[AnswerPayload]] = None

    model_config = ConfigDict(extra="allow")


class LabQaPayload(BaseModel):
    site_id: Optional[UUID] = None
    sampling_period: Optional[str] = None
    form_id: int
    answers: Optional[List[AnswerPayload]] = None

    model_config = ConfigDict(extra="allow")


class GenericPayload(BaseModel):
    form_id: int
    basin_id: Optional[UUID] = None
    wetland_id: Optional[UUID] = None
    site_id: Optional[UUID] = None
    answers: Optional[List[AnswerPayload]] = None

    model_config = ConfigDict(extra="allow")


def resolve_answers_and_anchors(payload: BaseModel, db: Session):
    # If legacy answers list is already provided in the payload, use it
    if hasattr(payload, "answers") and getattr(payload, "answers") is not None:
        return (
            getattr(payload, "answers"),
            getattr(payload, "wetland_id", None),
            getattr(payload, "site_id", None),
            getattr(payload, "basin_id", None),
        )

    # Otherwise, parse from extra dictionary (raw frontend key-value format)
    raw_data = payload.model_extra or {}
    form_id = getattr(payload, "form_id")

    from app.models.form import Question

    questions = db.query(Question).filter(Question.form_id == form_id).all()
    q_map = {q.id: q for q in questions}

    answers = []

    # Extract anchors from both Pydantic properties and raw dictionary string keys
    resolved_wetland_id = (
        getattr(payload, "wetland_id", None)
        or raw_data.get("wetland_id")
        or raw_data.get("wetland")
    )
    resolved_site_id = (
        getattr(payload, "site_id", None)
        or raw_data.get("site_id")
        or raw_data.get("site")
    )
    resolved_basin_id = (
        getattr(payload, "basin_id", None)
        or raw_data.get("basin_id")
        or raw_data.get("basin")
    )

    for key, val in raw_data.items():
        if key in (
            "datapoint",
            "sampling_period",
            "wetland_id",
            "wetland",
            "site_id",
            "site",
            "basin_id",
            "basin",
        ):
            continue
        try:
            q_id = int(key)
        except ValueError:
            continue

        if val is None:
            continue

        # Handle list values (e.g. cascades) by extracting the last item
        if isinstance(val, list):
            val = val[-1] if val else None

        if val is None:
            continue

        # Check question definition in database to resolve geo anchors
        q_def = q_map.get(q_id)
        if q_def and q_def.type.value == "cascade":
            opt = q_def.extra.get("option") if q_def.extra else None
            if not opt and hasattr(q_def, "option"):
                opt = q_def.option

            if opt in ("wetland", "administration"):
                if not resolved_wetland_id:
                    resolved_wetland_id = val
            elif opt == "site":
                if not resolved_site_id:
                    resolved_site_id = val
            elif opt == "basin":
                if not resolved_basin_id:
                    resolved_basin_id = val

        answers.append(AnswerPayload(question_id=q_id, value=val))

    # Cast to UUID if they are valid UUID strings
    if resolved_wetland_id and isinstance(resolved_wetland_id, str):
        try:
            resolved_wetland_id = UUID(resolved_wetland_id)
        except ValueError:
            pass
    if resolved_site_id and isinstance(resolved_site_id, str):
        try:
            resolved_site_id = UUID(resolved_site_id)
        except ValueError:
            pass
    if resolved_basin_id and isinstance(resolved_basin_id, str):
        try:
            resolved_basin_id = UUID(resolved_basin_id)
        except ValueError:
            pass

    return answers, resolved_wetland_id, resolved_site_id, resolved_basin_id


@router.post("/fgd")
def submit_fgd(
    payload: FgdPayload,
    db: Session = Depends(get_db),
):
    try:
        user = db.query(User).first()
        user_id = user.id if user else None

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
            created_by_id=user_id,
        )
        db.add(dp)
        db.flush()  # get dp.id

        # Map answers and calculate average
        qualitative_weights = []
        for ans in answers:
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
            avg_answer = Answer(
                datapoint_id=dp.id,
                question_id=answers[0].question_id,  # associate with FGD group
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
            submitter=sampling_period,  # store period in submitter or meta columns
            status="APPROVED",
            created_by_id=user_id,
        )
        db.add(dp)
        db.flush()

        # Save all academic answers
        for ans in answers:
            try:
                val_num = float(ans.value)
            except ValueError:
                val_num = None
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
    try:
        user = db.query(User).first()
        user_id = user.id if user else None

        answers, wetland_id, site_id, basin_id = resolve_answers_and_anchors(
            payload, db
        )

        # Fallback to first basin if no anchor is resolved
        if basin_id is None and wetland_id is None and site_id is None:
            from app.models.spatial import Basin

            first_basin = db.query(Basin).first()
            if first_basin:
                basin_id = first_basin.id

        # Enforce exactly one anchor populated
        anchors_count = sum(
            1 for v in [basin_id, wetland_id, site_id] if v is not None
        )
        if anchors_count != 1:
            raise HTTPException(
                status_code=400,
                detail="Exactly one of basin_id, wetland_id, or site_id must be populated",
            )

        # Create Datapoint under PENDING status
        dp = Datapoint(
            form_id=payload.form_id,
            basin_id=basin_id,
            wetland_id=wetland_id,
            site_id=site_id,
            status="PENDING",
            created_by_id=user_id,
        )
        db.add(dp)
        db.flush()

        # Save all dynamic answers
        for ans in answers:
            try:
                val_num = float(ans.value)
            except ValueError:
                val_num = None
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
