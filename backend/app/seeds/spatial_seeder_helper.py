import os
import json
import logging
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import shape, Polygon, MultiPolygon
from app.models.spatial import Basin, Wetland, Site, SpatialBoundary

logger = logging.getLogger(__name__)


def load_geojson_geometry(filename: str) -> MultiPolygon:
    geojson_path = os.path.join(os.path.dirname(__file__), "spatial", filename)
    with open(geojson_path, "r") as file:
        gj_data = json.load(file)

    if gj_data.get("type") == "FeatureCollection":
        geom_data = gj_data["features"][0]["geometry"]
    elif gj_data.get("type") == "GeometryCollection":
        geom_data = [
            g
            for g in gj_data["geometries"]
            if g["type"] in ("Polygon", "MultiPolygon")
        ][0]
    else:
        geom_data = gj_data

    geom_shape = shape(geom_data)

    if isinstance(geom_shape, Polygon):
        geom_shape = MultiPolygon([geom_shape])

    return geom_shape


def seed_spatial(db: Session):
    logger.info("Starting spatial seeding from JSON and GeoJSON data...")

    json_path = os.path.join(
        os.path.dirname(__file__), "spatial", "spatial_data.json"
    )
    if not os.path.exists(json_path):
        logger.error("Spatial seed data file not found at %s", json_path)
        return

    with open(json_path, "r") as file:
        data = json.load(file)

    geojson_basins = {
        "MARA": "mara-basin.geojson",
        "SIO_SITEKO": "sio-basin.geojson",
    }

    geojson_wetlands = {
        "LOWER_MARA_WETLAND": "mara-wetland.geojson",
        "SIO_ESTUARY_WETLAND": "sio-siteko-wetland.geojson",
    }

    # 1. Seed Basins
    for b_data in data.get("basins", []):
        basin_id = b_data["basin_id"]

        geojson_file = geojson_basins.get(basin_id)
        if geojson_file:
            try:
                geom_shape = load_geojson_geometry(geojson_file)
                geom_val = from_shape(geom_shape, srid=4326)
            except Exception as e:
                logger.error(
                    "Failed to load GeoJSON for basin %s: %s", basin_id, e
                )
                geom_val = from_shape(shape(b_data["geom"]), srid=4326)
        else:
            geom_val = from_shape(shape(b_data["geom"]), srid=4326)

        basin = db.query(Basin).filter(Basin.code == basin_id).first()
        if not basin:
            basin = Basin(
                code=basin_id,
                name=b_data["name"],
                geom=geom_val,
            )
            db.add(basin)
            db.flush()
            logger.info("Created Basin: %s", basin_id)
        else:
            basin.geom = geom_val
            db.flush()
            logger.info("Updated Basin geometry: %s", basin_id)

    # 2. Seed Wetlands
    for w_data in data.get("wetlands", []):
        wetland_id = w_data["wetland_id"]

        # Resolve parent basin string ID to UUID
        parent_basin = (
            db.query(Basin).filter(Basin.code == w_data["basin_id"]).first()
        )
        if not parent_basin:
            logger.error(
                "Parent Basin %s not found for Wetland %s",
                w_data["basin_id"],
                wetland_id,
            )
            continue

        geojson_file = geojson_wetlands.get(wetland_id)
        if geojson_file:
            try:
                geom_shape = load_geojson_geometry(geojson_file)
                geom_val = from_shape(geom_shape, srid=4326)
            except Exception as e:
                logger.error(
                    "Failed to load GeoJSON for wetland %s: %s",
                    wetland_id,
                    e,
                )
                geom_val = from_shape(shape(w_data["geom"]), srid=4326)
        else:
            geom_shape = shape(w_data["geom"])
            if isinstance(geom_shape, Polygon):
                geom_shape = MultiPolygon([geom_shape])
            geom_val = from_shape(geom_shape, srid=4326)

        wetland = db.query(Wetland).filter(Wetland.code == wetland_id).first()
        if not wetland:
            wetland = Wetland(
                code=wetland_id,
                basin_id=parent_basin.id,
                name=w_data["name"],
                geom=geom_val,
            )
            db.add(wetland)
            db.flush()
            logger.info("Created Wetland: %s", wetland_id)
        else:
            wetland.geom = geom_val
            db.flush()
            logger.info("Updated Wetland geometry: %s", wetland_id)

    # 3. Seed Sites
    for s_data in data.get("sites", []):
        site_id = s_data["site_id"]

        # Resolve parent wetland string ID to UUID
        parent_wetland = (
            db.query(Wetland)
            .filter(Wetland.code == s_data["wetland_id"])
            .first()
        )
        if not parent_wetland:
            logger.error(
                "Parent Wetland %s not found for Site %s",
                s_data["wetland_id"],
                site_id,
            )
            continue

        site = db.query(Site).filter(Site.code == site_id).first()
        if not site:
            site = Site(
                code=site_id,
                wetland_id=parent_wetland.id,
                name=s_data["name"],
                geom=from_shape(shape(s_data["geom"]), srid=4326),
            )
            db.add(site)
            db.flush()
            logger.info("Created Site: %s", site_id)
        else:
            logger.info("Site already exists: %s", site_id)

    # 4. Seed Spatial Boundaries (Hierarchical Regions and Districts)
    boundaries_data = data.get("spatial_boundaries", [])

    # 4.1 Seed Level 1 Boundaries (Regions)
    level1_map = {}
    for sb_data in [b for b in boundaries_data if b.get("level") == 1]:
        sb_name = sb_data["name"]
        basin_id_str = sb_data["basin_id"]

        parent_basin = (
            db.query(Basin).filter(Basin.code == basin_id_str).first()
        )
        if not parent_basin:
            logger.error(
                "Parent Basin %s not found for Region %s",
                basin_id_str,
                sb_name,
            )
            continue

        sb = (
            db.query(SpatialBoundary)
            .filter(
                SpatialBoundary.name == sb_name,
                SpatialBoundary.basin_id == parent_basin.id,
                SpatialBoundary.level == 1,
            )
            .first()
        )

        sh_geom = shape(sb_data["centroid_geom"])

        if not sb:
            sb = SpatialBoundary(
                name=sb_name,
                basin_id=parent_basin.id,
                level=1,
                parent_id=None,
                centroid_geom=from_shape(sh_geom, srid=4326),
            )
            db.add(sb)
            db.flush()
            logger.info(
                "Created Region (Level 1): %s in Basin %s",
                sb_name,
                basin_id_str,
            )
        else:
            sb.centroid_geom = from_shape(sh_geom, srid=4326)
            db.flush()
            logger.info(
                "Updated Region (Level 1): %s in Basin %s",
                sb_name,
                basin_id_str,
            )

        level1_map[sb_name] = sb.id

    # 4.2 Seed Level 2 Boundaries (Districts / Sub-counties)
    for sb_data in [b for b in boundaries_data if b.get("level") == 2]:
        sb_name = sb_data["name"]
        basin_id_str = sb_data["basin_id"]
        parent_name = sb_data.get("parent_name")

        parent_basin = (
            db.query(Basin).filter(Basin.code == basin_id_str).first()
        )
        if not parent_basin:
            logger.error(
                "Parent Basin %s not found for District %s",
                basin_id_str,
                sb_name,
            )
            continue

        parent_id = None
        if parent_name:
            parent_id = level1_map.get(parent_name)
            if not parent_id:
                # Fallback to query
                parent_obj = (
                    db.query(SpatialBoundary)
                    .filter(
                        SpatialBoundary.name == parent_name,
                        SpatialBoundary.basin_id == parent_basin.id,
                        SpatialBoundary.level == 1,
                    )
                    .first()
                )
                if parent_obj:
                    parent_id = parent_obj.id

        sb = (
            db.query(SpatialBoundary)
            .filter(
                SpatialBoundary.name == sb_name,
                SpatialBoundary.basin_id == parent_basin.id,
                SpatialBoundary.level == 2,
            )
            .first()
        )

        sh_geom = shape(sb_data["centroid_geom"])

        if not sb:
            sb = SpatialBoundary(
                name=sb_name,
                basin_id=parent_basin.id,
                level=2,
                parent_id=parent_id,
                centroid_geom=from_shape(sh_geom, srid=4326),
            )
            db.add(sb)
            logger.info(
                "Created District (Level 2): %s in Basin %s",
                sb_name,
                basin_id_str,
            )
        else:
            sb.parent_id = parent_id
            sb.centroid_geom = from_shape(sh_geom, srid=4326)
            logger.info(
                "Updated District (Level 2): %s in Basin %s",
                sb_name,
                basin_id_str,
            )

    db.commit()
    logger.info("Spatial seeding successfully completed!")
