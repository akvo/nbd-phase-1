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
from app.models.form import Form, Question, Option, FormNames
from app.models.submission import Datapoint, Answer
from app.models.spatial import SpatialBoundary, Basin
from app.models.citizen import Citizen
from app.services.storage import StorageService, build_blob_path

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


def _fetch_incident_options(db: Session) -> List[Option]:
    form = (
        db.query(Form)
        .filter(Form.name == FormNames.POLLUTION_REPORTING)
        .first()
    )
    if not form:
        return []
    q = (
        db.query(Question)
        .filter(Question.form_id == form.id, Question.name == "incident_type")
        .first()
    )
    if not q:
        return []
    return (
        db.query(Option)
        .filter(Option.question_id == q.id)
        .order_by(Option.order.asc())
        .all()
    )


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


def _save_report(
    db: Session,
    phone: str,
    session: WhatsAppSession,
    selected_option: Option,
    selected_sc: SpatialBoundary,
    media_gcs_path: Optional[str],
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

    q_incident = (
        db.query(Question)
        .filter(Question.form_id == form.id, Question.name == "incident_type")
        .first()
    )
    q_location = (
        db.query(Question)
        .filter(Question.form_id == form.id, Question.name == "location_id")
        .first()
    )
    q_media = (
        db.query(Question)
        .filter(
            Question.form_id == form.id,
            Question.name == "media_attachment",
        )
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
        else:
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
    else:
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

    # Answer: incident type (store option value)
    ans_incident = Answer(
        datapoint_id=dp.id,
        question_id=q_incident.id if q_incident else 0,
        name=None,
        options=[selected_option.value],
    )
    db.add(ans_incident)

    # Answer: location
    ans_location = Answer(
        datapoint_id=dp.id,
        question_id=q_location.id if q_location else 0,
        name=None,
        options=[str(selected_sc.id)],
    )
    db.add(ans_location)

    # Answer: media attachment path (if any)
    # Only persist when: a matching Question row exists AND upload succeeded.
    if media_gcs_path and media_gcs_path != "UPLOAD_FAILED":
        if q_media:
            ans_media = Answer(
                datapoint_id=dp.id,
                question_id=q_media.id,
                name=None,
                options=[media_gcs_path],
                index=1,
            )
            db.add(ans_media)
        else:
            logger.warning(
                "No 'media_attachment' question found for form_id=%s; "
                "skipping media answer (blob=%s)",
                form.id,
                media_gcs_path,
            )
    elif media_gcs_path == "UPLOAD_FAILED":
        logger.warning(
            "Media upload had previously failed for phone=%s; "
            "omitting media answer row.",
            phone,
        )

    db.commit()


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

        # ------------------------------------------------------------------
        # STATE: CONSENT
        # ------------------------------------------------------------------
        if state == "CONSENT":
            text_body = (msg.get("text") or {}).get("body", "").strip()
            welcome_msg = (
                "Welcome to NBD Wetland Watch \U0001f30a / Chagua lugha yako:\n\n"
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
                        "Jukwaa hili linakusanya taarifa za matukio ya mazingira. "
                        "Ripoti yako inahifadhiwa bila jina na matumizi ya data yamezuiliwa "
                        "kwa mipango ya ufuatiliaji.\n\n"
                        "Jibu *1* kukubali masharti na kuanza kuripoti.\n"
                        "Jibu *2* kukataa."
                    )
                else:
                    terms_msg = (
                        "Welcome to NBD Wetland Watch \U0001f30a\n\n"
                        "This platform collects environmental incident reports. "
                        "Your report is saved anonymously and data usage is "
                        "restricted to monitoring programs.\n\n"
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
                # Accepted — move to incident selection
                options = _fetch_incident_options(db)
                if not options:
                    if lang == "sw":
                        err_msg = "Samahani, mfumo haujaundwa bado. Tafadhali jaribu tena baadaye."
                    else:
                        err_msg = "Sorry, the reporting system is not yet configured. Please try again later."
                    await _send_message(phone, err_msg)
                    return

                from app.services.translation import get_translation

                menu = "\n".join(
                    f"{i}: {get_translation(o.translations, lang, o.label)}"
                    for i, o in enumerate(options, 1)
                )
                session.state = "INCIDENT_SELECT"
                db.commit()
                if lang == "sw":
                    prompt = f"Je, ungependa kuripoti nini?\n\n{menu}"
                else:
                    prompt = f"What would you like to report?\n\n{menu}"
                await _send_message(phone, prompt)
            elif text_body == "2":
                if lang == "sw":
                    decline_msg = "Ni lazima ukubali masharti ya data ili kuwasilisha ripoti. Tuma ujumbe wowote ili kuanza tena."
                else:
                    decline_msg = "You must accept the data terms to submit a report. Send any message to start again."
                await _send_message(phone, decline_msg)
                # Reset so they start fresh next time
                db.delete(session)
                db.commit()
            else:
                if lang == "sw":
                    terms_msg = (
                        "Karibu kwenye NBD Wetland Watch \U0001f30a\n\n"
                        "Jukwaa hili linakusanya taarifa za matukio ya mazingira. "
                        "Ripoti yako inahifadhiwa bila jina na matumizi ya data yamezuiliwa "
                        "kwa mipango ya ufuatiliaji.\n\n"
                        "Jibu *1* kukubali masharti na kuanza kuripoti.\n"
                        "Jibu *2* kukataa."
                    )
                else:
                    terms_msg = (
                        "Welcome to NBD Wetland Watch \U0001f30a\n\n"
                        "This platform collects environmental incident reports. "
                        "Your report is saved anonymously and data usage is "
                        "restricted to monitoring programs.\n\n"
                        "Reply *1* to accept terms and start reporting.\n"
                        "Reply *2* to decline."
                    )
                await _send_message(phone, terms_msg)
            return

        # ------------------------------------------------------------------
        # STATE: INCIDENT_SELECT
        # ------------------------------------------------------------------
        if state == "INCIDENT_SELECT":
            text_body = (msg.get("text") or {}).get("body", "").strip()
            options = _fetch_incident_options(db)
            lang = session.language
            from app.services.translation import get_translation

            try:
                idx = int(text_body) - 1
                if idx < 0 or idx >= len(options):
                    raise ValueError()
                selected = options[idx]
            except (ValueError, TypeError):
                menu = "\n".join(
                    f"{i}: {get_translation(o.translations, lang, o.label)}"
                    for i, o in enumerate(options, 1)
                )
                if lang == "sw":
                    prompt = f"Tafadhali jibu kwa nambari sahihi.\n\n{menu}"
                else:
                    prompt = f"Please reply with a valid number.\n\n{menu}"
                await _send_message(phone, prompt)
                return
            session.incident_type = selected.value
            session.option_text = selected.label
            session.state = "MEDIA_UPLOAD"
            db.commit()

            selected_label = get_translation(
                selected.translations, lang, selected.label
            )
            if lang == "sw":
                prompt = (
                    f"Ulichagua: *{selected_label}*\n\n"
                    "Tafadhali tuma picha au video ya tukio "
                    "(au jibu *skip* kuendelea bila picha/video)."
                )
            else:
                prompt = (
                    f"You selected: *{selected_label}*\n\n"
                    "Please send a photo or video of the incident "
                    "(or reply *skip* to continue without media)."
                )
            await _send_message(phone, prompt)
            return

        # ------------------------------------------------------------------
        # STATE: MEDIA_UPLOAD
        # ------------------------------------------------------------------
        if state == "MEDIA_UPLOAD":
            media_gcs_path = None
            lang = session.language
            if msg_type in ("image", "video", "document"):
                media_id = (msg.get(msg_type) or {}).get("id")
                mime_type = (msg.get(msg_type) or {}).get(
                    "mime_type", "application/octet-stream"
                )
                if media_id:
                    ext = mime_type.split("/")[-1].split(";")[0]
                    blob_name = build_blob_path("whatsapp", ext)
                    try:
                        # Step 1: resolve Meta media URL
                        media_url = await _get_media_url(media_id)
                        # Step 2: stream chunks to GCS (memory-safe, FR-002)
                        storage = StorageService()
                        await storage.stream_upload_async(
                            blob_name=blob_name,
                            chunks=_iter_media_chunks(media_url),
                            content_type=mime_type,
                        )
                        session.media_url = blob_name
                        logger.info(
                            "Media uploaded to GCS: %s (phone=%s)",
                            blob_name,
                            phone,
                        )
                    except Exception as exc:
                        # FR-006: log full traceback so GCS auth/network
                        # errors are visible in the container logs.
                        logger.error(
                            "Media upload failed for %s (blob=%s): %s",
                            phone,
                            blob_name,
                            exc,
                            exc_info=True,
                        )
                        session.media_url = "UPLOAD_FAILED"
            elif msg_type == "text":
                skip_text = (msg.get("text") or {}).get("body", "").strip()
                if skip_text.lower() != "skip":
                    if lang == "sw":
                        prompt = "Tafadhali tuma picha/video au jibu *skip*."
                    else:
                        prompt = "Please send a photo/video or reply *skip*."
                    await _send_message(phone, prompt)
                    return

            # Move to location
            subcounties = _fetch_subcounties(db)
            menu = _format_location_menu(subcounties, lang)
            session.state = "LOCATION_SELECT"
            db.commit()
            if lang == "sw":
                prompt = f"Chagua eneo lako:\n\n{menu}"
            else:
                prompt = f"Choose your location:\n\n{menu}"
            await _send_message(phone, prompt)
            return

        # ------------------------------------------------------------------
        # STATE: LOCATION_SELECT
        # ------------------------------------------------------------------
        if state == "LOCATION_SELECT":
            text_body = (msg.get("text") or {}).get("body", "").strip()
            subcounties = _fetch_subcounties(db)
            lang = session.language
            try:
                idx = int(text_body) - 1
                if idx < 0 or idx >= len(subcounties):
                    raise ValueError()
                selected_sc = subcounties[idx]
            except (ValueError, TypeError):
                menu = _format_location_menu(subcounties, lang)
                if lang == "sw":
                    prompt = f"Tafadhali jibu kwa nambari sahihi.\n\n{menu}"
                else:
                    prompt = f"Please reply with a valid number.\n\n{menu}"
                await _send_message(phone, prompt)
                return

            # Check if there are Level 3 sub-counties below the selected county
            sub_counties = (
                db.query(SpatialBoundary)
                .filter(
                    SpatialBoundary.level == 3,
                    SpatialBoundary.parent_id == selected_sc.id,
                )
                .order_by(SpatialBoundary.name)
                .all()
            )

            if sub_counties:
                session.state = "SUB_COUNTY_SELECT"
                session.location = str(selected_sc.id)
                db.commit()

                menu_lines = [
                    f"  {i}: {sc.name}" for i, sc in enumerate(sub_counties, 1)
                ]
                menu = "\n".join(menu_lines)
                if lang == "sw":
                    prompt = (
                        f"Chagua wilaya ndogo ya {selected_sc.name}:\n\n{menu}"
                    )
                else:
                    prompt = (
                        f"Choose sub-county of {selected_sc.name}:\n\n{menu}"
                    )
                await _send_message(phone, prompt)
                return

            # Fetch the selected option from session
            options = _fetch_incident_options(db)
            selected_option = next(
                (o for o in options if o.value == session.incident_type),
                None,
            )
            if not selected_option:
                logger.error(
                    "Cannot find option for incident_type=%s",
                    session.incident_type,
                )
                if lang == "sw":
                    err_msg = "Samahani, kuna kitu kimeenda vibaya. Tafadhali anza tena."
                else:
                    err_msg = (
                        "Sorry, something went wrong. Please start again."
                    )
                await _send_message(phone, err_msg)
                db.delete(session)
                db.commit()
                return

            _save_report(
                db,
                phone,
                session,
                selected_option,
                selected_sc,
                session.media_url,
            )
            # Delete session after successful submission
            db.delete(session)
            db.commit()
            if lang == "sw":
                thank_msg = "\u2705 Asante! Ripoti yako imepokelewa na NBD Wetland Watch."
            else:
                thank_msg = "\u2705 Thank you! Your report has been received by NBD Wetland Watch."
            await _send_message(phone, thank_msg)
            return

        # ------------------------------------------------------------------
        # STATE: SUB_COUNTY_SELECT
        # ------------------------------------------------------------------
        if state == "SUB_COUNTY_SELECT":
            text_body = (msg.get("text") or {}).get("body", "").strip()
            lang = session.language

            # Retrieve the selected county
            county_id = session.location
            selected_county = (
                db.query(SpatialBoundary)
                .filter(SpatialBoundary.id == county_id)
                .first()
            )
            if not selected_county:
                logger.error("County not found for ID %s", county_id)
                db.delete(session)
                db.commit()
                return

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
            except (ValueError, TypeError):
                menu_lines = [
                    f"  {i}: {sc.name}" for i, sc in enumerate(sub_counties, 1)
                ]
                menu = "\n".join(menu_lines)
                if lang == "sw":
                    prompt = f"Tafadhali jibu kwa nambari sahihi.\n\nChagua wilaya ndogo ya {selected_county.name}:\n\n{menu}"
                else:
                    prompt = f"Please reply with a valid number.\n\nChoose sub-county of {selected_county.name}:\n\n{menu}"
                await _send_message(phone, prompt)
                return

            # Fetch the selected option from session
            options = _fetch_incident_options(db)
            selected_option = next(
                (o for o in options if o.value == session.incident_type),
                None,
            )
            if not selected_option:
                logger.error(
                    "Cannot find option for incident_type=%s",
                    session.incident_type,
                )
                if lang == "sw":
                    err_msg = "Samahani, kuna kitu kimeenda vibaya. Tafadhali anza tena."
                else:
                    err_msg = (
                        "Sorry, something went wrong. Please start again."
                    )
                await _send_message(phone, err_msg)
                db.delete(session)
                db.commit()
                return

            _save_report(
                db,
                phone,
                session,
                selected_option,
                selected_sc,
                session.media_url,
            )
            # Delete session after successful submission
            db.delete(session)
            db.commit()
            if lang == "sw":
                thank_msg = "\u2705 Asante! Ripoti yako imepokelewa na NBD Wetland Watch."
            else:
                thank_msg = "\u2705 Thank you! Your report has been received by NBD Wetland Watch."
            await _send_message(phone, thank_msg)
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
