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
        .order_by(SpatialBoundary.name)
        .all()
    )


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
            pt = to_shape(selected_sc.centroid_geom)
            dp.geo = {"type": "Point", "coordinates": [pt.x, pt.y]}
    else:
        dp.basin_id = selected_sc.basin_id
        pt = to_shape(selected_sc.centroid_geom)
        dp.geo = {"type": "Point", "coordinates": [pt.x, pt.y]}

    db.add(dp)
    db.flush()

    # Answer: incident type (store option label)
    ans_incident = Answer(
        datapoint_id=dp.id,
        question_id=q_incident.id if q_incident else 0,
        name="incident_type",
        options=[selected_option.label],
    )
    db.add(ans_incident)

    # Answer: location
    ans_location = Answer(
        datapoint_id=dp.id,
        question_id=q_location.id if q_location else 0,
        name="sub_county",
        options=[selected_sc.name],
    )
    db.add(ans_location)

    # Answer: media attachment path (if any)
    # Only persist when: a matching Question row exists AND upload succeeded.
    if media_gcs_path and media_gcs_path != "UPLOAD_FAILED":
        if q_media:
            ans_media = Answer(
                datapoint_id=dp.id,
                question_id=q_media.id,
                name="media_attachment",
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
            consent_msg = (
                "Welcome to NBD Wetland Watch \U0001f30a\n\n"
                "This platform collects environmental incident reports. "
                "Your report is saved anonymously and data usage is "
                "restricted to monitoring programs.\n\n"
                "Reply *1* to accept terms and start reporting.\n"
                "Reply *2* to decline."
            )
            if not text_body:
                await _send_message(phone, consent_msg)
                return
            if text_body == "1":
                # Accepted — move to incident selection
                options = _fetch_incident_options(db)
                if not options:
                    await _send_message(
                        phone,
                        "Sorry, the reporting system is not yet configured. "
                        "Please try again later.",
                    )
                    return
                menu = "\n".join(
                    f"{i}: {o.label}" for i, o in enumerate(options, 1)
                )
                session.state = "INCIDENT_SELECT"
                db.commit()
                await _send_message(
                    phone, f"What would you like to report?\n\n{menu}"
                )
            elif text_body == "2":
                session.state = "CONSENT"
                db.commit()
                await _send_message(
                    phone,
                    "You must accept the data terms to submit a report. "
                    "Send any message to start again.",
                )
                # Reset so they start fresh next time
                db.delete(session)
                db.commit()
            else:
                await _send_message(phone, consent_msg)
            return

        # ------------------------------------------------------------------
        # STATE: INCIDENT_SELECT
        # ------------------------------------------------------------------
        if state == "INCIDENT_SELECT":
            text_body = (msg.get("text") or {}).get("body", "").strip()
            options = _fetch_incident_options(db)
            try:
                idx = int(text_body) - 1
                if idx < 0 or idx >= len(options):
                    raise ValueError()
                selected = options[idx]
            except (ValueError, TypeError):
                menu = "\n".join(
                    f"{i}: {o.label}" for i, o in enumerate(options, 1)
                )
                await _send_message(
                    phone,
                    f"Please reply with a valid number.\n\n{menu}",
                )
                return
            session.incident_type = selected.value
            session.option_text = selected.label
            session.state = "MEDIA_UPLOAD"
            db.commit()
            await _send_message(
                phone,
                f"You selected: *{selected.label}*\n\n"
                "Please send a photo or video of the incident "
                "(or reply *skip* to continue without media).",
            )
            return

        # ------------------------------------------------------------------
        # STATE: MEDIA_UPLOAD
        # ------------------------------------------------------------------
        if state == "MEDIA_UPLOAD":
            media_gcs_path = None
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
                    await _send_message(
                        phone,
                        "Please send a photo/video or reply *skip*.",
                    )
                    return

            # Move to location
            subcounties = _fetch_subcounties(db)
            menu = "\n".join(
                f"{i}: {sc.name}" for i, sc in enumerate(subcounties, 1)
            )
            session.state = "LOCATION_SELECT"
            db.commit()
            await _send_message(phone, f"Choose your location:\n\n{menu}")
            return

        # ------------------------------------------------------------------
        # STATE: LOCATION_SELECT
        # ------------------------------------------------------------------
        if state == "LOCATION_SELECT":
            text_body = (msg.get("text") or {}).get("body", "").strip()
            subcounties = _fetch_subcounties(db)
            try:
                idx = int(text_body) - 1
                if idx < 0 or idx >= len(subcounties):
                    raise ValueError()
                selected_sc = subcounties[idx]
            except (ValueError, TypeError):
                menu = "\n".join(
                    f"{i}: {sc.name}" for i, sc in enumerate(subcounties, 1)
                )
                await _send_message(
                    phone,
                    f"Please reply with a valid number.\n\n{menu}",
                )
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
                await _send_message(
                    phone,
                    "Sorry, something went wrong. Please start again.",
                )
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
            await _send_message(
                phone,
                "\u2705 Thank you! Your report has been received by "
                "NBD Wetland Watch.",
            )
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
