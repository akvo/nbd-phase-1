"""Facebook Messenger conversation state machine and ingestion service.

State flow:
    CONSENT -> DATA_TERMS -> DYNAMIC_QUESTION -> CONFIRMATION -> DONE

Parity with WhatsApp service:
- Only asks questions defined dynamically in the active Citizen Reporter form.
- Traverses questions dynamically in Group/Question Order with skip logic.
- Supports cascade spatial hierarchy (Counties -> Sub-counties -> Wards).
- Supports option menus with interactive Messenger Quick Replies.
- Streams photo evidence from Meta CDN to Google Cloud Storage.
- Confirmation step with full report summary and redo support.
- Persists completed reports into Datapoint and Answer tables.
"""

import hmac
import hashlib
import json
import logging
import httpx
import uuid
import base64
from typing import Any, AsyncIterator, Dict, List, Optional
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from geoalchemy2.shape import to_shape

from app.database import SessionLocal
from app.models.messenger_session import (
    MessengerSession,
    ProcessedWebhookMessage,
)
from app.models.form import (
    Form,
    Question,
    QuestionGroup,
    Option,
    FormNames,
    FormType,
    QuestionType,
)
from app.models.submission import Datapoint, Answer, SubmissionStatus
from app.models.spatial import SpatialBoundary, BoundaryLevel
from app.models.citizen import Citizen
from app.services.storage import StorageService, build_blob_path
from app.services.form_engine import is_question_active
from app.services.translation import get_translation
from app.services.spatial_service import (
    get_root_boundaries,
    get_child_boundaries,
    get_boundary_by_id,
)
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
# DB Helpers (Parity with WhatsApp Service)
# ---------------------------------------------------------------------------


def _get_or_create_session(
    db: Session, psid: str, page_id: str
) -> MessengerSession:
    """Retrieve existing session or instantiate a new one."""
    session = (
        db.query(MessengerSession)
        .filter_by(psid=psid, page_id=page_id)
        .first()
    )
    if session and session.created_at:
        now_dt = (
            datetime.now(timezone.utc)
            if session.created_at.tzinfo
            else datetime.utcnow()
        )
        age = now_dt - session.created_at
        if age > timedelta(hours=24):
            db.delete(session)
            db.commit()
            session = None

    if not session:
        session = MessengerSession(
            psid=psid,
            page_id=page_id,
            state="CONSENT",
            language="en",
            answers={},
        )
        db.add(session)
        db.flush()
    return session


def _fetch_pollution_form(db: Session) -> Optional[Form]:
    """Retrieve active Pollution Reporting Form snapshot."""
    return (
        db.query(Form)
        .filter(
            or_(
                Form.name == FormNames.POLLUTION_REPORTING,
                Form.type == FormType.CITIZEN_REPORTER.value,
            )
        )
        .first()
    )


def _fetch_form_questions(db: Session, form_id: int) -> List[Question]:
    """Fetch active questions ordered by QuestionGroup and Question order."""
    return (
        db.query(Question)
        .join(QuestionGroup, Question.question_group_id == QuestionGroup.id)
        .filter(
            Question.form_id == form_id,
            Question.deleted_at.is_(None),
            QuestionGroup.deleted_at.is_(None),
        )
        .order_by(
            QuestionGroup.order.asc().nullslast(),
            Question.order.asc().nullslast(),
        )
        .all()
    )


def _fetch_subcounties(db: Session) -> List[SpatialBoundary]:
    """Fetch root level boundaries for spatial cascade."""
    return get_root_boundaries(db)


def _format_location_menu(
    subcounties: List[SpatialBoundary], lang: str
) -> str:
    """Format hierarchical spatial options menu."""
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
    """Find the next question in list that is active, starting after current_q_id."""  # noqa
    start_checking = False if current_q_id else True
    for q in questions:
        if not start_checking:
            if q.id == current_q_id:
                start_checking = True
            continue
        if is_question_active(q, answers):
            return q
    return None


def _build_messenger_summary(
    db: Session,
    active_questions: List[Question],
    answers: Dict[str, Any],
    lang: str,
) -> str:
    """Construct a readable report review summary."""
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
            opt = None
            if q.options:
                opt = next(
                    (
                        o
                        for o in q.options
                        if str(o.value) == str(val) or str(o.id) == str(val)
                    ),
                    None,
                )
            if not opt:
                opt = (
                    db.query(Option)
                    .filter(
                        Option.question_id == q.id, Option.value == str(val)
                    )
                    .first()
                )
            val_label = (
                get_translation(opt.translations, lang, opt.label)
                if opt
                else str(val)
            )
        elif q.type == "cascade":
            sb = get_boundary_by_id(db, str(val))
            val_label = sb.name if sb else str(val)

        else:
            if val == "SKIPPED":
                val_label = "Skipped" if lang == "en" else "Imerukwa"
            elif not val:
                val_label = "None" if lang == "en" else "Hakuna"
            else:
                val_label = str(val)

        lines.append(f"• *{q_label}*: {val_label}")
    return "\n".join(lines)


def _save_report(
    db: Session,
    psid: str,
    session: MessengerSession,
    answers: Dict[str, Any],
    active_questions: List[Question],
) -> None:
    """Persist a completed Messenger report as Datapoint + Answers."""
    form = _fetch_pollution_form(db)
    if not form:
        logger.error("Pollution reporting form not found; aborting save.")
        return

    q_location = next(
        (q for q in active_questions if q.name == "location_id"), None
    )

    selected_sc = None
    if q_location and str(q_location.id) in answers:
        loc_val = answers[str(q_location.id)]
        selected_sc = get_boundary_by_id(db, loc_val)

    # Optional Citizen linkage if mapped
    citizen = None
    if session.citizen_id:
        citizen = (
            db.query(Citizen).filter(Citizen.id == session.citizen_id).first()
        )

    dp = Datapoint(
        uuid=uuid.uuid4(),
        form_id=form.id,
        published_version_id=form.active_version_id,
        submitter=f"messenger-{psid}",
        status=SubmissionStatus.PENDING,
        name=f"messenger-{psid}",
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

    # Save answers dynamically matching active form schema
    for q in active_questions:
        ans_val = answers.get(str(q.id))
        if ans_val is not None and ans_val not in ("UPLOAD_FAILED", "SKIPPED"):
            name = None
            value = None
            option = None

            if q.type in (
                QuestionType.geo,
                QuestionType.option,
                QuestionType.multiple_option,
            ):
                option = (
                    ans_val if isinstance(ans_val, list) else [str(ans_val)]
                )
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
                boundary = (
                    db.query(SpatialBoundary)
                    .filter(SpatialBoundary.id == ans_val)
                    .first()
                )
                if boundary:
                    name = boundary.name
                    chain = []
                    curr = boundary
                    while curr:
                        chain.insert(0, str(curr.id))
                        curr = curr.parent
                    option = chain
                else:
                    name = str(ans_val)
                    option = [str(ans_val)]
            else:
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
                index=(
                    1
                    if q.type in (QuestionType.image, QuestionType.attachment)
                    else None
                ),
            )
            db.add(ans)

    db.commit()


async def _prompt_question(
    psid: str, q: Question, lang: str, db: Session
) -> None:
    """Format and send question prompt with interactive quick replies."""
    q_label = get_translation(q.translations, lang, q.label)

    if q.type == "cascade":
        subcounties = _fetch_subcounties(db)
        menu = _format_location_menu(subcounties, lang)
        quick_replies = [
            {"title": f"{i}. {sc.name}"[:20], "payload": str(i)}
            for i, sc in enumerate(subcounties[:10], 1)
        ]
        prompt = f"{q_label}\n\n{menu}"
        await send_messenger_message(psid, prompt, quick_replies=quick_replies)

    elif q.type == "option":
        options = q.options or (
            db.query(Option)
            .filter(Option.question_id == q.id)
            .order_by(Option.order.asc())
            .all()
        )
        menu = "\n".join(
            f"{i}: {get_translation(o.translations, lang, o.label)}"
            for i, o in enumerate(options, 1)
        )
        quick_replies = [
            {
                "title": f"{i}. {get_translation(o.translations, lang, o.label)}"[:20],  # noqa: E501
                "payload": str(i),
            }
            for i, o in enumerate(options[:10], 1)
        ]
        prompt = f"{q_label}\n\n{menu}"
        await send_messenger_message(psid, prompt, quick_replies=quick_replies)

    elif q.type in ("image", "attachment"):
        quick_replies = None
        if not q.required:
            quick_replies = [{"title": "Skip", "payload": "skip"}]
        await send_messenger_message(
            psid, q_label, quick_replies=quick_replies
        )

    else:
        quick_replies = None
        if not q.required:
            quick_replies = [{"title": "Skip", "payload": "skip"}]
        await send_messenger_message(
            psid, f"{q_label}:", quick_replies=quick_replies
        )


# ---------------------------------------------------------------------------
# State Machine & Ingestion Engine
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
    session = _get_or_create_session(db, psid, page_id)
    state = session.state

    form = _fetch_pollution_form(db)
    if not form:
        logger.error("Pollution reporting form not found; aborting.")
        return

    active_questions = _fetch_form_questions(db, form.id)
    session_answers = session.answers or {}

    effective_input = qr_payload if qr_payload else text_input

    # -----------------------------------------------------------------------
    # STATE: CONSENT (Language Selection Gate)
    # -----------------------------------------------------------------------
    if state == "CONSENT":
        welcome_msg = (
            "Welcome to NBD Wetland Watch 🌊 / "
            "Chagua lugha yako:\n\n"
            "Reply 1 for English\n"
            "Reply 2 kwa Kiswahili"
        )
        quick_replies = [
            {"title": "1. English", "payload": "1"},
            {"title": "2. Kiswahili", "payload": "2"},
        ]

        if not effective_input:
            await send_messenger_message(
                psid, welcome_msg, quick_replies=quick_replies
            )
            return

        normalized = effective_input.lower()
        if normalized in ("1", "en", "english"):
            session.language = "en"
            session.state = "DATA_TERMS"
            db.commit()

            terms_msg = (
                "Welcome to NBD Wetland Watch 🌊\n\n"
                "This platform collects environmental incident reports. "
                "Your report is saved anonymously and data usage is "
                "restricted to monitoring programs.\n\n"
                "Reply 1 to accept terms and start reporting.\n"
                "Reply 2 to decline."
            )
            terms_qr = [
                {"title": "1. Accept Terms", "payload": "1"},
                {"title": "2. Decline", "payload": "2"},
            ]
            await send_messenger_message(
                psid, terms_msg, quick_replies=terms_qr
            )

        elif normalized in ("2", "sw", "kiswahili", "swahili"):
            session.language = "sw"
            session.state = "DATA_TERMS"
            db.commit()

            terms_msg = (
                "Karibu kwenye NBD Wetland Watch 🌊\n\n"
                "Jukwaa hili linakusanya taarifa za matukio ya mazingira. "
                "Ripoti yako inahifadhiwa bila jina na matumizi ya data "
                "yamezuiliwa kwa mipango ya ufuatiliaji.\n\n"
                "Jibu 1 kukubali masharti na kuanza kuripoti.\n"
                "Jibu 2 kukataa."
            )
            terms_qr = [
                {"title": "1. Kubali", "payload": "1"},
                {"title": "2. Kataa", "payload": "2"},
            ]
            await send_messenger_message(
                psid, terms_msg, quick_replies=terms_qr
            )
        else:
            await send_messenger_message(
                psid, welcome_msg, quick_replies=quick_replies
            )
        return

    # -----------------------------------------------------------------------
    # STATE: DATA_TERMS (Terms Acceptance Gate)
    # -----------------------------------------------------------------------
    if state == "DATA_TERMS":
        lang = session.language
        normalized = effective_input.lower()

        if normalized in ("1", "yes", "agree", "accept", "kubali", "ndio"):
            session_answers = {}
            session.answers = session_answers

            first_q = _get_next_active_question(
                active_questions, session_answers, None
            )
            if not first_q:
                thank_msg = (
                    "✅ Asante! Ripoti yako imepokelewa na NBD Wetland Watch."
                    if lang == "sw"
                    else "✅ Thank you! Your report has been received by NBD Wetland Watch."  # noqa: E501
                )
                await send_messenger_message(psid, thank_msg)
                db.delete(session)
                db.commit()
                return

            session.current_question_id = first_q.id
            session.state = "DYNAMIC_QUESTION"
            db.commit()

            await _prompt_question(psid, first_q, lang, db)

        elif normalized in ("2", "no", "decline", "kataa", "hapana"):
            decline_msg = (
                "Ni lazima ukubali masharti ya data ili kuwasilisha ripoti. "
                "Tuma ujumbe wowote ili kuanza tena."
                if lang == "sw"
                else "You must accept the data terms to submit a report. "
                "Send any message to start again."
            )
            await send_messenger_message(psid, decline_msg)
            db.delete(session)
            db.commit()

        else:
            if lang == "sw":
                terms_msg = (
                    "Karibu kwenye NBD Wetland Watch 🌊\n\n"
                    "Jukwaa hili linakusanya taarifa za matukio ya mazingira. "
                    "Ripoti yako inahifadhiwa bila jina na matumizi ya data "
                    "yamezuiliwa kwa mipango ya ufuatiliaji.\n\n"
                    "Jibu 1 kukubali masharti na kuanza kuripoti.\n"
                    "Jibu 2 kukataa."
                )
                terms_qr = [
                    {"title": "1. Kubali", "payload": "1"},
                    {"title": "2. Kataa", "payload": "2"},
                ]
            else:
                terms_msg = (
                    "Welcome to NBD Wetland Watch 🌊\n\n"
                    "This platform collects environmental incident reports. "
                    "Your report is saved anonymously and data usage is restricted "  # noqa: E501
                    "to monitoring programs.\n\n"
                    "Reply 1 to accept terms and start reporting.\n"
                    "Reply 2 to decline."
                )
                terms_qr = [
                    {"title": "1. Accept Terms", "payload": "1"},
                    {"title": "2. Decline", "payload": "2"},
                ]
            await send_messenger_message(
                psid, terms_msg, quick_replies=terms_qr
            )
        return

    # -----------------------------------------------------------------------
    # STATE: DYNAMIC_QUESTION (Form Questionnaire Traversal)
    # -----------------------------------------------------------------------
    if state == "DYNAMIC_QUESTION":
        lang = session.language
        curr_q = next(
            (
                q
                for q in active_questions
                if q.id == session.current_question_id
            ),
            None,
        )
        if not curr_q:
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
            selected_ids = (
                session.location.split("|") if session.location else []
            )

            if not selected_ids:
                options = _fetch_subcounties(db)
                parent_boundary = None
            else:
                current_parent_id = selected_ids[-1]
                parent_boundary = get_boundary_by_id(db, current_parent_id)
                options = (
                    get_child_boundaries(db, str(parent_boundary.id))
                    if parent_boundary
                    else []
                )

            chosen_boundary = None
            try:
                idx = int(effective_input) - 1
                if 0 <= idx < len(options):
                    chosen_boundary = options[idx]
            except (ValueError, TypeError):
                pass

            if not chosen_boundary:
                # Try matching by name
                for opt in options:
                    if opt.name.lower() == effective_input.lower():
                        chosen_boundary = opt
                        break

            if not chosen_boundary:
                if not parent_boundary:
                    menu = _format_location_menu(options, lang)
                    sub_prompt = menu
                else:
                    menu_lines = [
                        f"  {i}: {o.name}" for i, o in enumerate(options, 1)
                    ]
                    menu = "\n".join(menu_lines)
                    p_name = parent_boundary.name
                    sub_prompt = (
                        f"Chagua eneo chini ya {p_name}:\n\n{menu}"
                        if lang == "sw"
                        else f"Choose location under {p_name}:\n\n{menu}"
                    )

                prompt = (
                    f"Tafadhali jibu kwa nambari sahihi.\n\n{sub_prompt}"
                    if lang == "sw"
                    else f"Please reply with a valid number.\n\n{sub_prompt}"
                )
                quick_replies = [
                    {"title": f"{i}. {o.name}"[:20], "payload": str(i)}
                    for i, o in enumerate(options[:10], 1)
                ]
                await send_messenger_message(
                    psid, prompt, quick_replies=quick_replies
                )
                return

            # Check if chosen boundary has children
            children = get_child_boundaries(db, str(chosen_boundary.id))
            if children:
                new_path = (
                    f"{session.location}|{chosen_boundary.id}"
                    if session.location
                    else str(chosen_boundary.id)
                )
                session.location = new_path
                db.commit()

                menu_lines = [
                    f"  {i}: {ch.name}" for i, ch in enumerate(children, 1)
                ]
                menu = "\n".join(menu_lines)
                cb_name = chosen_boundary.name
                prompt = (
                    f"Chagua eneo chini ya {cb_name}:\n\n{menu}"
                    if lang == "sw"
                    else f"Choose location under {cb_name}:\n\n{menu}"
                )
                quick_replies = [
                    {"title": f"{i}. {ch.name}"[:20], "payload": str(i)}
                    for i, ch in enumerate(children[:10], 1)
                ]
                await send_messenger_message(
                    psid, prompt, quick_replies=quick_replies
                )
                return
            else:
                if chosen_boundary.level < BoundaryLevel.WARD:
                    cb_name = chosen_boundary.name
                    err_prompt = (
                        f"Eneo lazima liwe katika ngazi ya Wodi. "
                        f"Hakuna wodi zilizopatikana chini ya {cb_name}. "
                        "Tafadhali wasiliana na msimamizi."
                        if lang == "sw"
                        else f"Location must be specified at the Ward "
                        f"level (Level 4). No wards found under "
                        f"{cb_name}. Please contact support."
                    )
                    await send_messenger_message(psid, err_prompt)
                    return

                parsed_val = str(chosen_boundary.id)
                valid = True

        elif curr_q.type == "option":
            options = curr_q.options or (
                db.query(Option)
                .filter(Option.question_id == curr_q.id)
                .order_by(Option.order.asc())
                .all()
            )
            selected_opt = None
            try:
                idx = int(effective_input) - 1
                if 0 <= idx < len(options):
                    selected_opt = options[idx]
            except (ValueError, TypeError):
                pass

            if not selected_opt:
                # Match by option value or option label
                for opt in options:
                    if opt.value and opt.value.lower() == effective_input.lower():  # noqa: E501
                        selected_opt = opt
                        break
                    if opt.label and opt.label.lower() == effective_input.lower():  # noqa: E501
                        selected_opt = opt
                        break

            if selected_opt:
                parsed_val = selected_opt.value
                valid = True
            else:
                menu = "\n".join(
                    f"{i}: {get_translation(o.translations, lang, o.label)}"
                    for i, o in enumerate(options, 1)
                )
                prompt = (
                    f"Tafadhali jibu kwa nambari sahihi.\n\n{menu}"
                    if lang == "sw"
                    else f"Please reply with a valid number.\n\n{menu}"
                )
                quick_replies = [
                    {
                        "title": f"{i}. {get_translation(o.translations, lang, o.label)}"[:20],  # noqa: E501
                        "payload": str(i),
                    }
                    for i, o in enumerate(options[:10], 1)
                ]
                await send_messenger_message(
                    psid, prompt, quick_replies=quick_replies
                )
                return

        elif curr_q.type in ("image", "attachment"):
            photo_url = None
            for att in attachments:
                if att.get("type") in ("image", "video", "file", "fallback"):
                    photo_url = att.get("payload", {}).get("url")
                    break

            if photo_url:
                blob_name = build_blob_path("messenger", "jpg")
                try:
                    storage = StorageService()
                    await storage.stream_upload_async(
                        blob_name=blob_name,
                        chunks=iter_meta_media_chunks(photo_url),
                        content_type="image/jpeg",
                    )
                    parsed_val = blob_name
                    valid = True
                except Exception as exc:
                    logger.error(
                        "Media upload failed for Messenger user %s: %s",
                        psid,
                        exc,
                    )
                    parsed_val = "UPLOAD_FAILED"
                    valid = True
            elif effective_input.lower() == "skip" or not curr_q.required:
                parsed_val = "SKIPPED"
                valid = True
            else:
                prompt = (
                    "Tafadhali tuma picha au jibu *skip*."
                    if lang == "sw"
                    else "Please send a photo or reply *skip*."
                )
                quick_replies = [{"title": "Skip", "payload": "skip"}]
                await send_messenger_message(
                    psid, prompt, quick_replies=quick_replies
                )
                return

        else:
            if not curr_q.required:
                if effective_input.lower() in ("none", "skip", "-"):
                    parsed_val = "SKIPPED"
                else:
                    parsed_val = effective_input
                valid = True
            elif effective_input:
                parsed_val = effective_input
                valid = True

        if valid:
            session_answers[str(curr_q.id)] = parsed_val
            session.answers = session_answers
            flag_modified(session, "answers")
            session.location = None
            db.commit()

            next_q = _get_next_active_question(
                active_questions, session_answers, curr_q.id
            )
            if next_q:
                session.current_question_id = next_q.id
                db.commit()
                await _prompt_question(psid, next_q, lang, db)
            else:
                session.state = "CONFIRMATION"
                db.commit()

                summary = _build_messenger_summary(
                    db, active_questions, session_answers, lang
                )
                if lang == "sw":
                    confirm_msg = (
                        "Tafadhali hakikisha maelezo ya ripoti yako:\n"
                        f"{summary}\n\n"
                        "Jibu 1 kuthibitisha\n"
                        "Jibu 2 kuanza tena"
                    )
                    confirm_qr = [
                        {"title": "1. Thibitisha", "payload": "1"},
                        {"title": "2. Anza Tena", "payload": "2"},
                    ]
                else:
                    confirm_msg = (
                        "Please review your report details:\n"
                        f"{summary}\n\n"
                        "Reply 1 to Confirm\n"
                        "Reply 2 to Redo"
                    )
                    confirm_qr = [
                        {"title": "1. Confirm", "payload": "1"},
                        {"title": "2. Redo", "payload": "2"},
                    ]
                await send_messenger_message(
                    psid, confirm_msg, quick_replies=confirm_qr
                )
        return

    # -----------------------------------------------------------------------
    # STATE: CONFIRMATION
    # -----------------------------------------------------------------------
    if state == "CONFIRMATION":
        lang = session.language
        normalized = effective_input.lower()

        if normalized in ("1", "confirm", "yes", "thibitisha", "ndio"):
            _save_report(db, psid, session, session_answers, active_questions)
            db.delete(session)
            db.commit()

            thank_msg = (
                "✅ Asante! Ripoti yako imepokelewa na NBD Wetland Watch."
                if lang == "sw"
                else "✅ Thank you! Your report has been received by NBD Wetland Watch."  # noqa: E501
            )
            await send_messenger_message(psid, thank_msg)

        elif normalized in ("2", "redo", "reset", "anza tena"):
            # Delete any uploaded media before resetting
            storage = StorageService()
            for q in active_questions:
                if q.type in ("image", "attachment"):
                    val = session_answers.get(str(q.id))
                    if val and val not in ("UPLOAD_FAILED", "SKIPPED"):
                        storage.delete_file(val)

            session.answers = {}
            session.state = "DYNAMIC_QUESTION"
            flag_modified(session, "answers")

            first_q = _get_next_active_question(active_questions, {}, None)
            if first_q:
                session.current_question_id = first_q.id
                db.commit()
                reset_msg = (
                    "Kazi imefutwa. Tuanze tena tangu mwanzo."
                    if lang == "sw"
                    else "Report reset. Let's start again from the beginning."
                )
                await send_messenger_message(psid, reset_msg)
                await _prompt_question(psid, first_q, lang, db)
            else:
                db.delete(session)
                db.commit()

        else:
            summary = _build_messenger_summary(
                db, active_questions, session_answers, lang
            )
            if lang == "sw":
                confirm_msg = (
                    "Tafadhali jibu kwa nambari sahihi.\n\n"
                    "Tafadhali hakikisha maelezo ya ripoti yako:\n"
                    f"{summary}\n\n"
                    "Jibu 1 kuthibitisha\n"
                    "Jibu 2 kuanza tena"
                )
                confirm_qr = [
                    {"title": "1. Thibitisha", "payload": "1"},
                    {"title": "2. Anza Tena", "payload": "2"},
                ]
            else:
                confirm_msg = (
                    "Please reply with a valid number.\n\n"
                    "Please review your report details:\n"
                    f"{summary}\n\n"
                    "Reply 1 to Confirm\n"
                    "Reply 2 to Redo"
                )
                confirm_qr = [
                    {"title": "1. Confirm", "payload": "1"},
                    {"title": "2. Redo", "payload": "2"},
                ]
            await send_messenger_message(
                psid, confirm_msg, quick_replies=confirm_qr
            )
        return


# ---------------------------------------------------------------------------
# Data Deletion Request Handler (Meta GDPR / Privacy Policy Compliance)
# ---------------------------------------------------------------------------


def handle_data_deletion_request(
    signed_request: str, app_secret: str
) -> Dict[str, str]:
    """Decode Meta signed request and anonymize/purge user data."""
    try:
        encoded_sig, payload = signed_request.split(".", 1)
        # Fix base64 padding
        payload_bytes = base64.urlsafe_b64decode(payload + "==")
        data = json.loads(payload_bytes.decode("utf-8"))
        user_id = str(data.get("user_id", ""))

        db: Session = SessionLocal()
        try:
            # Purge transient session states
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
