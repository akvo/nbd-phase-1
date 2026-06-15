import logging
from app.database import SessionLocal
from app.models.spatial import Site
from app.models.citizen import Citizen

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_citizens(db) -> None:
    logger.info("Starting citizen seeding...")

    # Fetch reference sites to link seeded citizens
    site_mara = db.query(Site).filter(Site.code == "NBD-MARA-001").first()
    site_sio = db.query(Site).filter(Site.code == "NBD-SIO-001").first()

    if not site_mara or not site_sio:
        logger.error(
            "Required sites NBD-MARA-001 or NBD-SIO-001 not found. "
            "Please run the spatial seeder first!"
        )
        return

    # Seed test citizens (both WATCHER and SCIENTIST roles)
    citizen_data = [
        {
            "phone_number": "+254700000001",
            "site_id": site_mara.id,
            "role": "SCIENTIST",
        },
        {
            "phone_number": "+254700000002",
            "site_id": site_sio.id,
            "role": "SCIENTIST",
        },
        {
            "phone_number": "+254700000003",
            "site_id": site_mara.id,
            "role": "WATCHER",
        },
        {
            "phone_number": "+254700000004",
            "site_id": site_sio.id,
            "role": "WATCHER",
        },
    ]

    for c_info in citizen_data:
        existing = (
            db.query(Citizen)
            .filter(Citizen.phone_number == c_info["phone_number"])
            .first()
        )
        if not existing:
            citizen = Citizen(
                phone_number=c_info["phone_number"],
                site_id=c_info["site_id"],
                role=c_info["role"],
            )
            db.add(citizen)
            logger.info(
                f"Seeded citizen: {c_info['phone_number']} as "
                f"{c_info['role']} linked to site {c_info['site_id']}"
            )
        else:
            logger.info(f"Citizen {c_info['phone_number']} already exists.")

    db.commit()
    logger.info("Citizen seeding successfully completed!")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_citizens(db)
    finally:
        db.close()
