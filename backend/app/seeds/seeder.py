import logging
from app.database import SessionLocal
from app.seeds.form_seeder_helper import seed_forms

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_forms(db)
    finally:
        db.close()
