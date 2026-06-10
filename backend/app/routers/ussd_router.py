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

    # Step 0: Language Selection Menu
    if depth == 0:
        response_text = (
            "CON Choose Language / Chagua Lugha:\n"
            "1. English\n"
            "2. Kiswahili"
        )
        return PlainTextResponse(clean_ussd_response(response_text))

    # Parse language choice
    lang_choice = parts[0]
    if lang_choice == "2":
        lang = "sw"
    else:
        lang = "en"

    # Step 1: Consent Gate (translated)
    if depth == 1:
        if lang == "sw":
            response_text = (
                "CON Karibu kwenye NBD Wetland Watch. Jukwaa hili linakusanya "
                "taarifa za matukio ya mazingira. Ripoti yako inahifadhiwa "
                "bila jina. Matumizi ya data yamezuiliwa kwa mipango ya ufuatiliaji.\n"
                "Bonyeza 1 kukubali na kuanza kuripoti.\n"
                "Bonyeza 2 kukataa masharti."
            )
        else:
            response_text = (
                "CON Welcome to NBD Wetland Watch. This platform collects "
                "environmental incident reports. Your report is saved "
                "anonymously. Data usage is restricted to monitoring programs.\n"
                "Press 1 to accept and start reporting.\n"
                "Press 2 to decline terms."
            )
        return PlainTextResponse(clean_ussd_response(response_text))

    # Parse consent choice
    consent = parts[1]
    if consent != "1":
        if lang == "sw":
            response_text = "END Masharti ya data lazima yakubalike ili kuripoti. Kikao kimefungwa."
        else:
            response_text = (
                "END Data terms must be accepted to report. Session closed."
            )
        processed_sessions[sessionId] = response_text
        return PlainTextResponse(clean_ussd_response(response_text))

    from app.services.translation import get_translation

    # Step 2: Incident Selection
    if depth == 2:
        if not options:
            if lang == "sw":
                response_text = (
                    "END Hitilafu ya mfumo wa ndani. Chaguzi hazijaundwa."
                )
            else:
                response_text = (
                    "END Internal system error. Form options not configured."
                )
            processed_sessions[sessionId] = response_text
            return PlainTextResponse(clean_ussd_response(response_text))

        menu_items = [
            f"{idx}: {get_translation(opt.translations, lang, opt.label)}"
            for idx, opt in enumerate(options, 1)
        ]
        if lang == "sw":
            response_text = "CON Ripoti mabadiliko katika:\n" + "\n".join(
                menu_items
            )
        else:
            response_text = "CON Report a change in:\n" + "\n".join(menu_items)
        return PlainTextResponse(clean_ussd_response(response_text))

    # Step 3: Location Selection (dynamic list based on country networkCode)
    incident_type = parts[2]
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

    # Fetch Level 2 (Districts) sorted by basin and name
    subcounties = (
        db.query(SpatialBoundary)
        .join(Basin)
        .filter(Basin.code.in_(basins), SpatialBoundary.level == 2)
        .order_by(SpatialBoundary.basin_id, SpatialBoundary.name)
        .all()
    )

    menu_lines = []
    current_parent_id = None
    for idx, sc in enumerate(subcounties, 1):
        if sc.parent_id != current_parent_id:
            current_parent_id = sc.parent_id
            parent = sc.parent
            if parent:
                if menu_lines:
                    menu_lines.append("")
                if lang == "sw":
                    menu_lines.append(f"{parent.name} (Mkoa):")
                else:
                    menu_lines.append(f"{parent.name} (Region):")
        menu_lines.append(f"  {idx}. {sc.name}")

    if depth == 3:
        if lang == "sw":
            response_text = "CON Chagua Mahali:\n" + "\n".join(menu_lines)
        else:
            response_text = "CON Choose Location:\n" + "\n".join(menu_lines)
        return PlainTextResponse(clean_ussd_response(response_text))

    # Step 4: Terminal processing and saving
    location_index_str = parts[3]
    try:
        location_idx = int(location_index_str) - 1
        if location_idx < 0 or location_idx >= len(subcounties):
            raise ValueError()
    except ValueError:
        if lang == "sw":
            response_text = (
                "END Uteuzi wa mahali sio sahihi. Kikao kimefungwa."
            )
        else:
            response_text = "END Invalid location selection. Session closed."
        processed_sessions[sessionId] = response_text
        return PlainTextResponse(clean_ussd_response(response_text))

    selected_sc = subcounties[location_idx]

    # Geocode and save report
    if not form:
        if lang == "sw":
            response_text = "END Hitilafu ya mfumo wa ndani. Fomu haijaundwa."
        else:
            response_text = "END Internal system error. Form not configured."
        processed_sessions[sessionId] = response_text
        return PlainTextResponse(clean_ussd_response(response_text))

    # Validate incident selection
    try:
        incident_idx = int(incident_type) - 1
        if incident_idx < 0 or incident_idx >= len(options):
            raise ValueError()
        selected_option = options[incident_idx]
    except (ValueError, IndexError):
        if lang == "sw":
            response_text = "END Uteuzi wa tukio sio sahihi. Kikao kimefungwa."
        else:
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
        options=[
            get_translation(
                selected_option.translations, lang, selected_option.label
            )
        ],
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

    if lang == "sw":
        response_text = "END Asante kwa ripoti yako. NBD Wetland Watch imepokea taarifa yako."
    else:
        response_text = (
            "END Thank you for your report. NBD Wetland Watch has "
            "received your update."
        )
    processed_sessions[sessionId] = response_text
    return PlainTextResponse(clean_ussd_response(response_text))
