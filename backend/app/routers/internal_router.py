from typing import List, Union, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.submission import Datapoint, Answer, SubmissionStatus
from app.models.user import User
from app.dependencies.auth import get_current_user
import logging


logger = logging.getLogger(__name__)

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


SpatialAnchorType = Optional[
    Union[UUID, str, int, List[Union[UUID, str, int]]]
]


class AnswerPayload(BaseModel):
    question_id: Union[int, str]
    value: Union[float, str, list, dict, None]
    name: Optional[str] = None
    val_num: Optional[float] = None
    options: Optional[List[str]] = None


def _extract_terminal_val(val: Union[UUID, str, int, list, tuple, None]):
    if isinstance(val, (list, tuple)):
        return val[-1] if len(val) > 0 else None
    return val


def _resolve_site(val, db: Session) -> Optional[UUID]:
    if val is None:
        return None
    val = _extract_terminal_val(val)
    if val is None or val in ("null", "None", ""):
        return None
    from app.models.spatial import Site
    from sqlalchemy import func

    # 1. Try UUID
    try:
        if isinstance(val, UUID):
            site_uuid = val
        else:
            site_uuid = UUID(str(val).strip())
        site = db.query(Site).filter(Site.id == site_uuid).first()
        if site:
            return site.id
    except (ValueError, TypeError, AttributeError):
        pass

    # 2. Try code or name
    val_str = str(val).strip()
    site = (
        db.query(Site)
        .filter(
            (func.lower(Site.code) == func.lower(val_str))
            | (func.lower(Site.name) == func.lower(val_str))
        )
        .first()
    )
    return site.id if site else None


def _resolve_wetland(val, db: Session) -> Optional[UUID]:
    if val is None:
        return None
    val = _extract_terminal_val(val)
    if val is None or val in ("null", "None", ""):
        return None
    from app.models.spatial import Wetland
    from sqlalchemy import func

    # 1. Try UUID
    try:
        if isinstance(val, UUID):
            wetland_uuid = val
        else:
            wetland_uuid = UUID(str(val).strip())
        wetland = db.query(Wetland).filter(Wetland.id == wetland_uuid).first()
        if wetland:
            return wetland.id
    except (ValueError, TypeError, AttributeError):
        pass

    # 2. Try code or name
    val_str = str(val).strip()
    wetland = (
        db.query(Wetland)
        .filter(
            (func.lower(Wetland.code) == func.lower(val_str))
            | (func.lower(Wetland.name) == func.lower(val_str))
        )
        .first()
    )
    return wetland.id if wetland else None


def _resolve_basin(val, db: Session) -> Optional[UUID]:
    if val is None:
        return None
    val = _extract_terminal_val(val)
    if val is None or val in ("null", "None", ""):
        return None
    from app.models.spatial import Basin
    from sqlalchemy import func

    # 1. Try UUID
    try:
        if isinstance(val, UUID):
            basin_uuid = val
        else:
            basin_uuid = UUID(str(val).strip())
        basin = db.query(Basin).filter(Basin.id == basin_uuid).first()
        if basin:
            return basin.id
    except (ValueError, TypeError, AttributeError):
        pass

    # 2. Try code or name
    val_str = str(val).strip()
    basin = (
        db.query(Basin)
        .filter(
            (func.lower(Basin.code) == func.lower(val_str))
            | (func.lower(Basin.name) == func.lower(val_str))
        )
        .first()
    )
    return basin.id if basin else None


def resolve_answers_and_anchors(payload: BaseModel, db: Session):
    from app.models.form import Question, QuestionType
    from app.services.storage import StorageService, build_blob_path
    import base64
    import json

    form_id = getattr(payload, "form_id")
    questions = db.query(Question).filter(Question.form_id == form_id).all()
    q_map = {q.id: q for q in questions}
    q_name_map = {q.name: q for q in questions if q.name}

    raw_answers = []
    # If legacy answers list is already provided in the payload, use it
    if hasattr(payload, "answers") and getattr(payload, "answers") is not None:
        for ans in getattr(payload, "answers"):
            raw_answers.append((ans.question_id, ans.value))
    else:
        # Otherwise, parse from extra dictionary
        raw_data = payload.model_extra or {}
        for key, val in raw_data.items():
            if key in ("datapoint", "sampling_period"):
                continue
            raw_answers.append((key, val))

        # Check explicit anchor fields
        # to see if they correspond to questions in this form
        for anchor_key in (
            "site_id",
            "wetland_id",
            "basin_id",
            "location_id",
        ):
            anchor_val = getattr(payload, anchor_key, None)
            if anchor_val is not None:
                if anchor_key in q_name_map and not any(
                    str(k) == anchor_key for k, _ in raw_answers
                ):
                    raw_answers.append((anchor_key, anchor_val))

    # Also extract potential anchors from Pydantic properties and raw dict keys
    raw_data = (
        payload.model_extra or {} if not hasattr(payload, "answers") else {}
    )
    raw_wetland_val = (
        getattr(payload, "wetland_id", None)
        or raw_data.get("wetland_id")
        or raw_data.get("wetland")
    )
    raw_site_val = (
        getattr(payload, "site_id", None)
        or raw_data.get("site_id")
        or raw_data.get("site")
    )
    raw_basin_val = (
        getattr(payload, "basin_id", None)
        or raw_data.get("basin_id")
        or raw_data.get("basin")
    )

    resolved_wetland_id = _resolve_wetland(raw_wetland_val, db)
    resolved_site_id = _resolve_site(raw_site_val, db)
    resolved_basin_id = _resolve_basin(raw_basin_val, db)

    answers = []

    for key, val in raw_answers:
        if val is None:
            continue

        q_def = None
        try:
            q_id_int = int(key)
            q_def = q_map.get(q_id_int)
        except ValueError:
            pass

        if not q_def:
            q_def = q_name_map.get(str(key))

        if not q_def:
            continue

        q_id = q_def.id
        q_type = q_def.type
        val_name = None
        val_num = None
        val_opts = None

        # Resolve spatial anchors on the fly for cascade select
        if q_type == QuestionType.cascade:
            opt = q_def.extra.get("option") if q_def.extra else None
            if (
                not opt
                and hasattr(q_def, "option")
                and isinstance(q_def.option, str)
            ):
                opt = q_def.option
            endpoint = ""
            if q_def.api and isinstance(q_def.api, dict):
                endpoint = q_def.api.get("endpoint") or ""

            terminal_val = _extract_terminal_val(val)

            if q_def.name == "location_id" or "sub-counties" in endpoint:
                from app.models.spatial import SpatialBoundary
                import uuid

                sb = None
                try:
                    sb_uuid = uuid.UUID(str(terminal_val))
                    sb = (
                        db.query(SpatialBoundary)
                        .filter(SpatialBoundary.id == sb_uuid)
                        .first()
                    )
                except (ValueError, TypeError):
                    sb = (
                        db.query(SpatialBoundary)
                        .filter(
                            SpatialBoundary.name.ilike(
                                str(terminal_val).strip()
                            )
                        )
                        .first()
                    )
                if sb and not resolved_basin_id:
                    resolved_basin_id = sb.basin_id
            elif (
                opt in ("wetland", "administration")
                or "wetlands" in endpoint
                or q_def.name in ("wetland", "wetland_id", "wetland_code")
            ):
                if not resolved_wetland_id:
                    resolved_wetland_id = _resolve_wetland(terminal_val, db)
            elif (
                opt == "site"
                or "sites" in endpoint
                or q_def.name in ("site", "site_id", "site_code")
            ):
                if not resolved_site_id:
                    resolved_site_id = _resolve_site(terminal_val, db)
            elif (
                opt == "basin"
                or "basins" in endpoint
                or q_def.name in ("basin", "basin_id", "basin_code")
            ):
                if not resolved_basin_id:
                    resolved_basin_id = _resolve_basin(terminal_val, db)

        # Map type specific values
        if q_type == QuestionType.number:
            try:
                val_num = float(val)
            except (ValueError, TypeError):
                pass
        elif q_type == QuestionType.cascade:
            from app.models.spatial import (
                SpatialBoundary,
                Site,
                Wetland,
                Basin,
            )

            terminal_val = val[-1] if isinstance(val, list) and val else val
            val_opts = (
                [str(x) for x in val] if isinstance(val, list) else [str(val)]
            )
            resolved_entity_name = None
            if terminal_val:
                try:
                    uuid_val = UUID(str(terminal_val))
                    sb = (
                        db.query(SpatialBoundary)
                        .filter(SpatialBoundary.id == uuid_val)
                        .first()
                    )
                    if sb:
                        resolved_entity_name = sb.name
                    else:
                        st = db.query(Site).filter(Site.id == uuid_val).first()
                        if st:
                            resolved_entity_name = st.name
                        else:
                            wt = (
                                db.query(Wetland)
                                .filter(Wetland.id == uuid_val)
                                .first()
                            )
                            if wt:
                                resolved_entity_name = wt.name
                            else:
                                ba = (
                                    db.query(Basin)
                                    .filter(Basin.id == uuid_val)
                                    .first()
                                )
                                if ba:
                                    resolved_entity_name = ba.name
                except (ValueError, TypeError):
                    pass
            val_name = resolved_entity_name or str(terminal_val)
        elif q_type in (QuestionType.option, QuestionType.multiple_option):
            if isinstance(val, list):
                val_opts = [str(x) for x in val]
            else:
                val_opts = [str(val)]
        elif q_type in (
            QuestionType.image,
            QuestionType.signature,
            QuestionType.attachment,
        ):
            if isinstance(val, str) and val.startswith("data:"):
                try:
                    header, base64_data = val.split(";base64,")
                    content_type = header.replace("data:", "")
                    ext = content_type.split("/")[-1]
                    if ext == "jpeg":
                        ext = "jpg"
                    img_bytes = base64.b64decode(base64_data)
                    blob_path = build_blob_path("webforms", ext)
                    storage = StorageService()
                    storage.upload_file(img_bytes, blob_path, content_type)
                    val_name = blob_path
                except Exception:
                    val_name = val
            else:
                val_name = str(val)
        else:
            if isinstance(val, (dict, list)):
                val_name = json.dumps(val)
            else:
                val_name = str(val)

        answers.append(
            AnswerPayload(
                question_id=q_id,
                value=val,
                name=val_name,
                val_num=val_num,
                options=val_opts,
            )
        )

    # 2. Try to resolve site_id, wetland_id, or basin_id from answers
    # if not explicitly passed
    if not resolved_site_id:
        for ans in answers:
            q = q_map.get(ans.question_id)
            if q and q.name in ("site", "site_id", "site_code", "location_id"):
                candidate = (
                    ans.options[-1] if ans.options else (ans.name or ans.value)
                )
                resolved_site_id = _resolve_site(candidate, db)
                if resolved_site_id:
                    break

    if not resolved_wetland_id:
        for ans in answers:
            q = q_map.get(ans.question_id)
            if q and q.name in ("wetland", "wetland_id", "wetland_code"):
                candidate = (
                    ans.options[-1] if ans.options else (ans.name or ans.value)
                )
                resolved_wetland_id = _resolve_wetland(candidate, db)
                if resolved_wetland_id:
                    break

    if not resolved_basin_id:
        for ans in answers:
            q = q_map.get(ans.question_id)
            if q and q.name in ("basin", "basin_id", "basin_code"):
                candidate = (
                    ans.options[-1] if ans.options else (ans.name or ans.value)
                )
                resolved_basin_id = _resolve_basin(candidate, db)
                if resolved_basin_id:
                    break

    return answers, resolved_wetland_id, resolved_site_id, resolved_basin_id


class FgdPayload(BaseModel):
    wetland_id: SpatialAnchorType = None
    form_id: int
    answers: Optional[List[AnswerPayload]] = None

    model_config = ConfigDict(extra="allow")


class LabQaPayload(BaseModel):
    site_id: SpatialAnchorType = None
    sampling_period: Optional[str] = None
    form_id: int
    answers: Optional[List[AnswerPayload]] = None

    model_config = ConfigDict(extra="allow")


class GenericPayload(BaseModel):
    form_id: int
    basin_id: SpatialAnchorType = None
    wetland_id: SpatialAnchorType = None
    site_id: SpatialAnchorType = None
    answers: Optional[List[AnswerPayload]] = None

    model_config = ConfigDict(extra="allow")


@router.post("/fgd")
def submit_fgd(
    payload: FgdPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user = current_user
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
            status=SubmissionStatus.APPROVED,
            created_by_id=user_id,
        )
        db.add(dp)
        db.flush()  # get dp.id

        # Map answers and calculate average
        qualitative_weights = []
        for ans in answers:
            val_str = ans.name if ans.name is not None else str(ans.value)
            val_str_upper = val_str.upper().strip()
            # If answer matches a weight, collect it for average
            if val_str_upper in IK_WEIGHTS:
                qualitative_weights.append(IK_WEIGHTS[val_str_upper])

            # Save raw answer
            answer_record = Answer(
                datapoint_id=dp.id,
                question_id=ans.question_id,
                name=val_str,
                options=ans.options,
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

        # Trigger FGD handler to create the FgdRecord row in the database
        from app.services.scoring import get_handler
        from app.models.form import FormType

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


@router.post("/lab-qa")
def submit_lab_qa(
    payload: LabQaPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user = current_user
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
            submitter=sampling_period,  # store period in meta columns
            status=SubmissionStatus.APPROVED,
            created_by_id=user_id,
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
                created_by_id=user_id,
            )
            db.add(answer_record)

        db.commit()

        # Trigger auto-reconciliation check
        from app.services.reconciliation import reconcile_lab_datapoint

        try:
            reconcile_lab_datapoint(db, dp.id)
        except Exception as recon_err:
            # Prevent failure of submission if reconciliation fails
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                "Reconciliation failed for lab datapoint "
                f"{dp.id}: {recon_err}",
                exc_info=True,
            )

        return {"status": "success", "datapoint_id": dp.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/submit")
def submit_generic(
    payload: GenericPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user = current_user
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
                detail=(
                    "Exactly one of basin_id, wetland_id, "
                    "or site_id must be populated"
                ),
            )

        # Create Datapoint under PENDING status
        dp = Datapoint(
            form_id=payload.form_id,
            basin_id=basin_id,
            wetland_id=wetland_id,
            site_id=site_id,
            status=SubmissionStatus.PENDING,
            created_by_id=user_id,
        )
        db.add(dp)
        db.flush()

        # Save all dynamic answers
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
                created_by_id=user_id,
            )
            db.add(answer_record)

        db.commit()
        return {"status": "success", "datapoint_id": dp.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
