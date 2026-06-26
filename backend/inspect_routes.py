from app.main import app
for r in app.routes:
    if "submissions" in getattr(r, "path", ""):
        print(f"{r.path} {getattr(r, 'methods', None)}")
