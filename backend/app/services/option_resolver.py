from typing import List
import uuid
from sqlalchemy.orm import Session
from app.models.submission import Datapoint
from app.models.form import Option
from app.models.spatial import SpatialBoundary


def is_valid_uuid(val) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, TypeError):
        return False


def populate_answers_option_labels(
    datapoints: List[Datapoint], db: Session
) -> None:
    """
    Batch resolves option IDs and cascade boundary UUIDs
    to human-readable labels.
    """
    all_boundary_ids = []
    answers_to_resolve = []
    question_ids = []

    for dp in datapoints:
        for ans in dp.answers:
            if ans.options and isinstance(ans.options, list):
                if ans.question and ans.question.type in (
                    "option",
                    "multiple_option",
                    "cascade",
                ):
                    answers_to_resolve.append(ans)
                    question_ids.append(ans.question_id)
                    for opt_val in ans.options:
                        if is_valid_uuid(opt_val):
                            all_boundary_ids.append(opt_val)

    if not answers_to_resolve and not all_boundary_ids:
        return

    label_map = {}

    # Query Options scoped by question IDs
    if question_ids:
        options = (
            db.query(Option).filter(Option.question_id.in_(question_ids)).all()
        )
        for opt in options:
            label_map[(opt.question_id, opt.id)] = opt.label
            if opt.value:
                label_map[(opt.question_id, str(opt.value))] = opt.label
                try:
                    label_map[(opt.question_id, int(opt.value))] = opt.label
                except (ValueError, TypeError):
                    pass

    # Query Spatial Boundaries
    if all_boundary_ids:
        boundaries = (
            db.query(SpatialBoundary)
            .filter(SpatialBoundary.id.in_(all_boundary_ids))
            .all()
        )
        for b in boundaries:
            label_map[str(b.id)] = b.name
            label_map[b.id] = b.name

    for ans in answers_to_resolve:
        resolved = []
        q_id = ans.question_id
        # Flatten and resolve values. If a value contains spaces but matches
        # directly, keep it intact. Otherwise, split it into separate values.
        flat_options = []
        for val in ans.options:
            val_str = str(val).strip()
            # If the option value is directly matched in
            # label_map, keep it intact
            has_direct_match = (
                (q_id, val_str) in label_map
                or (q_id, val) in label_map
                or is_valid_uuid(val_str)
            )
            if not has_direct_match and " " in val_str:
                flat_options.extend(
                    x.strip() for x in val_str.split(" ") if x.strip()
                )
            else:
                flat_options.append(val_str)

        for val in flat_options:
            if is_valid_uuid(val):
                if val in label_map:
                    resolved.append(label_map[val])
                elif str(val) in label_map:
                    resolved.append(label_map[str(val)])
                else:
                    resolved.append(str(val))
            else:
                try:
                    int_val = int(val)
                except (ValueError, TypeError):
                    int_val = None

                if int_val is not None and (q_id, int_val) in label_map:
                    resolved.append(label_map[(q_id, int_val)])
                elif (q_id, val) in label_map:
                    resolved.append(label_map[(q_id, val)])
                elif (q_id, str(val)) in label_map:
                    resolved.append(label_map[(q_id, str(val))])
                else:
                    resolved.append(str(val))

        if (
            ans.question
            and ans.question.type == "cascade"
            and len(resolved) >= 3
        ):
            ans._resolved_value = resolved[-1]
        else:
            # Surface free-text "allow other" value stored in ans.name.
            # When a respondent picks "Other" and types a custom answer,
            # kobo.py stores the selected token in options and the typed
            # text in Answer.name.  Replace the bare "other"/"others"
            # token with the labelled free-text so the display reads
            # e.g. "Papyrus, Other: spring fed pond".
            if ans.name:
                resolved = [
                    (
                        f"Other: {ans.name}"
                        if r.lower()
                        in ("other", "others", "_other", "_others")
                        else r
                    )
                    for r in resolved
                ]
            ans._resolved_value = ", ".join(resolved)


def resolve_datapoint_brief_attributes(
    datapoint: Datapoint, db: Session, brief: bool = False
):
    """
    Resolves top-level image_url, incident_type_name, incident_type_id, and
    reported_location attributes from answers for a datapoint.
    """
    from app.models.form import Question, Option
    from app.models.spatial import SpatialBoundary
    from app.models.submission import Answer
    from app.services.storage import StorageService
    import uuid
    from sqlalchemy import or_

    image_url = None
    incident_type_name = None
    incident_type_id = None
    reported_location = None

    if brief:
        # Resolve image
        img_ans = (
            db.query(Answer)
            .filter(
                Answer.datapoint_id == datapoint.id,
                or_(
                    Answer.name.ilike("%.jpg"),
                    Answer.name.ilike("%.jpeg"),
                    Answer.name.ilike("%.png"),
                    Answer.name.ilike("%.webp"),
                    Answer.name.ilike("%.gif"),
                    Answer.name.ilike("%.mp4"),
                    Answer.name.ilike("media/%"),
                    Answer.name.ilike("webforms/%"),
                ),
            )
            .first()
        )
        if img_ans:
            try:
                image_url = StorageService().generate_read_signed_url(
                    img_ans.name
                )
            except Exception:
                image_url = img_ans.name

        # Resolve incident type dynamically by matching question name
        type_ans = (
            db.query(Answer)
            .join(Question, Answer.question_id == Question.id)
            .filter(
                Answer.datapoint_id == datapoint.id,
                Question.name == "incident_type",
            )
            .first()
        )
        if type_ans and type_ans.options:
            incident_type_id = type_ans.options[0]
            try:
                opt_val_int = int(type_ans.options[0])
            except (ValueError, TypeError):
                opt_val_int = -9999

            opt = (
                db.query(Option)
                .filter(
                    Option.question_id == type_ans.question_id,
                    or_(
                        Option.id == opt_val_int,
                        Option.value == str(type_ans.options[0]),
                    ),
                )
                .first()
            )
            if opt:
                incident_type_name = opt.label

        # Resolve reported location
        loc_ans = (
            db.query(Answer)
            .join(Question, Answer.question_id == Question.id)
            .filter(
                Answer.datapoint_id == datapoint.id,
                Question.name == "location_id",
            )
            .first()
        )
        if loc_ans:
            if loc_ans.options:
                loc_val = loc_ans.options[0]
                # Check if UUID
                try:
                    uuid.UUID(str(loc_val))
                    is_uuid = True
                except (ValueError, TypeError):
                    is_uuid = False

                if is_uuid:
                    sb = (
                        db.query(SpatialBoundary)
                        .filter(SpatialBoundary.id == loc_val)
                        .first()
                    )
                    if sb:
                        reported_location = sb.name
                else:
                    reported_location = str(loc_val)
            else:
                reported_location = loc_ans.name
    else:
        for ans in datapoint.answers:
            if ans.read_url:
                image_url = ans.read_url
            if (
                ans.question and ans.question.name == "incident_type"
            ) or ans.name == "incident_type":
                incident_type_name = (
                    getattr(ans, "_resolved_value", None) or ans.value
                )
                if ans.options:
                    incident_type_id = ans.options[0]
            if (
                ans.question and ans.question.name == "location_id"
            ) or ans.name == "location_id":
                reported_location = getattr(ans, "_resolved_value", None)
                if not reported_location:
                    if ans.options:
                        loc_val = ans.options[0]
                        try:
                            uuid.UUID(str(loc_val))
                            is_uuid = True
                        except (ValueError, TypeError):
                            is_uuid = False

                        if is_uuid:
                            sb = (
                                db.query(SpatialBoundary)
                                .filter(SpatialBoundary.id == loc_val)
                                .first()
                            )
                            if sb:
                                reported_location = sb.name
                        else:
                            reported_location = str(loc_val)
                    else:
                        reported_location = ans.name or ans.value

    return image_url, incident_type_name, incident_type_id, reported_location
