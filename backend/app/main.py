from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, EmailStr
from slowapi.errors import RateLimitExceeded

from app.limiter import limiter
from app.mail import EmailService
from app.routers.storage_router import router as storage_router
from app.routers.spatial_router import router as spatial_router
from app.routers.form_router import router as form_router
from app.routers.user_router import router as user_router
from app.routers.submission_router import router as submission_router
from app.routers.dead_letter_router import router as dead_letter_router
from app.routers.audit_log_router import router as audit_log_router
from app.routers.ussd_router import router as ussd_router
from app.routers.citizen_router import router as citizen_router
from app.routers.whatsapp_router import router as whatsapp_router
from app.routers.internal_router import router as internal_router
from app.routers.auth_router import router as auth_router
from app.routers.public_router import router as public_router
from app.routers.admin_router import router as admin_router
from app.routers.form_export_router import router as form_export_router


from fastapi.responses import JSONResponse


def custom_rate_limit_exceeded_handler(request, exc):
    retry_after = 60
    try:
        from datetime import datetime

        if (
            exc.limit
            and hasattr(exc.limit, "limit")
            and hasattr(exc.limit.limit, "reset_at")
        ):
            reset_at = exc.limit.limit.reset_at
            if reset_at:
                now = datetime.now().timestamp()
                retry_after = max(1, int(reset_at - now))
    except Exception:
        pass

    return JSONResponse(
        status_code=429,
        content={"detail": getattr(exc, "detail", "Rate limit exceeded")},
        headers={"Retry-After": str(retry_after)},
    )


API_DESCRIPTION = (
    "Welcome to the National Biodiversity Database (NBD) API.\n"
    "This API provides services for monitoring wetland health, managing "
    "spatial boundaries, and collecting sampling data.\n\n"
    "### Data Dictionary & Units\n"
    "The data structures exposed by this API contain strict metric "
    "definitions:\n"
    "- **pH**: Dimensionless scale (2.0 to 10.0)\n"
    "- **Temperature**: Degrees Celsius (°C)\n"
    "- **Dissolved Oxygen (DO)**: Milligrams per liter (mg/L)\n"
    "- **Invasive Macrophytes**: Cover percentage (%)\n"
    "- **CPUE**: Catch Per Unit Effort (kg/net-night)\n"
    "- **Health Indices / Scores**: Normalized (0.0 to 1.0)"
)


app = FastAPI(
    title="Nbd Pilot API",
    description=API_DESCRIPTION,
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded, custom_rate_limit_exceeded_handler
)


app.include_router(auth_router)
app.include_router(storage_router)
app.include_router(spatial_router)
app.include_router(form_router)
app.include_router(user_router)
app.include_router(submission_router)
app.include_router(dead_letter_router)
app.include_router(audit_log_router)
app.include_router(ussd_router)
app.include_router(citizen_router)
app.include_router(whatsapp_router)
app.include_router(internal_router)
app.include_router(public_router)
app.include_router(admin_router)
app.include_router(form_export_router)


class TestEmailRequest(BaseModel):
    to: EmailStr
    subject: str
    body: str


@app.get("/api")
def read_root():
    return {"message": "Hello from FastAPI backend"}


@app.get("/api/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/api/v1/test/email", status_code=202)
async def send_test_email(
    payload: TestEmailRequest, background_tasks: BackgroundTasks
):
    service = EmailService()
    background_tasks.add_task(
        service.send_email_async,
        to=payload.to,
        subject=payload.subject,
        html_body=payload.body,
    )
    return {"message": "Test email has been queued", "recipient": payload.to}


@app.get("/api/v1/test/mock-webhook-failure")
def mock_webhook_failure(
    endpoint: str,
    status_code: int = 500,
):
    from app.database import SessionLocal
    from app.models.user import User
    from app.models.audit_log import AuditLog

    db = SessionLocal()
    try:
        sys_user = User.get_or_create_system_user(db)
        entity_type = (
            "ussd_webhook" if endpoint == "ussd" else "whatsapp_webhook"
        )
        audit = AuditLog(
            actor_id=sys_user.id,
            action="POST",
            entity_type=entity_type,
            entity_id=str(status_code),
        )
        db.add(audit)
        db.commit()
        return {
            "status": "logged",
            "endpoint": f"/api/v1/{endpoint}",
            "logged_status_code": status_code,
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
