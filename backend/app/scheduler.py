import logging
import time
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def hourly_kobotoolbox_pull():
    logger.info("Executing hourly KoboToolbox data pull...")
    # Placeholder logic for pulling KoboToolbox records
    time.sleep(2)
    logger.info("KoboToolbox pull completed successfully.")


def monthly_gee_ingest():
    logger.info("Executing monthly GEE batch ingestion...")
    # Placeholder logic for GEE batch ingestions
    time.sleep(5)
    logger.info("GEE batch ingestion completed successfully.")


if __name__ == "__main__":
    logger.info("Initializing APScheduler daemon...")
    scheduler = BlockingScheduler()

    # Schedule hourly KoboToolbox pulls
    scheduler.add_job(hourly_kobotoolbox_pull, "cron", hour="*")

    # Schedule monthly GEE batch ingestions
    # (runs on the 1st of every month at 00:00)
    scheduler.add_job(monthly_gee_ingest, "cron", day=1, hour=0, minute=0)

    logger.info("Scheduler configured. Starting loop...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
