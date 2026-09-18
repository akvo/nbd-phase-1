from fastapi import (
    APIRouter,
    BackgroundTasks,
    Request,
    HTTPException,
    Depends,
    status,
    Query,
    Response,
    Form,
)
from app.dependencies.messenger_config import (
    get_messenger_config,
    MessengerConfig,
)
from app.services.messenger_service import (
    verify_messenger_signature,
    process_messenger_message,
    handle_data_deletion_request,
)
import json
import logging

router = APIRouter(prefix="/api/v1/messenger", tags=["Messenger"])
logger = logging.getLogger(__name__)


@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    verify_token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
    config: MessengerConfig = Depends(get_messenger_config),
):
    """Meta webhook verification endpoint (GET challenge handshake)."""
    if mode == "subscribe" and verify_token == config.messenger_verify_token:
        logger.info("Messenger webhook verification successful.")
        return Response(
            content=challenge, media_type="text/plain", status_code=200
        )

    logger.warning("Messenger webhook verification failed.")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Verification token mismatch",
    )


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    config: MessengerConfig = Depends(get_messenger_config),
):
    """Meta webhook event receiver (POST).

    Verifies the HMAC-SHA256 signature and dispatches payload to background.
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    # Security check: verify HMAC-SHA256 signature
    if not verify_messenger_signature(
        raw_body, signature, config.messenger_app_secret
    ):
        logger.warning(
            "Invalid X-Hub-Signature-256 received on Messenger webhook"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid signature",
        )

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body"
        )

    # Dispatch to background task worker for state machine processing
    background_tasks.add_task(process_messenger_message, payload)

    return Response(content="EVENT_RECEIVED", status_code=200)


@router.post("/data-deletion")
async def data_deletion_callback(
    signed_request: str = Form(...),
    config: MessengerConfig = Depends(get_messenger_config),
):
    """Mandatory Meta Data Deletion Request Callback.

    Complies with Meta Platform Terms & GDPR by processing data scrub requests.
    """
    result = handle_data_deletion_request(
        signed_request, config.messenger_app_secret
    )
    return result
