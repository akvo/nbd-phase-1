from fastapi import FastAPI

app = FastAPI(title="Nbd Pilot API", version="1.0.0")


@app.get("/api")
def read_root():
    return {"message": "Hello from FastAPI backend"}


@app.get("/api/healthz")
def healthz():
    return {"status": "ok"}
