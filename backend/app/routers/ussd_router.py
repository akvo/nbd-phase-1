import re
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Form as FastAPIForm
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.spatial import SpatialBoundary, Basin
from app.models.form import (
    Form,
    Question,
    QuestionGroup,
    Option,
    FormNames,
    QuestionType,
)
from app.models.submission import Datapoint, Answer
from app.models.citizen import Citizen
from app.services.ussd_pager import USSDDynamicPager

router = APIRouter(prefix="/api/v1/ussd", tags=["ussd"])

# In-memory cache for sessionId idempotency
processed_sessions = {}


def build_ussd_summary(
    db: Session, active_questions: list, current_answers: dict, lang: str
) -> str:
    from app.services.translation import get_translation

    lines = []
    q_counter = 1
    for q in active_questions:
        if q.type in ("image", "attachment"):
            continue
        val = current_answers.get(q.id)
        if val is None:
            continue

        q_label = get_translation(q.translations, lang, q.label)
        if q.type == "option":
            opt = (
                db.query(Option)
                .filter(Option.question_id == q.id, Option.value == str(val))
                .first()
            )
            val_label = (
                get_translation(opt.translations, lang, opt.label)
                if opt
                else str(val)
            )
        elif q.type == "cascade":
            sb = (
                db.query(SpatialBoundary)
                .filter(SpatialBoundary.id == str(val))
                .first()
            )
            val_label = sb.name if sb else str(val)
        else:
            val_label = str(val)

        lines.append(f"Q{q_counter}. {q_label}: {val_label}")
        q_counter += 1
    return "\n".join(lines)


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
    from app.models.user import User
    from app.models.audit_log import AuditLog

    status_code = 200
    try:
        response = _handle_ussd_core(
            sessionId=sessionId,
            phoneNumber=phoneNumber,
            networkCode=networkCode,
            serviceCode=serviceCode,
            text=text,
            db=db,
        )
        return response
    except Exception as e:
        status_code = 500
        raise e
    finally:
        try:
            sys_user = User.get_or_create_system_user(db)
            audit = AuditLog(
                actor_id=sys_user.id,
                action="POST",
                entity_type="ussd_webhook",
                entity_id=str(status_code),
            )
            db.add(audit)
            db.commit()
        except Exception:
            db.rollback()


def _handle_ussd_core(
    sessionId: str,
    phoneNumber: str,
    networkCode: str,
    serviceCode: str,
    text: Optional[str],
    db: Session,
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

    # Fetch form configuration snapshot
    form = (
        db.query(Form)
        .filter(Form.name == FormNames.POLLUTION_REPORTING)
        .first()
    )
    if not form:
        return PlainTextResponse(
            clean_ussd_response(
                "END Hitilafu ya mfumo wa ndani. Fomu haijaundwa."
                if depth > 0 and parts[0] == "2"
                else "END Internal system error. Form not configured."
            )
        )

    # Fetch all questions in order of Group Order, then Question Order
    active_questions = (
        db.query(Question)
        .join(QuestionGroup)
        .filter(
            Question.form_id == form.id,
            Question.deleted_at.is_(None),
            QuestionGroup.deleted_at.is_(None),
        )
        .order_by(
            QuestionGroup.order.asc().nullslast(),
            Question.order.asc().nullslast(),
        )
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

    # Step 1: Consent Gate (translated & paginated)
    # The user inputs after language selection (parts[1:]) are parsed to
    # determine if they are on Consent Page 1, Page 2, accepted, or declined.
    consent_page = 1
    consent_accepted = False
    consent_declined = False

    # We will traverse parts[1:] to calculate final state
    processed_count = 0  # Number of items in parts consumed by consent step
    for part in parts[1:]:
        processed_count += 1
        part_clean = part.strip()
        if consent_page == 1:
            if part_clean == "98":
                consent_page = 2
            elif part_clean == "1":
                consent_accepted = True
                break
            elif part_clean == "2":
                consent_declined = True
                break
        elif consent_page == 2:
            if part_clean == "0":
                consent_page = 1
            elif part_clean == "1":
                consent_accepted = True
                break
            elif part_clean == "2":
                consent_declined = True
                break

    # If they haven't explicitly accepted or declined yet, show current page
    if not consent_accepted and not consent_declined:
        if consent_page == 1:
            if lang == "sw":
                response_text = (
                    "CON Karibu NBD Wetland Watch. "
                    "Tunakusanya taarifa za mazingira bila jina.\n"
                    "98. Angalia zaidi\n"
                    "2. Kataa"
                )
            else:
                response_text = (
                    "CON Welcome to NBD Wetland Watch. "
                    "We collect anonymous environmental reports.\n"
                    "98. View More\n"
                    "2. Decline"
                )
        else:  # Page 2
            if lang == "sw":
                response_text = (
                    "CON Data inatumika kwa ufuatiliaji tu. "
                    "Kuendelea ni kukubali masharti.\n"
                    "1. Kubali na kuanza\n"
                    "0. Rudi nyuma"
                )
            else:
                response_text = (
                    "CON Data is used only for monitoring. "
                    "Proceeding means you agree.\n"
                    "1. Accept & Start\n"
                    "0. Back"
                )
        return PlainTextResponse(clean_ussd_response(response_text))

    if consent_declined:
        if lang == "sw":
            response_text = (
                "END Masharti ya data lazima yakubalike ili kuripoti. "
                "Kikao kimefungwa."
            )
        else:
            response_text = (
                "END Data terms must be accepted to report. Session closed."
            )
        processed_sessions[sessionId] = response_text
        return PlainTextResponse(clean_ussd_response(response_text))

    # If consent was accepted:
    # We must rebuild/clean the parts array to remove paging traversal values.
    # Dynamic questions start at index 2, expecting parts[0] = language,
    # parts[1] = accept (1)
    parts = parts[:1] + ["1"] + parts[1 + processed_count :]  # noqa

    from app.services.translation import get_translation
    from app.services.form_engine import is_question_active

    # Determine participating basins from telco code
    basins = []
    if networkCode in ("63902", "63903"):
        basins = ["MARA", "SIO_SITEKO"]
    elif networkCode in ("64101", "64110"):
        basins = ["SIO_SITEKO"]
    elif networkCode in ("64002", "64004", "64005"):
        basins = ["MARA"]
    else:
        basins = ["MARA", "SIO_SITEKO"]

    # Traversal loop to evaluate current question
    while True:
        current_answers = {}
        input_idx = 2
        q_idx = 0
        selected_sc = None

        while q_idx < len(active_questions):
            q = active_questions[q_idx]

            # Check skip logic (dependency)
            if not is_question_active(q, current_answers):
                q_idx += 1
                continue

            # If USSD does not support media, skip the question
            if q.type in ("image", "attachment"):
                q_idx += 1
                continue

            # If user has provided input for this active question
            if input_idx < len(parts):
                user_input = parts[input_idx].strip()

                if q.type == "cascade":
                    # Level 2 (County) selection
                    counties = (
                        db.query(SpatialBoundary)
                        .join(Basin)
                        .filter(
                            Basin.code.in_(basins), SpatialBoundary.level == 2
                        )
                        .order_by(
                            SpatialBoundary.basin_id, SpatialBoundary.name
                        )
                        .all()
                    )

                    pager = USSDDynamicPager(page_size=4)
                    q_label = get_translation(q.translations, lang, q.label)
                    res = pager.render_page(
                        counties,
                        parts[input_idx:],
                        f"{q_label}:",
                        lang=lang,
                        is_cascade=True,
                    )

                    if res["selected"] is not None:
                        selected_county = res["selected"]
                        # Cleanse parts to replace paging path
                        # with the selected option value
                        parts = (
                            parts[:input_idx]
                            + [res["final_value"]]
                            + parts[input_idx + res["consumed"] :]  # noqa
                        )
                    else:
                        return PlainTextResponse(
                            clean_ussd_response(f"CON {res['prompt_text']}")
                        )

                    sub_counties = (
                        db.query(SpatialBoundary)
                        .filter(
                            SpatialBoundary.level == 3,
                            SpatialBoundary.parent_id == selected_county.id,
                        )
                        .order_by(SpatialBoundary.name)
                        .all()
                    )

                    if sub_counties:
                        # Dynamic paging for sub-county selection
                        pager_sc = USSDDynamicPager(page_size=4)
                        sc_inputs = parts[input_idx + 1 :]  # noqa
                        sc_label = (
                            f"Chagua Wilaya ndogo ya {selected_county.name}:"
                            if lang == "sw"
                            else f"Choose Sub-County of {selected_county.name}:"  # noqa
                        )
                        res_sc = pager_sc.render_page(
                            sub_counties,
                            sc_inputs,
                            sc_label,
                            lang=lang,
                            is_cascade=True,
                        )

                        if res_sc["selected"] is not None:
                            selected_sc = res_sc["selected"]
                            current_answers[q.id] = str(selected_sc.id)
                            current_answers[q.name] = str(selected_sc.id)
                            # Cleanse parts for the sub-county pagination
                            parts = (
                                parts[: input_idx + 1]
                                + [res_sc["final_value"]]
                                + parts[
                                    input_idx
                                    + 1
                                    + res_sc["consumed"] :  # noqa
                                ]
                            )
                            input_idx += 2
                        else:
                            return PlainTextResponse(
                                clean_ussd_response(
                                    f"CON {res_sc['prompt_text']}"
                                )
                            )
                    else:
                        selected_sc = selected_county
                        current_answers[q.id] = str(selected_sc.id)
                        current_answers[q.name] = str(selected_sc.id)
                        input_idx += 1

                elif q.type == "option":
                    options = (
                        db.query(Option)
                        .filter(Option.question_id == q.id)
                        .order_by(Option.order.asc())
                        .all()
                    )

                    pager = USSDDynamicPager(page_size=4)
                    q_label = get_translation(q.translations, lang, q.label)
                    res = pager.render_page(
                        options, parts[input_idx:], f"{q_label}:", lang=lang
                    )

                    if res["selected"] is not None:
                        selected_opt = res["selected"]
                        current_answers[q.id] = selected_opt.value
                        current_answers[q.name] = selected_opt.value
                        # Cleanse parts
                        parts = (
                            parts[:input_idx]
                            + [res["final_value"]]
                            + parts[input_idx + res["consumed"] :]  # noqa
                        )
                        input_idx += 1
                    else:
                        return PlainTextResponse(
                            clean_ussd_response(f"CON {res['prompt_text']}")
                        )

                else:
                    current_answers[q.id] = user_input
                    current_answers[q.name] = user_input
                    input_idx += 1

                q_idx += 1

            else:
                # We don't have user input for this question yet,
                # so prompt for it
                if q.type == "cascade":
                    counties = (
                        db.query(SpatialBoundary)
                        .join(Basin)
                        .filter(
                            Basin.code.in_(basins), SpatialBoundary.level == 2
                        )
                        .order_by(
                            SpatialBoundary.basin_id, SpatialBoundary.name
                        )
                        .all()
                    )
                    pager = USSDDynamicPager(page_size=4)
                    q_label = get_translation(q.translations, lang, q.label)
                    res = pager.render_page(
                        counties, [], f"{q_label}:", lang=lang, is_cascade=True
                    )
                    return PlainTextResponse(
                        clean_ussd_response(f"CON {res['prompt_text']}")
                    )

                elif q.type == "option":
                    options = (
                        db.query(Option)
                        .filter(Option.question_id == q.id)
                        .order_by(Option.order.asc())
                        .all()
                    )
                    pager = USSDDynamicPager(page_size=4)
                    q_label = get_translation(q.translations, lang, q.label)
                    res = pager.render_page(
                        options, [], f"{q_label}:", lang=lang
                    )
                    return PlainTextResponse(
                        clean_ussd_response(f"CON {res['prompt_text']}")
                    )

                else:
                    q_label = get_translation(q.translations, lang, q.label)
                    prompt_text = f"CON {q_label}:"
                    return PlainTextResponse(clean_ussd_response(prompt_text))

        # Check confirmation choice
        if input_idx < len(parts):
            confirm_choice = parts[input_idx].strip()
            if confirm_choice == "2":
                # Redo: keep language & consent, restart form loop
                parts = parts[:2] + parts[input_idx + 1 :]  # noqa
                continue
            elif confirm_choice == "1":
                # Confirm: proceed to database save
                break
            else:
                # Invalid choice, drop the invalid input and re-display summary
                parts = parts[:input_idx]
        else:
            # Not confirmed yet: show summary and prompt choices
            summary = build_ussd_summary(
                db, active_questions, current_answers, lang
            )
            if lang == "sw":
                prompt_text = (
                    f"CON Hakikisha maelezo yako:\n{summary}\n\n"
                    f"1. Thibitisha\n"
                    f"2. Anza tena"
                )
            else:
                prompt_text = (
                    f"CON Confirm your details:\n{summary}\n\n"
                    f"1. Confirm\n"
                    f"2. Redo"
                )
            return PlainTextResponse(clean_ussd_response(prompt_text))

    # If we reached here, it means all dynamic questions have been processed!
    # Geocode and save report
    citizen = (
        db.query(Citizen).filter(Citizen.phone_number == phoneNumber).first()
    )

    dp = Datapoint(
        uuid=uuid.uuid4(),
        form_id=form.id,
        published_version_id=form.active_version_id,
        submitter="USSD",
        status="PENDING",
        name=sessionId,
    )

    from geoalchemy2.shape import to_shape

    if citizen:
        from app.models.spatial import Site

        site = db.query(Site).filter(Site.id == citizen.site_id).first()
        if site:
            dp.site_id = citizen.site_id
            point = to_shape(site.geom)
            dp.geo = {"type": "Point", "coordinates": [point.x, point.y]}
        elif selected_sc:
            dp.basin_id = selected_sc.basin_id
            centroid_geom = selected_sc.centroid_geom
            curr_parent = selected_sc.parent
            while not centroid_geom and curr_parent:
                centroid_geom = curr_parent.centroid_geom
                curr_parent = curr_parent.parent

            if centroid_geom:
                point = to_shape(centroid_geom)
                dp.geo = {"type": "Point", "coordinates": [point.x, point.y]}
            else:
                dp.geo = None
    elif selected_sc:
        dp.basin_id = selected_sc.basin_id
        centroid_geom = selected_sc.centroid_geom
        curr_parent = selected_sc.parent
        while not centroid_geom and curr_parent:
            centroid_geom = curr_parent.centroid_geom
            curr_parent = curr_parent.parent

        if centroid_geom:
            point = to_shape(centroid_geom)
            dp.geo = {"type": "Point", "coordinates": [point.x, point.y]}
        else:
            dp.geo = None

    db.add(dp)
    db.flush()

    # Create Answer records for each question
    for q in active_questions:
        ans_val = current_answers.get(q.id)
        if ans_val is not None:
            name = None
            value = None
            option = None

            if q.type in (
                QuestionType.geo,
                QuestionType.option,
                QuestionType.multiple_option,
            ):
                option = [str(ans_val)]
            elif q.type in (
                QuestionType.input,
                QuestionType.text,
                QuestionType.image,
                QuestionType.date,
                QuestionType.autofield,
                QuestionType.attachment,
                QuestionType.signature,
            ):
                name = str(ans_val)
            elif q.type == QuestionType.cascade:
                option = [str(ans_val)]
                boundary = (
                    db.query(SpatialBoundary)
                    .filter(SpatialBoundary.id == ans_val)
                    .first()
                )
                if boundary:
                    name = boundary.name
                else:
                    name = str(ans_val)
            else:
                # Fallback or numeric types
                try:
                    value = float(ans_val)
                except (ValueError, TypeError):
                    name = str(ans_val)

            ans = Answer(
                datapoint_id=dp.id,
                question_id=q.id,
                name=name,
                options=option,
                value=value,
            )
            db.add(ans)

    db.commit()

    if lang == "sw":
        response_text = (
            "END Asante kwa ripoti yako. NBD Wetland Watch imepokea "
            "taarifa yako."
        )
    else:
        response_text = (
            "END Thank you for your report. NBD Wetland Watch has "
            "received your update."
        )
    processed_sessions[sessionId] = response_text
    return PlainTextResponse(clean_ussd_response(response_text))
