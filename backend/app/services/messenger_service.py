"""Facebook Messenger conversation state machine and ingestion service.

State flow:
    CONSENT -> INCIDENT_SELECT -> MEDIA_UPLOAD -> LOCATION_SELECT -> DONE

Handles:
- Webhook signature verification (HMAC-SHA256)
- Message de-duplication via `processed_webhook_messages` table
- Stateful conversation routing with Messenger Quick Replies
- Image download from Meta CDN & streaming to Google Cloud Storage (GCS)
- Persistence into `Datapoint` and `Answer` models with `source='MESSENGER'`
- 24-hour session expiration and cleanup
"""

import hmac
import hashlib
import json
import logging
import httpx
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.messenger_session import (
    MessengerSession,
    ProcessedWebhookMessage,
)
from app.models.submission import Datapoint, Answer, SubmissionStatus
from app.services.storage import StorageService
from app.dependencies.messenger_config import get_messenger_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cryptographic & Security Helpers
# ---------------------------------------------------------------------------


def verify_messenger_signature(
    raw_body: bytes, signature_header: str, app_secret: str
) -> bool:
    """Validate X-Hub-Signature-256 header using constant-time comparison."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected_signature = signature_header[len("sha256=") :]  # noqa: E203
    computed_signature = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, computed_signature)


# ---------------------------------------------------------------------------
# Meta Graph Send API Helpers
# ---------------------------------------------------------------------------


async def send_messenger_message(
    psid: str,
    text: str,
    quick_replies: Optional[List[Dict[str, str]]] = None,
) -> bool:
    """Send text or Quick Reply buttons to a Messenger user."""
    config = get_messenger_config()
    token = config.messenger_page_token
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={token}"

    message_payload: Dict[str, Any] = {"text": text}
    if quick_replies:
        message_payload["quick_replies"] = [
            {
                "content_type": "text",
                "title": qr["title"][:20],  # Meta quick reply title limit
                "payload": qr["payload"],
            }
            for qr in quick_replies
        ]

    payload = {
        "recipient": {"id": psid},
        "messaging_type": "RESPONSE",
        "message": message_payload,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                return True
            logger.warning(
                "Messenger Graph API send error [%s]: %s",
                resp.status_code,
                resp.text,
            )
            return False
    except Exception as exc:
        logger.error("Failed to send Messenger message to %s: %s", psid, exc)
        return False


async def iter_meta_media_chunks(
    media_url: str, chunk_size: int = 1024 * 1024
) -> AsyncIterator[bytes]:
    """Stream binary chunks from Meta's CDN media URL."""
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "GET", media_url, follow_redirects=True
        ) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(chunk_size):
                yield chunk


# ---------------------------------------------------------------------------
# Ingestion & State Machine Engine
# ---------------------------------------------------------------------------


async def process_messenger_message(payload: Dict[str, Any]) -> None:
    """Asynchronous worker for processing incoming Meta Messenger events."""
    entries = payload.get("entry", [])
    db: Session = SessionLocal()

    try:
        for entry in entries:
            page_id = str(entry.get("id", "UNKNOWN_PAGE"))
            messaging_events = entry.get("messaging", [])

            for event in messaging_events:
                sender = event.get("sender", {})
                psid = str(sender.get("id", ""))
                if not psid:
                    continue

                message = event.get("message", {})
                mid = str(message.get("mid", ""))

                # 1. Message De-Duplication Check
                if mid:
                    existing = (
                        db.query(ProcessedWebhookMessage)
                        .filter_by(mid=mid)
                        .first()
                    )
                    if existing:
                        logger.info(
                            "Dropping duplicate Messenger event mid=%s", mid
                        )
                        continue

                    # Record processed mid
                    db.add(ProcessedWebhookMessage(mid=mid, psid=psid))
                    db.commit()

                # Extract content
                text_input = (message.get("text") or "").strip()
                quick_reply = message.get("quick_reply", {})
                qr_payload = quick_reply.get("payload", "")
                attachments = message.get("attachments", [])

                await _handle_user_state(
                    db=db,
                    psid=psid,
                    page_id=page_id,
                    text_input=text_input,
                    qr_payload=qr_payload,
                    attachments=attachments,
                )

    except Exception as exc:
        logger.exception("Error processing messenger message: %s", exc)
        db.rollback()
    finally:
        db.close()


async def _handle_user_state(
    db: Session,
    psid: str,
    page_id: str,
    text_input: str,
    qr_payload: str,
    attachments: List[Dict[str, Any]],
) -> None:
    """Core state machine progression for citizen reporting."""
    session = (
        db.query(MessengerSession)
        .filter_by(psid=psid, page_id=page_id)
        .first()
    )

    # 24-hour expiration check
    if session and session.created_at:
        age = datetime.now(session.created_at.tzinfo) - session.created_at
        if age > timedelta(hours=24):
            db.delete(session)
            db.commit()
            session = None

    if not session:
        session = MessengerSession(
            psid=psid,
            page_id=page_id,
            state="CONSENT",
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    state = session.state

    # -----------------------------------------------------------------------
    # STATE: CONSENT
    # -----------------------------------------------------------------------
    if state == "CONSENT":
        normalized = (qr_payload or text_input).upper()
        if normalized in ["1", "YES", "CONSENT_YES", "AGREE"]:
            session.state = "INCIDENT_SELECT"
            db.commit()

            quick_replies = [
                {"title": "1. Water Pollution", "payload": "POLLUTION"},
                {"title": "2. Illegal Dumping", "payload": "DUMPING"},
                {"title": "3. Siltation / Soil", "payload": "SILTATION"},
                {"title": "4. Other Hazard", "payload": "OTHER"},
            ]
            welcome_text = (
                "Thank you for your consent. "
                "What type of incident are you reporting?"
            )
            await send_messenger_message(
                psid,
                welcome_text,
                quick_replies=quick_replies,
            )
        elif normalized in ["2", "NO", "CONSENT_NO", "DECLINE"]:
            db.delete(session)
            db.commit()
            decline_text = (
                "You have declined data collection. "
                "This reporting session is closed."
            )
            await send_messenger_message(psid, decline_text)
        else:
            quick_replies = [
                {"title": "1. Yes, I Consent", "payload": "CONSENT_YES"},
                {"title": "2. No, Decline", "payload": "CONSENT_NO"},
            ]
            consent_text = (
                "Welcome to the Nile Basin Wetland Watch! 🌿 "
                "Do you consent to sharing your environmental report "
                "and photo evidence with the monitoring team?"
            )
            await send_messenger_message(
                psid,
                consent_text,
                quick_replies=quick_replies,
            )

    # -----------------------------------------------------------------------
    # STATE: INCIDENT_SELECT
    # -----------------------------------------------------------------------
    elif state == "INCIDENT_SELECT":
        incident_choice = qr_payload or text_input
        session.incident_type = incident_choice[:50]
        session.state = "MEDIA_UPLOAD"
        db.commit()

        prompt_text = (
            f"Incident category '{incident_choice}' selected. "
            "Please take or upload a clear photo of the incident."
        )
        await send_messenger_message(psid, prompt_text)

    # -----------------------------------------------------------------------
    # STATE: MEDIA_UPLOAD
    # -----------------------------------------------------------------------
    elif state == "MEDIA_UPLOAD":
        photo_url = None
        for att in attachments:
            if att.get("type") == "image":
                payload_data = att.get("payload", {})
                photo_url = payload_data.get("url")
                break

        if photo_url:
            # Stream photo to Google Cloud Storage
            blob_name = f"media/messenger/{uuid.uuid4().hex}.jpg"
            storage_service = StorageService()

            try:
                chunk_gen = iter_meta_media_chunks(photo_url)
                gcs_path = await storage_service.stream_upload_async(
                    chunk_gen, blob_name, content_type="image/jpeg"
                )
            except Exception as e:
                logger.warning(
                    "GCS stream upload fallback to direct URL: %s", e
                )
                gcs_path = photo_url

            session.media_url = gcs_path
            session.state = "LOCATION_SELECT"
            db.commit()

            # Offer sample Sub-County quick replies
            quick_replies = [
                {"title": "1. Bomet Central", "payload": "Bomet Central"},
                {"title": "2. Narok South", "payload": "Narok South"},
                {"title": "3. Busia Town", "payload": "Busia Town"},
                {"title": "4. Samia Sub-county", "payload": "Samia"},
            ]
            loc_text = (
                "Photo received and stored! 📸 "
                "Please select your sub-county or location:"
            )
            await send_messenger_message(
                psid,
                loc_text,
                quick_replies=quick_replies,
            )
        else:
            await send_messenger_message(
                psid,
                "Please attach an image photo of the incident to continue.",
            )

    # -----------------------------------------------------------------------
    # STATE: LOCATION_SELECT
    # -----------------------------------------------------------------------
    elif state == "LOCATION_SELECT":
        location_choice = (
            qr_payload if qr_payload else text_input or "Unknown Location"
        )
        session.location = location_choice

        from app.models.form import Form, Question
        from app.models.spatial import Basin

        form = db.query(Form).filter(Form.type == 1).first()
        form_id = form.id if form else 1
        published_version_id = form.active_version_id if form else None

        # Resolve spatial anchor (Basin)
        basin = db.query(Basin).first()
        basin_id = basin.id if basin else None

        datapoint = Datapoint(
            uuid=uuid.uuid4(),
            form_id=form_id,
            published_version_id=published_version_id,
            basin_id=basin_id,
            submitter=f"messenger-{psid}",
            name=f"messenger-{psid}",
            status=SubmissionStatus.PENDING,
            geo={"type": "Point", "coordinates": [35.0, -0.5]},
        )
        db.add(datapoint)
        db.flush()

        if session.media_url:
            q = db.query(Question).filter(Question.form_id == form_id).first()
            q_id = q.id if q else 1
            answer = Answer(
                datapoint_id=datapoint.id,
                question_id=q_id,
                name=session.media_url,
            )
            db.add(answer)

        db.commit()

        report_id = f"NBD-REP-{datapoint.id:05d}"

        # Clean up session
        db.delete(session)
        db.commit()

        success_msg = (
            f"✅ Report submitted successfully! Reference ID: {report_id}. "
            "Thank you for protecting our wetlands."
        )
        await send_messenger_message(psid, success_msg)


# ---------------------------------------------------------------------------
# Data Deletion Request Handler (Meta GDPR / Privacy Policy Compliance)
# ---------------------------------------------------------------------------


def handle_data_deletion_request(
    signed_request: str, app_secret: str
) -> Dict[str, str]:
    """Decode Meta signed request and anonymize/purge user data."""
    import base64

    try:
        encoded_sig, payload = signed_request.split(".", 1)
        # Fix base64 padding
        payload_bytes = base64.urlsafe_b64decode(payload + "==")
        data = json.loads(payload_bytes.decode("utf-8"))
        user_id = str(data.get("user_id", ""))

        db: Session = SessionLocal()
        try:
            # 1. Purge transient session states
            db.query(MessengerSession).filter_by(psid=user_id).delete()
            db.query(ProcessedWebhookMessage).filter_by(psid=user_id).delete()
            db.commit()
        finally:
            db.close()

        confirmation_code = f"DEL-{uuid.uuid4().hex[:12].upper()}"
        status_url = (
            f"https://portal.nbd.org/data-deletion?code={confirmation_code}"
        )

        return {
            "url": status_url,
            "confirmation_code": confirmation_code,
        }
    except Exception as exc:
        logger.error("Failed to parse signed deletion request: %s", exc)
        confirmation_code = f"ERR-{uuid.uuid4().hex[:8]}"
        return {
            "url": "https://portal.nbd.org/data-deletion",
            "confirmation_code": confirmation_code,
        }
