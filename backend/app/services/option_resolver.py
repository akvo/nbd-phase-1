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
    all_option_ids = []
    all_boundary_ids = []
    answers_to_resolve = []

    for dp in datapoints:
        for ans in dp.answers:
            if ans.options and isinstance(ans.options, list):
                if ans.question and ans.question.type in (
                    "option",
                    "multiple_option",
                    "cascade",
                ):
                    answers_to_resolve.append(ans)
                    for opt_val in ans.options:
                        if is_valid_uuid(opt_val):
                            all_boundary_ids.append(opt_val)
                        else:
                            try:
                                all_option_ids.append(int(opt_val))
                            except (ValueError, TypeError):
                                all_option_ids.append(opt_val)

    if not all_option_ids and not all_boundary_ids:
        return

    label_map = {}

    # Query Options
    if all_option_ids:
        int_ids = [x for x in all_option_ids if isinstance(x, int)]
        str_vals = [str(x) for x in all_option_ids]

        options = (
            db.query(Option)
            .filter((Option.id.in_(int_ids)) | (Option.value.in_(str_vals)))
            .all()
        )
        for opt in options:
            label_map[opt.id] = opt.label
            if opt.value:
                label_map[opt.value] = opt.label

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
        for val in ans.options:
            try:
                int_val = int(val)
            except (ValueError, TypeError):
                int_val = None

            if int_val is not None and int_val in label_map:
                resolved.append(label_map[int_val])
            elif val in label_map:
                resolved.append(label_map[val])
            elif str(val) in label_map:
                resolved.append(label_map[str(val)])
            else:
                resolved.append(str(val))
        ans._resolved_value = ", ".join(resolved)
