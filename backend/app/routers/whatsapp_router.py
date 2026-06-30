from fastapi import (
    APIRouter,
    BackgroundTasks,
    Request,
    HTTPException,
    Depends,
    status,
    Query,
    Response,
)
from app.dependencies.whatsapp_config import (
    get_whatsapp_config,
    WhatsAppConfig,
)
from twilio.request_validator import RequestValidator
from app.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/whatsapp", tags=["WhatsApp"])


@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    verify_token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    """Twilio verification compatibility or health endpoint.
    Responds with the hub.challenge or OK.
    """
    if challenge:
        return Response(
            content=challenge, media_type="text/plain", status_code=200
        )
    return Response(content="OK", media_type="text/plain", status_code=200)


def _verify_signature(
    url: str, params: dict, signature: str, auth_token: str
) -> bool:
    if not signature:
        return False
    validator = RequestValidator(auth_token)
    if validator.validate(url, params, signature):
        return True
    # Fallback: if the server received HTTP but the
    # client sent HTTPS (common behind proxies)
    if url.startswith("http://"):
        https_url = url.replace("http://", "https://", 1)
        if validator.validate(https_url, params, signature):
            return True
    return False


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    config: WhatsAppConfig = Depends(get_whatsapp_config),
    db: Session = Depends(get_db),
):
    """Entry point for Twilio webhook POSTs.

    Verifies the Twilio signature, then enqueues the payload for
    asynchronous processing.
    """
    from app.models.user import User
    from app.models.audit_log import AuditLog

    status_code = 200
    try:
        # Parse form parameters
        form_data = await request.form()
        params = dict(form_data)

        signature = request.headers.get("X-Twilio-Signature", "")

        # Reconstruct public URL if forwarded
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host", request.url.netloc)
        path = request.url.path
        url = f"{scheme}://{host}{path}"
        if request.url.query:
            url += f"?{request.url.query}"

        print(f"[TWILIO DEBUG] URL: {url}", flush=True)
        print(f"[TWILIO DEBUG] Signature: {signature}", flush=True)
        print(f"[TWILIO DEBUG] Params: {params}", flush=True)
        token_prefix = config.auth_token[:4]
        print(f"[TWILIO DEBUG] Auth Token: {token_prefix}...", flush=True)

        if not _verify_signature(url, params, signature, config.auth_token):
            status_code = 403
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid signature",
            )

        # Dispatch asynchronously
        from app.services.whatsapp_service import process_whatsapp_message

        background_tasks.add_task(process_whatsapp_message, params)

        # Return a valid empty TwiML response to Twilio
        twiml_content = "<Response></Response>"
        return Response(
            content=twiml_content, media_type="text/xml", status_code=200
        )
    except HTTPException as http_err:
        status_code = http_err.status_code
        raise http_err
    except Exception as err:
        status_code = 500
        raise err
    finally:
        try:
            sys_user = User.get_or_create_system_user(db)
            audit = AuditLog(
                actor_id=sys_user.id,
                action="POST",
                entity_type="whatsapp_webhook",
                entity_id=str(status_code),
            )
            db.add(audit)
            db.commit()
        except Exception:
            db.rollback()
