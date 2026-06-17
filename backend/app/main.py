from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, EmailStr
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


app = FastAPI(
    title="Nbd Pilot API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
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
