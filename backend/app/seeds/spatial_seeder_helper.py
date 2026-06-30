import os
import json
import logging
import csv
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
        "Mara_Wetland": "mara-wetland.geojson",
        "Sio_Siteko_Wetland": "sio-siteko-wetland.geojson",
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
            wetland.name = w_data["name"]
            wetland.basin_id = parent_basin.id
            wetland.geom = geom_val
            db.flush()
            logger.info("Updated Wetland: %s", wetland_id)

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
            site.name = s_data["name"]
            site.wetland_id = parent_wetland.id
            site.geom = from_shape(shape(s_data["geom"]), srid=4326)
            db.flush()
            logger.info("Updated Site properties: %s", site_id)

        from app.models.management_action import ManagementAction

        actions_templates = {
            "GREEN": [
                (
                    "Routine Patrols",
                    "Conduct standard monthly water sampling and visual checks.",  # noqa
                ),
                (
                    "Community Engagement",
                    "Hold educational workshops with local farmers on sustainable wetland use.",  # noqa
                ),
            ],
            "YELLOW": [
                (
                    "Establish Silt Traps & Grass Strips",
                    "Catch sediment and runoff from crop boundaries near the wetland.",  # noqa
                ),
                (
                    "Constructed Wetlands",
                    "Setup domestic greywater filters around housing zones adjacent to the basin.",  # noqa
                ),
                (
                    "Livelihood Transitions",
                    "Guide farmers to apiculture (beekeeping) or sustainable macrophyte harvesting.",  # noqa
                ),  # noqa
                (
                    "Riparian Re-vegetation",
                    "Target plantings of indigenous species along degraded river banks.",  # noqa
                ),  # noqa
            ],
            "RED": [
                (
                    "Report Discharge",
                    "Log effluent discharge with local Ministry of Environment and Water units.",  # noqa
                ),  # noqa
                (
                    "Interceptor STPs",
                    "Direct untreated sewage to local treatment plants to halt degradation.",  # noqa
                ),  # noqa
                (
                    "Buffer Enactment",
                    "Stop agricultural encroachment using local buffer regulations under EMCA.",  # noqa
                ),  # noqa
                (
                    "Mesh Controls",
                    "Direct fishermen to larger gillnet sizes to protect breeding fish stocks.",  # noqa
                ),  # noqa
            ],
        }

        for color, actions in actions_templates.items():
            for label, desc in actions:
                existing_action = (
                    db.query(ManagementAction)
                    .filter(
                        ManagementAction.site_id == site.id,
                        ManagementAction.status_color == color,
                        ManagementAction.short_label == label,
                    )
                    .first()
                )
                if not existing_action:
                    action = ManagementAction(
                        site_id=site.id,
                        status_color=color,
                        short_label=label,
                        description_text=desc,
                    )
                    db.add(action)
                    db.flush()

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

    # 4.2 Seed Level 2 (Counties) and Level 3 (Sub-counties) from CSV files
    csv_mappings = [
        {
            "file": "Mara-sub-counties.csv",
            "basin_code": "MARA",
            "parent_region_name": "Mara Region",
        },
        {
            "file": "Sio-sub-counties.csv",
            "basin_code": "SIO_SITEKO",
            "parent_region_name": "Sio-Siteko Region",
        },
    ]

    for mapping in csv_mappings:
        csv_file = mapping["file"]
        basin_code = mapping["basin_code"]
        parent_region_name = mapping["parent_region_name"]

        parent_basin = db.query(Basin).filter(Basin.code == basin_code).first()
        if not parent_basin:
            logger.error(
                "Parent Basin %s not found for CSV %s", basin_code, csv_file
            )
            continue

        region_id = level1_map.get(parent_region_name)
        if not region_id:
            region_obj = (
                db.query(SpatialBoundary)
                .filter(
                    SpatialBoundary.name == parent_region_name,
                    SpatialBoundary.basin_id == parent_basin.id,
                    SpatialBoundary.level == 1,
                )
                .first()
            )
            if region_obj:
                region_id = region_obj.id
            else:
                logger.error("Region %s not found in DB", parent_region_name)
                continue

        csv_path = os.path.join(os.path.dirname(__file__), "spatial", csv_file)
        if not os.path.exists(csv_path):
            logger.error("CSV file not found at %s", csv_path)
            continue

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                county_name = row.get("County", "").strip()
                sub_county_name = row.get("Sub-County", "").strip()

                if not county_name or not sub_county_name:
                    continue

                # 1. Look up or create County (Level 2)
                county_obj = (
                    db.query(SpatialBoundary)
                    .filter(
                        SpatialBoundary.name == county_name,
                        SpatialBoundary.basin_id == parent_basin.id,
                        SpatialBoundary.level == 2,
                        SpatialBoundary.parent_id == region_id,
                    )
                    .first()
                )

                if not county_obj:
                    county_obj = SpatialBoundary(
                        name=county_name,
                        basin_id=parent_basin.id,
                        level=2,
                        parent_id=region_id,
                        centroid_geom=None,
                    )
                    db.add(county_obj)
                    db.flush()
                    logger.info(
                        "Created County (Level 2): %s in Basin %s",
                        county_name,
                        basin_code,
                    )

                # 2. Look up or create Sub-County (Level 3)
                sub_county_obj = (
                    db.query(SpatialBoundary)
                    .filter(
                        SpatialBoundary.name == sub_county_name,
                        SpatialBoundary.basin_id == parent_basin.id,
                        SpatialBoundary.level == 3,
                        SpatialBoundary.parent_id == county_obj.id,
                    )
                    .first()
                )

                if not sub_county_obj:
                    sub_county_obj = SpatialBoundary(
                        name=sub_county_name,
                        basin_id=parent_basin.id,
                        level=3,
                        parent_id=county_obj.id,
                        centroid_geom=None,
                    )
                    db.add(sub_county_obj)
                    db.flush()
                    logger.info(
                        "Created Sub-County (Level 3): %s under County %s",
                        sub_county_name,
                        county_name,
                    )

    db.commit()
    logger.info("Spatial seeding successfully completed!")
