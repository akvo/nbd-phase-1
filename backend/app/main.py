from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, EmailStr
from app.mail import EmailService
from app.routers.storage_router import router as storage_router



app = FastAPI(title="Nbd Pilot API", version="1.0.0")
app.include_router(storage_router)


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
