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
import hmac
import hashlib
import json


router = APIRouter(prefix="/api/v1/whatsapp", tags=["WhatsApp"])


@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(..., alias="hub.mode"),
    verify_token: str = Query(..., alias="hub.verify_token"),
    challenge: str = Query(..., alias="hub.challenge"),
    config: WhatsAppConfig = Depends(get_whatsapp_config),
):
    """Meta subscription validation endpoint.
    Responds with the hub.challenge when the verify token matches.
    """
    if mode != "subscribe" or verify_token != config.verify_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verification token mismatch",
        )
    return Response(
        content=challenge, media_type="text/plain", status_code=200
    )


def _verify_signature(request: Request, config: WhatsAppConfig) -> bool:
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        return False
    body = request._body if hasattr(request, "_body") else None
    if body is None:
        # FastAPI reads body only once; we need to read it here
        body = request.scope.get("body")
    if body is None:
        return False
    expected = (
        "sha256="
        + hmac.new(
            key=config.app_secret.encode(), msg=body, digestmod=hashlib.sha256
        ).hexdigest()
    )
    return hmac.compare_digest(expected, signature)


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    config: WhatsAppConfig = Depends(get_whatsapp_config),
):
    """Entry point for Meta webhook POSTs.

    Verifies the HMAC signature, then enqueues the payload for
    asynchronous processing so Meta receives a 200 OK in < 300 ms
    (FR-004).
    """
    # Read raw body for signature verification
    raw_body = await request.body()
    # Store raw body for later use
    request._body = raw_body
    if not _verify_signature(request, config):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature"
        )
    payload = json.loads(raw_body)
    # Basic validation – Meta sends 'entry' list
    if not payload.get("entry"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed payload"
        )
    # Dispatch asynchronously — Meta gets the response before processing begins
    from app.services.whatsapp_service import process_whatsapp_message

    background_tasks.add_task(process_whatsapp_message, payload)
    return {"status": "accepted"}
