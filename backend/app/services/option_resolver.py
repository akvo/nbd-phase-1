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
                        if r.lower() in ("other", "others")
                        else r
                    )
                    for r in resolved
                ]
            ans._resolved_value = ", ".join(resolved)
