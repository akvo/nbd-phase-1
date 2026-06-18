import csv
import logging
from app.database import SessionLocal
from app.models.spatial import Site

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_sites_to_csv():
    logger.info("Starting site export to CSV...")
    db = SessionLocal()
    try:
        sites = db.query(Site).order_by(Site.code).all()
        filepath = "/app/app/seeds/sites.csv"

        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Kobo select_one_from_file requires 'name' and 'label'
            writer.writerow(["name", "label"])
            for site in sites:
                writer.writerow([site.code, site.name])

        logger.info(f"Exported {len(sites)} sites to {filepath}")
    except Exception as e:
        logger.exception("Failed to export sites: %s", e)
    finally:
        db.close()


if __name__ == "__main__":
    export_sites_to_csv()
