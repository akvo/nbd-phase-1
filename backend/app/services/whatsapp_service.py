"""WhatsApp conversation state machine service.

State flow:
    CONSENT -> INCIDENT_SELECT -> MEDIA_UPLOAD -> LOCATION_SELECT -> DONE

Each incoming message is dispatched here after signature verification.
The service manages session state via the whatsapp_sessions table and
persists completed reports as Datapoint/Answer records, mirroring the
USSD router logic.
"""

import uuid  # noqa: F401
import logging
import os
import httpx
from typing import Any, AsyncIterator, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.whatsapp_session import WhatsAppSession
from app.models.form import Form, Question, QuestionGroup, Option, FormNames
from app.models.submission import Datapoint, Answer
from app.models.spatial import SpatialBoundary, Basin
from app.models.citizen import Citizen
from app.services.storage import StorageService, build_blob_path
from app.services.form_engine import is_question_active

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Meta Graph API helpers
# ---------------------------------------------------------------------------

GRAPH_API_VERSION = "v25.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def _get_access_token() -> str:
    token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("WHATSAPP_ACCESS_TOKEN env var is not set")
    return token


async def _send_message(phone: str, text: str) -> None:
    """Send a text message via the WhatsApp Business API."""
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    if not phone_id:
        logger.warning("WHATSAPP_PHONE_NUMBER_ID not set; skipping send")
        return
    url = f"{GRAPH_BASE}/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text},
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_get_access_token()}",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()


async def _get_media_url(media_id: str) -> str:
    """Step 1: resolve a Meta media_id to its short-lived download URL."""
    headers = {"Authorization": f"Bearer {_get_access_token()}"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{GRAPH_BASE}/{media_id}", headers=headers)
        resp.raise_for_status()
        url = resp.json().get("url")
        if not url:
            raise ValueError(f"No URL returned for media_id={media_id}")
        return url


async def _iter_media_chunks(
    media_url: str, chunk_size: int = 1024 * 1024
) -> AsyncIterator[bytes]:
    """Step 2: stream binary chunks from Meta's media URL.

    Uses httpx streaming to avoid loading the full file into RAM.
    WhatsApp caps media at 16 MB so peak memory ≤ 16 MB.
    """
    headers = {"Authorization": f"Bearer {_get_access_token()}"}
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("GET", media_url, headers=headers) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(chunk_size):
                yield chunk


# ---------------------------------------------------------------------------
# Payload parsing helpers
# ---------------------------------------------------------------------------


def _extract_message(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the first message dict from a Meta webhook payload, or None."""
    try:
        return payload["entry"][0]["changes"][0]["value"]["messages"][0]
    except (KeyError, IndexError):
        return None


def _sender_phone(payload: Dict[str, Any]) -> Optional[str]:
    try:
        return payload["entry"][0]["changes"][0]["value"]["messages"][0][
            "from"
        ]
    except (KeyError, IndexError):
        return None


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _get_or_create_session(db: Session, phone: str) -> WhatsAppSession:
    session = (
        db.query(WhatsAppSession)
        .filter(WhatsAppSession.phone_number == phone)
        .first()
    )
    if not session:
        session = WhatsAppSession(phone_number=phone, state="CONSENT")
        db.add(session)
        db.flush()
    return session


def _fetch_subcounties(db: Session) -> List[SpatialBoundary]:
    return (
        db.query(SpatialBoundary)
        .join(Basin)
        .filter(SpatialBoundary.level == 2)
        .order_by(SpatialBoundary.basin_id, SpatialBoundary.name)
        .all()
    )


def _format_location_menu(
    subcounties: List[SpatialBoundary], lang: str
) -> str:
    menu_lines = []
    current_parent_id = None
    for i, sc in enumerate(subcounties, 1):
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
        menu_lines.append(f"  {i}: {sc.name}")
    return "\n".join(menu_lines)


def _get_next_active_question(
    questions: List[Question],
    answers: Dict[str, Any],
    current_q_id: Optional[int],
) -> Optional[Question]:
    """
    Find the next question in list that is active, starting after current_q_id.
    """
    start_checking = False if current_q_id else True
    for q in questions:
        if not start_checking:
            if q.id == current_q_id:
                start_checking = True
            continue
        # Skip image/attachment type
        # if it's not WhatsApp but here it is WhatsApp so it is fine
        if is_question_active(q, answers):
            return q
    return None


def _save_report(
    db: Session,
    phone: str,
    session: WhatsAppSession,
    answers: Dict[str, Any],
    active_questions: List[Question],
) -> None:
    """Persist a completed WhatsApp report as a Datapoint + Answers."""
    from geoalchemy2.shape import to_shape

    form = (
        db.query(Form)
        .filter(Form.name == FormNames.POLLUTION_REPORTING)
        .first()
    )
    if not form:
        logger.error("Pollution reporting form not found; aborting save.")
        return

    q_location = (
        db.query(Question)
        .filter(Question.form_id == form.id, Question.name == "location_id")
        .first()
    )

    selected_sc = None
    if q_location and str(q_location.id) in answers:
        loc_val = answers[str(q_location.id)]
        selected_sc = (
            db.query(SpatialBoundary)
            .filter(SpatialBoundary.id == loc_val)
            .first()
        )

    citizen = db.query(Citizen).filter(Citizen.phone_number == phone).first()

    dp = Datapoint(
        uuid=uuid.uuid4(),
        form_id=form.id,
        published_version_id=form.active_version_id,
        submitter="WHATSAPP",
        status="PENDING",
        name=f"wa-{phone}",
    )

    if citizen:
        from app.models.spatial import Site

        site = db.query(Site).filter(Site.id == citizen.site_id).first()
        if site:
            dp.site_id = citizen.site_id
            pt = to_shape(site.geom)
            dp.geo = {"type": "Point", "coordinates": [pt.x, pt.y]}
        elif selected_sc:
            dp.basin_id = selected_sc.basin_id
            centroid_geom = selected_sc.centroid_geom
            curr_parent = selected_sc.parent
            while not centroid_geom and curr_parent:
                centroid_geom = curr_parent.centroid_geom
                curr_parent = curr_parent.parent

            if centroid_geom:
                pt = to_shape(centroid_geom)
                dp.geo = {"type": "Point", "coordinates": [pt.x, pt.y]}
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
            pt = to_shape(centroid_geom)
            dp.geo = {"type": "Point", "coordinates": [pt.x, pt.y]}
        else:
            dp.geo = None

    db.add(dp)
    db.flush()

    # Save answers dynamically
    for q in active_questions:
        ans_val = answers.get(str(q.id))
        if ans_val is not None and ans_val not in ("UPLOAD_FAILED", "SKIPPED"):
            # If it's a list, save it as a list, else wrap in a list
            ans_opts = ans_val if isinstance(ans_val, list) else [str(ans_val)]
            ans = Answer(
                datapoint_id=dp.id,
                question_id=q.id,
                name=None,
                options=ans_opts,
                index=1 if q.type in ("image", "attachment") else None,
            )
            db.add(ans)

    db.commit()


def _build_whatsapp_summary(
    db: Session,
    active_questions: List[Question],
    answers: Dict[str, Any],
    lang: str,
) -> str:
    from app.services.translation import get_translation

    lines = []
    for q in active_questions:
        val = answers.get(str(q.id))
        if val is None:
            continue
        q_label = get_translation(q.translations, lang, q.label)
        if q.type in ("image", "attachment"):
            val_label = "Media Uploaded" if lang == "en" else "Picha Imepakiwa"
            if val == "UPLOAD_FAILED":
                val_label = "Failed" if lang == "en" else "Haikufaulu"
            elif val == "SKIPPED":
                val_label = "Skipped" if lang == "en" else "Imerukwa"
        elif q.type == "option":
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

        lines.append(f"• *{q_label}*: {val_label}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


async def process_whatsapp_message(payload: Dict[str, Any]) -> None:
    """Route an inbound Meta webhook payload through the state machine."""
    msg = _extract_message(payload)
    phone = _sender_phone(payload)
    if not msg or not phone:
        logger.warning("Skipping webhook: no message or phone found.")
        return

    msg_type = msg.get("type")

    db: Session = SessionLocal()
    try:
        session = _get_or_create_session(db, phone)
        state = session.state

        # Fetch form configuration snapshot
        form = (
            db.query(Form)
            .filter(Form.name == FormNames.POLLUTION_REPORTING)
            .first()
        )
        if not form:
            logger.error("Pollution reporting form not found; aborting.")
            return

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

        from app.services.translation import get_translation

        # Initialize session answers dict
        session_answers = session.answers or {}

        # ------------------------------------------------------------------
        # STATE: CONSENT
        # ------------------------------------------------------------------
        if state == "CONSENT":
            text_body = (msg.get("text") or {}).get("body", "").strip()
            welcome_msg = (
                "Welcome to NBD Wetland Watch \U0001f30a / "
                "Chagua lugha yako:\n\n"
                "Reply *1* for English\n"
                "Reply *2* kwa Kiswahili"
            )
            if not text_body:
                await _send_message(phone, welcome_msg)
                return
            if text_body in ("1", "2"):
                # Save language preference
                session.language = "sw" if text_body == "2" else "en"
                session.state = "DATA_TERMS"
                db.commit()

                if session.language == "sw":
                    terms_msg = (
                        "Karibu kwenye NBD Wetland Watch \U0001f30a\n\n"
                        "Jukwaa hili linakusanya taarifa za matukio "
                        "ya mazingira. "
                        "Ripoti yako inahifadhiwa bila jina na matumizi "
                        "ya data yamezuiliwa kwa mipango ya ufuatiliaji.\n\n"
                        "Jibu *1* kukubali masharti na kuanza kuripoti.\n"
                        "Jibu *2* kukataa."
                    )
                else:
                    terms_msg = (
                        "Welcome to NBD Wetland Watch \U0001f30a\n\n"
                        "This platform collects environmental incident "
                        "reports. Your report is saved anonymously and "
                        "data usage is restricted to monitoring programs.\n\n"
                        "Reply *1* to accept terms and start reporting.\n"
                        "Reply *2* to decline."
                    )
                await _send_message(phone, terms_msg)
            else:
                await _send_message(phone, welcome_msg)
            return

        # ------------------------------------------------------------------
        # STATE: DATA_TERMS
        # ------------------------------------------------------------------
        if state == "DATA_TERMS":
            text_body = (msg.get("text") or {}).get("body", "").strip()
            lang = session.language
            if text_body == "1":
                # Accepted — move to dynamic questions
                session_answers = {}
                session.answers = session_answers

                # Find first active question
                first_q = _get_next_active_question(
                    active_questions, session_answers, None
                )
                if not first_q:
                    if lang == "sw":
                        thank_msg = "\u2705 Asante! Ripoti yako imepokelewa na NBD Wetland Watch."  # noqa
                    else:
                        thank_msg = "\u2705 Thank you! Your report has been received by NBD Wetland Watch."  # noqa
                    await _send_message(phone, thank_msg)
                    db.delete(session)
                    db.commit()
                    return

                session.current_question_id = first_q.id
                session.state = "DYNAMIC_QUESTION"
                db.commit()

                # Prompt first question
                await _prompt_question(phone, first_q, lang, db)
            elif text_body == "2":
                if lang == "sw":
                    decline_msg = "Ni lazima ukubali masharti ya data ili kuwasilisha ripoti. Tuma ujumbe wowote ili kuanza tena."  # noqa: E501
                else:
                    decline_msg = (
                        "You must accept the data terms to submit a report. "
                        "Send any message to start again."
                    )
                await _send_message(phone, decline_msg)
                db.delete(session)
                db.commit()
            else:
                if lang == "sw":
                    terms_msg = (
                        "Karibu kwenye NBD Wetland Watch \U0001f30a\n\n"
                        "Jukwaa hili linakusanya taarifa za matukio ya mazingira. "  # noqa: E501
                        "Ripoti yako inahifadhiwa bila jina na matumizi ya data yamezuiliwa "  # noqa: E501
                        "kwa mipango ya ufuatiliaji.\n\n"
                        "Jibu *1* kukubali masharti na kuanza kuripoti.\n"
                        "Jibu *2* kukataa."
                    )
                else:
                    terms_msg = (
                        "Welcome to NBD Wetland Watch \U0001f30a\n\n"
                        "This platform collects environmental incident "
                        "reports. Your report is saved anonymously and "
                        "data usage is restricted to monitoring programs.\n\n"
                        "Reply *1* to accept terms and start reporting.\n"
                        "Reply *2* to decline."
                    )
                await _send_message(phone, terms_msg)
            return

        # ------------------------------------------------------------------
        # STATE: DYNAMIC_QUESTION
        # ------------------------------------------------------------------
        if state == "DYNAMIC_QUESTION":
            lang = session.language
            curr_q = (
                db.query(Question)
                .filter(Question.id == session.current_question_id)
                .first()
            )
            if not curr_q:
                logger.error(
                    "Current question ID %s not found in database",
                    session.current_question_id,
                )
                db.delete(session)
                db.commit()
                return

            valid = False
            parsed_val = None

            if curr_q.type == "cascade":
                # Multi-level location cascade: Region -> County -> Sub-county
                counties = _fetch_subcounties(db)
                if not session.location:
                    # Parse County choice
                    text_body = (msg.get("text") or {}).get("body", "").strip()
                    try:
                        idx = int(text_body) - 1
                        if idx < 0 or idx >= len(counties):
                            raise ValueError()
                        selected_county = counties[idx]
                        valid = True
                    except (ValueError, TypeError):
                        menu = _format_location_menu(counties, lang)
                        prompt = (
                            f"Tafadhali jibu kwa nambari sahihi.\n\n{menu}"
                            if lang == "sw"
                            else f"Please reply with a valid number.\n\n{menu}"
                        )
                        await _send_message(phone, prompt)
                        return

                    # Check if there are level 3 sub-counties
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
                        session.location = str(selected_county.id)
                        db.commit()
                        menu_lines = [
                            f"  {i}: {sc.name}"
                            for i, sc in enumerate(sub_counties, 1)
                        ]
                        menu = "\n".join(menu_lines)
                        prompt = (
                            f"Chagua wilaya ndogo ya {selected_county.name}:\n\n{menu}"  # noqa
                            if lang == "sw"
                            else f"Choose sub-county of {selected_county.name}:\n\n{menu}"  # noqa
                        )
                        await _send_message(phone, prompt)
                        return
                    else:
                        # No sub-counties, county is final
                        parsed_val = str(selected_county.id)
                else:
                    # Parse Sub-county choice
                    text_body = (msg.get("text") or {}).get("body", "").strip()
                    county_id = session.location
                    selected_county = (
                        db.query(SpatialBoundary)
                        .filter(SpatialBoundary.id == county_id)
                        .first()
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
                    try:
                        idx = int(text_body) - 1
                        if idx < 0 or idx >= len(sub_counties):
                            raise ValueError()
                        selected_sc = sub_counties[idx]
                        parsed_val = str(selected_sc.id)
                        valid = True
                    except (ValueError, TypeError):
                        menu_lines = [
                            f"  {i}: {sc.name}"
                            for i, sc in enumerate(sub_counties, 1)
                        ]
                        menu = "\n".join(menu_lines)
                        prompt = (
                            f"Tafadhali jibu kwa nambari sahihi.\n\nChagua wilaya ndogo ya {selected_county.name}:\n\n{menu}"  # noqa
                            if lang == "sw"
                            else f"Please reply with a valid number.\n\nChoose sub-county of {selected_county.name}:\n\n{menu}"  # noqa
                        )
                        await _send_message(phone, prompt)
                        return

            elif curr_q.type == "option":
                text_body = (msg.get("text") or {}).get("body", "").strip()
                options = (
                    db.query(Option)
                    .filter(Option.question_id == curr_q.id)
                    .order_by(Option.order.asc())
                    .all()
                )
                try:
                    idx = int(text_body) - 1
                    if idx < 0 or idx >= len(options):
                        raise ValueError()
                    selected_opt = options[idx]
                    parsed_val = selected_opt.value
                    valid = True
                except (ValueError, TypeError):
                    menu = "\n".join(
                        f"{i}: {get_translation(o.translations, lang, o.label)}"  # noqa
                        for i, o in enumerate(options, 1)
                    )
                    prompt = (
                        f"Tafadhali jibu kwa nambari sahihi.\n\n{menu}"
                        if lang == "sw"
                        else f"Please reply with a valid number.\n\n{menu}"
                    )
                    await _send_message(phone, prompt)
                    return

            elif curr_q.type in ("image", "attachment"):
                if msg_type in ("image", "video", "document"):
                    media_id = (msg.get(msg_type) or {}).get("id")
                    mime_type = (msg.get(msg_type) or {}).get(
                        "mime_type", "application/octet-stream"
                    )
                    if media_id:
                        ext = mime_type.split("/")[-1].split(";")[0]
                        blob_name = build_blob_path("whatsapp", ext)
                        try:
                            media_url = await _get_media_url(media_id)
                            storage = StorageService()
                            await storage.stream_upload_async(
                                blob_name=blob_name,
                                chunks=_iter_media_chunks(media_url),
                                content_type=mime_type,
                            )
                            parsed_val = blob_name
                            valid = True
                        except Exception as exc:
                            logger.error(
                                "Media upload failed for %s (blob=%s): %s",
                                phone,
                                blob_name,
                                exc,
                                exc_info=True,
                            )
                            parsed_val = "UPLOAD_FAILED"
                            valid = True
                elif msg_type == "text":
                    skip_text = (msg.get("text") or {}).get("body", "").strip()
                    if skip_text.lower() == "skip":
                        parsed_val = "SKIPPED"
                        valid = True
                    else:
                        prompt = (
                            "Tafadhali tuma picha/video au jibu *skip*."
                            if lang == "sw"
                            else "Please send a photo/video or reply *skip*."
                        )
                        await _send_message(phone, prompt)
                        return

            else:
                # Text/number or fallback input types
                text_body = (msg.get("text") or {}).get("body", "").strip()
                if text_body:
                    parsed_val = text_body
                    valid = True

            if valid:
                # Save answer in session answers
                session_answers[str(curr_q.id)] = parsed_val
                session.answers = session_answers
                from sqlalchemy.orm.attributes import flag_modified

                flag_modified(session, "answers")
                session.location = None  # Reset temporary cascade state
                db.commit()

                # Get next active question
                next_q = _get_next_active_question(
                    active_questions, session_answers, curr_q.id
                )
                if next_q:
                    session.current_question_id = next_q.id
                    db.commit()
                    await _prompt_question(phone, next_q, lang, db)
                else:
                    # All completed!
                    # Set state to CONFIRMATION and prompt review
                    session.state = "CONFIRMATION"
                    db.commit()

                    summary = _build_whatsapp_summary(
                        db, active_questions, session_answers, lang
                    )
                    if lang == "sw":
                        confirm_msg = (
                            "Tafadhali hakikisha maelezo ya ripoti yako:\n"
                            f"{summary}\n\n"
                            "Jibu *1* kuthibitisha\n"
                            "Jibu *2* kuanza tena"
                        )
                    else:
                        confirm_msg = (
                            "Please review your report details:\n"
                            f"{summary}\n\n"
                            "Reply *1* to Confirm\n"
                            "Reply *2* to Redo"
                        )
                    await _send_message(phone, confirm_msg)
            return

        # ------------------------------------------------------------------
        # STATE: CONFIRMATION
        # ------------------------------------------------------------------
        if state == "CONFIRMATION":
            lang = session.language
            text_body = (msg.get("text") or {}).get("body", "").strip()

            if text_body == "1":
                _save_report(
                    db, phone, session, session_answers, active_questions
                )
                db.delete(session)
                db.commit()

                thank_msg = (
                    "✅ Asante! Ripoti yako imepokelewa na NBD Wetland Watch."
                    if lang == "sw"
                    else "✅ Thank you! Your report has been received by NBD Wetland Watch."  # noqa
                )
                await _send_message(phone, thank_msg)

            elif text_body == "2":
                # Delete any uploaded media before clearing the session answers
                storage = StorageService()
                for q in active_questions:
                    if q.type in ("image", "attachment"):
                        val = session_answers.get(str(q.id))
                        if val and val not in ("UPLOAD_FAILED", "SKIPPED"):
                            storage.delete_file(val)

                session.answers = {}
                session.state = "DYNAMIC_QUESTION"
                from sqlalchemy.orm.attributes import flag_modified

                flag_modified(session, "answers")

                first_q = _get_next_active_question(active_questions, {}, None)
                if first_q:
                    session.current_question_id = first_q.id
                    db.commit()
                    reset_msg = (
                        "Kazi imefutwa. Tuanze tena tangu mwanzo."
                        if lang == "sw"
                        else "Report reset. Let's start again from the beginning."  # noqa
                    )
                    await _send_message(phone, reset_msg)
                    await _prompt_question(phone, first_q, lang, db)
                else:
                    db.delete(session)
                    db.commit()
            else:
                summary = _build_whatsapp_summary(
                    db, active_questions, session_answers, lang
                )
                if lang == "sw":
                    confirm_msg = (
                        "Tafadhali jibu kwa nambari sahihi.\n\n"
                        "Tafadhali hakikisha maelezo ya ripoti yako:\n"
                        f"{summary}\n\n"
                        "Jibu *1* kuthibitisha\n"
                        "Jibu *2* kuanza tena"
                    )
                else:
                    confirm_msg = (
                        "Please reply with a valid number.\n\n"
                        "Please review your report details:\n"
                        f"{summary}\n\n"
                        "Reply *1* to Confirm\n"
                        "Reply *2* to Redo"
                    )
                await _send_message(phone, confirm_msg)
            return

    except Exception as exc:
        logger.exception("Unhandled error in WhatsApp state machine: %s", exc)
        db.rollback()
        try:
            await _send_message(
                phone,
                "Sorry, an error occurred. Please try again later.",
            )
        except Exception:
            pass
    finally:
        db.close()


async def _prompt_question(
    phone: str, q: Question, lang: str, db: Session
) -> None:
    """Helper to format and send the question prompt to WhatsApp user."""
    from app.services.translation import get_translation

    q_label = get_translation(q.translations, lang, q.label)

    if q.type == "cascade":
        subcounties = _fetch_subcounties(db)
        menu = _format_location_menu(subcounties, lang)
        prompt = (
            f"Chagua eneo lako:\n\n{menu}"
            if lang == "sw"
            else f"Choose your location:\n\n{menu}"
        )
        await _send_message(phone, prompt)

    elif q.type == "option":
        options = (
            db.query(Option)
            .filter(Option.question_id == q.id)
            .order_by(Option.order.asc())
            .all()
        )
        menu = "\n".join(
            f"{i}: {get_translation(o.translations, lang, o.label)}"
            for i, o in enumerate(options, 1)
        )
        prompt = (
            f"Je, ungependa kuripoti nini?\n\n{menu}"
            if lang == "sw"
            else f"What would you like to report?\n\n{menu}"
        )
        await _send_message(phone, prompt)

    elif q.type in ("image", "attachment"):
        prompt = (
            f"Tafadhali tuma picha au video ya tukio (au jibu *skip* kuendelea bila picha/video)."  # noqa
            if lang == "sw"
            else f"Please send a photo or video of the incident (or reply *skip* to continue without media)."  # noqa
        )
        await _send_message(phone, prompt)

    else:
        await _send_message(phone, f"{q_label}:")
