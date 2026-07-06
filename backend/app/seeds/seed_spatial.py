import logging
from app.database import SessionLocal
from app.seeds.spatial_seeder_helper import seed_spatial

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_spatial(db)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
