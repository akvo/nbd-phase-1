import os
import json
import logging
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import shape
from app.models.spatial import Basin, Wetland, Site, SpatialBoundary

logger = logging.getLogger(__name__)


def seed_spatial(db: Session):
    logger.info("Starting spatial seeding from JSON data...")

    json_path = os.path.join(
        os.path.dirname(__file__), "spatial", "spatial_data.json"
    )
    if not os.path.exists(json_path):
        logger.error("Spatial seed data file not found at %s", json_path)
        return

    with open(json_path, "r") as file:
        data = json.load(file)

    # 1. Seed Basins
    for b_data in data.get("basins", []):
        basin_id = b_data["basin_id"]
        basin = db.query(Basin).filter(Basin.basin_id == basin_id).first()
        if not basin:
            basin = Basin(
                basin_id=basin_id,
                name=b_data["name"],
                geom=from_shape(shape(b_data["geom"]), srid=4326),
            )
            db.add(basin)
            db.flush()
            logger.info("Created Basin: %s", basin_id)
        else:
            logger.info("Basin already exists: %s", basin_id)

    # 2. Seed Wetlands
    for w_data in data.get("wetlands", []):
        wetland_id = w_data["wetland_id"]
        wetland = (
            db.query(Wetland).filter(Wetland.wetland_id == wetland_id).first()
        )
        if not wetland:
            wetland = Wetland(
                wetland_id=wetland_id,
                basin_id=w_data["basin_id"],
                name=w_data["name"],
                geom=from_shape(shape(w_data["geom"]), srid=4326),
            )
            db.add(wetland)
            db.flush()
            logger.info("Created Wetland: %s", wetland_id)
        else:
            logger.info("Wetland already exists: %s", wetland_id)

    # 3. Seed Sites
    for s_data in data.get("sites", []):
        site_id = s_data["site_id"]
        site = db.query(Site).filter(Site.site_id == site_id).first()
        if not site:
            site = Site(
                site_id=site_id,
                wetland_id=s_data["wetland_id"],
                name=s_data["name"],
                geom=from_shape(shape(s_data["geom"]), srid=4326),
            )
            db.add(site)
            db.flush()
            logger.info("Created Site: %s", site_id)
        else:
            logger.info("Site already exists: %s", site_id)

    # 4. Seed Spatial Boundaries (Sub-Counties)
    for sb_data in data.get("sub_counties", []):
        sb_name = sb_data["name"]
        basin_id = sb_data["basin_id"]

        sb = (
            db.query(SpatialBoundary)
            .filter(
                SpatialBoundary.name == sb_name,
                SpatialBoundary.basin_id == basin_id,
            )
            .first()
        )

        sh_geom = shape(sb_data["centroid_geom"])

        if not sb:
            sb = SpatialBoundary(
                name=sb_name,
                basin_id=basin_id,
                centroid_geom=from_shape(sh_geom, srid=4326),
            )
            db.add(sb)
            logger.info(
                "Created Sub-County: %s in Basin %s", sb_name, basin_id
            )
        else:
            sb.centroid_geom = from_shape(sh_geom, srid=4326)
            logger.info(
                "Updated/Verified Sub-County: %s in Basin %s",
                sb_name,
                basin_id,
            )

    db.commit()
    logger.info("Spatial seeding successfully completed!")
