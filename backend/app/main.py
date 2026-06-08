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


app = FastAPI(
    title="Nbd Pilot API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

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
