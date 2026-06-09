import logging
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from app.database import SessionLocal
from app.models.whatsapp_session import WhatsAppSession

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def hourly_kobotoolbox_pull():
    logger.info("Executing hourly KoboToolbox data pull...")
    from app.services.kobo import sync_kobo_submissions

    db = SessionLocal()
    try:
        results = sync_kobo_submissions(db)
        logger.info(
            "KoboToolbox sync: Processed %d forms, Ingested %d records.",
            results.get("processed_forms", 0),
            results.get("ingested_records", 0),
        )
        if results.get("errors"):
            logger.warning("KoboToolbox sync errors: %s", results["errors"])
    except Exception as e:
        logger.error("Error pulling data from KoboToolbox: %s", e)
    finally:
        db.close()
    logger.info("KoboToolbox pull completed.")


def monthly_gee_ingest():
    logger.info("Executing monthly GEE batch ingestion...")

    # Placeholder logic for GEE batch ingestions
    time.sleep(5)
    logger.info("GEE batch ingestion completed successfully.")


def cleanup_whatsapp_sessions():
    """Delete WhatsApp sessions older than 24 hours.

    Runs hourly to comply with Meta's 24-hour messaging window policy
    and to prevent stale session state from accumulating.
    """
    logger.info("Pruning stale WhatsApp sessions (>24h)...")
    cutoff = datetime.utcnow() - timedelta(hours=24)
    db = SessionLocal()
    try:
        deleted = (
            db.query(WhatsAppSession)
            .filter(WhatsAppSession.created_at < cutoff)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info("Removed %d expired WhatsApp session(s).", deleted)
    except Exception as exc:
        db.rollback()
        logger.error("Session cleanup failed: %s", exc)
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Initializing APScheduler daemon...")
    scheduler = BlockingScheduler()

    # Schedule hourly KoboToolbox pulls
    scheduler.add_job(hourly_kobotoolbox_pull, "cron", hour="*")

    # Schedule monthly GEE batch ingestions
    # (runs on the 1st of every month at 00:00)
    scheduler.add_job(monthly_gee_ingest, "cron", day=1, hour=0, minute=0)

    # Schedule hourly WhatsApp session cleanup
    scheduler.add_job(cleanup_whatsapp_sessions, "cron", hour="*")

    logger.info("Scheduler configured. Starting loop...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
