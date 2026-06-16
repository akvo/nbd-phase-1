import logging
from app.database import SessionLocal
from app.models.spatial import Site
from app.models.citizen import Citizen

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_citizens(db) -> None:
    logger.info("Starting citizen seeding...")

    # Fetch all available sites
    sites = db.query(Site).all()
    if not sites:
        logger.error(
            "No sites found in DB. Please run the spatial seeder first!"
        )
        return

    # Seed test citizens (both WATCHER and SCIENTIST roles) for each site
    extra_citizen_index = 100
    for site in sites:
        if site.code == "NBD-MARA-001":
            phones = {
                "SCIENTIST": "+254700000001",
                "WATCHER": "+254700000003",
            }
        elif site.code == "NBD-SIO-001":
            phones = {
                "SCIENTIST": "+254700000002",
                "WATCHER": "+254700000004",
            }
        else:
            phones = {
                "SCIENTIST": f"+254700000{extra_citizen_index}",
                "WATCHER": f"+254700000{extra_citizen_index + 1}",
            }
            extra_citizen_index += 2

        for role, phone in phones.items():
            existing = (
                db.query(Citizen).filter(Citizen.phone_number == phone).first()
            )
            if not existing:
                citizen = Citizen(
                    phone_number=phone,
                    site_id=site.id,
                    role=role,
                )
                db.add(citizen)
                logger.info(
                    f"Seeded citizen: {phone} as "
                    f"{role} linked to site {site.code} ({site.id})"
                )
            else:
                logger.info(f"Citizen {phone} already exists.")

    db.commit()
    logger.info("Citizen seeding successfully completed!")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_citizens(db)
    finally:
        db.close()
