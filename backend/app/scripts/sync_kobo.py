import logging
from app.database import SessionLocal
from app.services.kobo import sync_kobo_submissions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Executing manual KoboToolbox pull script...")
    db = SessionLocal()
    try:
        results = sync_kobo_submissions(db)
        logger.info(
            "Kobo sync: Processed %d forms, Ingested %d records.",
            results.get("processed_forms", 0),
            results.get("ingested_records", 0),
        )
        if results.get("errors"):
            logger.warning(
                "Errors encountered during manual sync: %s", results["errors"]
            )
    except Exception as e:
        logger.exception("Manual Kobo sync failed with error: %s", e)
    finally:
        db.close()
