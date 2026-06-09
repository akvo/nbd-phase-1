import re
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Form as FastAPIForm
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.spatial import SpatialBoundary, Basin, Site
from app.models.form import Form, Question, Option, FormNames
from app.models.submission import Datapoint, Answer
from app.models.citizen import Citizen

router = APIRouter(prefix="/api/v1/ussd", tags=["ussd"])

# In-memory cache for sessionId idempotency
processed_sessions = {}


def clean_ussd_response(text: str) -> str:
    """Filter to only permit characters matching [A-Za-z0-9\\s?.,:;*#]"""
    return re.sub(r"[^A-Za-z0-9\s?.,:;*#]", "", text)


@router.post("", response_class=PlainTextResponse)
def handle_ussd(
    sessionId: str = FastAPIForm(...),
    phoneNumber: str = FastAPIForm(...),
    networkCode: str = FastAPIForm(...),
    serviceCode: str = FastAPIForm(...),
    text: Optional[str] = FastAPIForm(""),
    db: Session = Depends(get_db),
):
    # Idempotency check
    if sessionId in processed_sessions:
        return PlainTextResponse(processed_sessions[sessionId])

    # Determine state/depth
    # text is concatenated inputs delimited by *
    input_str = text.strip() if text else ""
    if not input_str:
        parts = []
        depth = 0
    else:
        parts = input_str.split("*")
        depth = len(parts)

    # Fetch form and incident_type options dynamically
    form = (
        db.query(Form)
        .filter(Form.name == FormNames.POLLUTION_REPORTING)
        .first()
    )
    options = []
    q_incident = None
    if form:
        q_incident = (
            db.query(Question)
            .filter(
                Question.form_id == form.id, Question.name == "incident_type"
            )
            .first()
        )
        if q_incident:
            options = (
                db.query(Option)
                .filter(Option.question_id == q_incident.id)
                .order_by(Option.order.asc())
                .all()
            )

    # Step 0: Consent Gate
    if depth == 0:
        response_text = (
            "CON Welcome to NBD Wetland Watch. This platform collects "
            "environmental incident reports. Your report is saved "
            "anonymously. Data usage is restricted to monitoring programs.\n"
            "Press 1 to accept and start reporting.\n"
            "Press 2 to decline terms."
        )
        return PlainTextResponse(clean_ussd_response(response_text))

    # Parse consent choice
    consent = parts[0]
    if consent != "1":
        response_text = (
            "END Data terms must be accepted to report. Session closed."
        )
        processed_sessions[sessionId] = response_text
        return PlainTextResponse(clean_ussd_response(response_text))

    # Step 1: Incident Selection
    if depth == 1:
        if not options:
            response_text = (
                "END Internal system error. Form options not configured."
            )
            processed_sessions[sessionId] = response_text
            return PlainTextResponse(clean_ussd_response(response_text))
        menu_items = [
            f"{idx}: {opt.label}" for idx, opt in enumerate(options, 1)
        ]
        response_text = "CON Report a change in:\n" + "\n".join(menu_items)
        return PlainTextResponse(clean_ussd_response(response_text))

    # Step 2: Location Selection (dynamic list based on country networkCode)
    incident_type = parts[1]
    # Map network code to participating basins
    # Kenya: 63902, 63903 (Mara & Sio-Siteko)
    # Uganda: 64101, 64110 (Sio-Siteko)
    # Tanzania: 64002, 64004, 64005 (Mara)
    basins = []
    if networkCode in ("63902", "63903"):
        basins = ["MARA", "SIO_SITEKO"]
    elif networkCode in ("64101", "64110"):
        basins = ["SIO_SITEKO"]
    elif networkCode in ("64002", "64004", "64005"):
        basins = ["MARA"]
    else:
        # Default fallback
        basins = ["MARA", "SIO_SITEKO"]

    # Fetch sub-counties sorted alphabetically
    subcounties = (
        db.query(SpatialBoundary)
        .join(Basin)
        .filter(Basin.code.in_(basins))
        .order_by(SpatialBoundary.name)
        .all()
    )

    if depth == 2:
        menu_items = []
        for idx, sc in enumerate(subcounties, 1):
            menu_items.append(f"{idx}: {sc.name}")
        response_text = "CON Choose Location:\n" + "\n".join(menu_items)
        return PlainTextResponse(clean_ussd_response(response_text))

    # Step 3: Terminal processing and saving
    location_index_str = parts[2]
    try:
        location_idx = int(location_index_str) - 1
        if location_idx < 0 or location_idx >= len(subcounties):
            raise ValueError()
    except ValueError:
        response_text = "END Invalid location selection. Session closed."
        processed_sessions[sessionId] = response_text
        return PlainTextResponse(clean_ussd_response(response_text))

    selected_sc = subcounties[location_idx]

    # Geocode and save report
    if not form:
        response_text = "END Internal system error. Form not configured."
        processed_sessions[sessionId] = response_text
        return PlainTextResponse(clean_ussd_response(response_text))

    # Validate incident selection
    try:
        incident_idx = int(incident_type) - 1
        if incident_idx < 0 or incident_idx >= len(options):
            raise ValueError()
        selected_option = options[incident_idx]
        incident_val = (
            float(selected_option.value) if selected_option.value else 0.0
        )
    except (ValueError, IndexError):
        response_text = "END Invalid incident selection. Session closed."
        processed_sessions[sessionId] = response_text
        return PlainTextResponse(clean_ussd_response(response_text))

    # Find location_id question
    q_location = (
        db.query(Question)
        .filter(Question.form_id == form.id, Question.name == "location_id")
        .first()
    )

    # Check if phoneNumber belongs to a registered citizen
    citizen = (
        db.query(Citizen).filter(Citizen.phone_number == phoneNumber).first()
    )

    # Create Datapoint
    dp = Datapoint(
        uuid=uuid.uuid4(),
        form_id=form.id,
        published_version_id=form.active_version_id,
        submitter="USSD",
        status="PENDING",
        name=sessionId,  # Store sessionId for reference
    )

    from geoalchemy2.shape import to_shape

    if citizen:
        site = db.query(Site).filter(Site.id == citizen.site_id).first()
        if site:
            dp.site_id = citizen.site_id
            point = to_shape(site.geom)
            dp.geo = {"type": "Point", "coordinates": [point.x, point.y]}
        else:
            # Fallback if site not found in database
            dp.basin_id = selected_sc.basin_id
            centroid_geom = selected_sc.centroid_geom
            point = to_shape(centroid_geom)
            dp.geo = {"type": "Point", "coordinates": [point.x, point.y]}
    else:
        # Fallback to selected sub-county centroid
        dp.basin_id = selected_sc.basin_id
        centroid_geom = selected_sc.centroid_geom
        point = to_shape(centroid_geom)
        dp.geo = {"type": "Point", "coordinates": [point.x, point.y]}

    db.add(dp)
    db.flush()

    # Create answers
    ans_incident = Answer(
        datapoint_id=dp.id,
        question_id=q_incident.id if q_incident else 0,
        name=None,
        options=[selected_option.label],
    )
    db.add(ans_incident)

    ans_location = Answer(
        datapoint_id=dp.id,
        question_id=q_location.id if q_location else 0,
        name=None,
        options=[selected_sc.name],
    )
    db.add(ans_location)
    db.commit()

    response_text = (
        "END Thank you for your report. NBD Wetland Watch has "
        "received your update."
    )
    processed_sessions[sessionId] = response_text
    return PlainTextResponse(clean_ussd_response(response_text))
