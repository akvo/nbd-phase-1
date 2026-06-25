import logging
import random
from datetime import datetime
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from app.database import SessionLocal
from app.models.form import Form, Question
from app.models.spatial import Site
from app.models.submission import Datapoint, Answer
from app.models.health_score import HealthScore
from app.models.sampling_record import SamplingRecord
from app.models.management_action import ManagementAction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_fake_submissions(
    db: Session, num_submissions: int = 3, spread: float = 0.15
) -> None:
    logger.info(
        f"Starting fake submission seeding (count target: {num_submissions} per site, fallback spread: {spread})..."  # noqa
    )

    # 1. Fetch the Pollution Reporting Form
    form = (
        db.query(Form).filter(Form.name == "Pollution Reporting Form").first()
    )
    if not form:
        logger.error(
            "Pollution Reporting Form not found in database! Please run form seeder first."  # noqa
        )
        return

    # Fetch the incident_type question
    question_type = (
        db.query(Question)
        .filter(Question.form_id == form.id, Question.name == "incident_type")
        .first()
    )

    if not question_type:
        logger.error(
            "incident_type question not found for Pollution Reporting Form."
        )
        return

    # Fetch description/details question
    question_desc = (
        db.query(Question)
        .filter(
            Question.form_id == form.id,
            Question.name == "incident_description",
        )
        .first()
    )

    # Fetch media_attachment question to use
    # as fallback to satisfy foreign key constraints
    question_media = (
        db.query(Question)
        .filter(
            Question.form_id == form.id,
            Question.name == "media_attachment",
        )
        .first()
    )

    # 2. Fetch all sites
    sites = db.query(Site).all()
    if not sites:
        logger.error("No sites found. Please run spatial seeder first.")
        return

    # Delete existing fake submissions to
    # ensure we seed exactly the requested count
    deleted_count = (
        db.query(Datapoint)
        .filter(
            Datapoint.form_id == form.id,
            Datapoint.submitter == "System Test Seeder",
        )
        .delete(synchronize_session=False)
    )
    if deleted_count > 0:
        logger.info(f"Deleted {deleted_count} existing fake submissions.")

    # Define the three templates (Critical, Elevated, Moderate)
    incident_templates = [
        {
            "severity": "Critical",
            "type_value": 3,
            "type_label": "Fish or animal kills",
            "desc": "Observed multiple dead fish floating near the river banks. Water looks extremely dark and stagnant.",  # noqa
        },
        {
            "severity": "Elevated",
            "type_value": 2,
            "type_label": "Smell (bad odour)",
            "desc": "Strong chemical odor detected coming from the upstream channel. Locals reporting headaches.",  # noqa
        },
        {
            "severity": "Moderate",
            "type_value": 4,
            "type_label": "Storm event",
            "desc": "Heavy runoff and turbidity following the recent seasonal storm. Debris visible.",  # noqa
        },
    ]

    # Pre-defined management actions templates
    actions_templates = {
        "GREEN": [
            (
                "Routine Patrols",
                "Conduct standard monthly water sampling and visual checks.",
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
            ),
            (
                "Riparian Re-vegetation",
                "Target plantings of indigenous species along degraded river banks.",  # noqa
            ),
        ],
        "RED": [
            (
                "Report Discharge",
                "Log effluent discharge with local Ministry of Environment and Water units.",  # noqa
            ),
            (
                "Interceptor STPs",
                "Direct untreated sewage to local treatment plants to halt degradation.",  # noqa
            ),
            (
                "Buffer Enactment",
                "Stop agricultural encroachment using local buffer regulations under EMCA.",  # noqa
            ),
            (
                "Mesh Controls",
                "Direct fishermen to larger gillnet sizes to protect breeding fish stocks.",  # noqa
            ),
        ],
    }

    # Deterministic health classes to
    # distribute across sites to showcase all possibilities (A-E)
    health_classes_distribution = ["A", "B", "C", "D", "E"]

    for idx_site, site in enumerate(sites):
        # Extract coordinates using to_shape
        if site.geom:
            point = to_shape(site.geom)
            coords = [point.x, point.y]
        else:
            coords = [34.5678, -1.2345]

        # Seed HealthScore and SamplingRecord history (past 30 days)
        from datetime import timedelta

        # Clear existing history for this site first to prevent duplicate runs
        db.query(HealthScore).filter(HealthScore.site_id == site.id).delete(
            synchronize_session=False
        )
        db.query(SamplingRecord).filter(
            SamplingRecord.site_id == site.id
        ).delete(synchronize_session=False)

        selected_class = health_classes_distribution[
            idx_site % len(health_classes_distribution)
        ]
        # Map base score ranges based on class
        if selected_class == "A":
            base_score = 0.92
        elif selected_class == "B":
            base_score = 0.74
        elif selected_class == "C":
            base_score = 0.52
        elif selected_class == "D":
            base_score = 0.31
        else:
            base_score = 0.12

        # Generate 5 historical records spanning 30 days back
        now = datetime.utcnow()
        for offset_days in [30, 22, 15, 8, 0]:
            record_time = now - timedelta(days=offset_days)
            # Add distinct variance to scores to display line graphs clearly
            variance = random.uniform(-0.18, 0.18)
            score = max(0.05, min(0.98, base_score + variance))

            # Seed HealthScore history
            health_score = HealthScore(
                site_id=site.id,
                wqi_score=score,
                composite_score=score,
                ik_signal_value=score,
                adjusted_score=score,
                health_class=selected_class,
                calculated_at=record_time,
            )
            db.add(health_score)

            # Seed SamplingRecord history
            # Map parameters dynamically to database fields:
            # ph_value (2.0 - 10.0), temp_value (5.0 - 50.0),
            # do_value (0.5 - 35.0)
            sampling_rec = SamplingRecord(
                site_id=site.id,
                ph_value=max(4.0, min(9.0, 7.0 + random.uniform(-1.5, 1.5))),
                temp_value=max(
                    15.0, min(35.0, 24.0 + random.uniform(-6.0, 6.0))
                ),
                do_value=max(3.0, min(12.0, 6.5 + random.uniform(-2.5, 2.5))),
                invasive_macrophytes=max(
                    0.0, min(100.0, 25.0 + random.uniform(-20.0, 20.0))
                ),
                water_level=random.choice(["HIGH", "MEDIUM", "LOW"]),
                sampled_at=record_time,
            )
            db.add(sampling_rec)

        logger.info(
            f"Seeded 5 historical scores & samplings (class {selected_class}) "
            f"for site: {site.name}"
        )

        # B. Seed Management Actions templates for
        # GREEN, YELLOW, RED status colors
        for color, actions in actions_templates.items():
            for short_label, description_text in actions:
                existing_action = (
                    db.query(ManagementAction)
                    .filter(
                        ManagementAction.site_id == site.id,
                        ManagementAction.status_color == color,
                        ManagementAction.short_label == short_label,
                    )
                    .first()
                )

                if not existing_action:
                    m_action = ManagementAction(
                        site_id=site.id,
                        status_color=color,
                        short_label=short_label,
                        description_text=description_text,
                    )
                    db.add(m_action)
                    logger.info(
                        f"Seeded ManagementAction ({color}) '{short_label}' for site: {site.name}"  # noqa
                    )

        # Determine spatial boundaries from parent wetland if available
        wetland_bounds = None
        if site.wetland and site.wetland.geom:
            try:
                wetland_shape = to_shape(site.wetland.geom)
                wetland_bounds = (
                    wetland_shape.bounds
                )  # (minx, miny, maxx, maxy)
            except Exception as e:
                logger.warning(
                    f"Could not parse wetland geometry for site {site.name}: {e}"  # noqa
                )

        # C. Seed Pollution reports
        # (approved Datapoints) with random coordinates offset
        for idx in range(num_submissions):
            template = incident_templates[idx % len(incident_templates)]
            # Scatter coordinates within wetland boundary if available,
            # else fallback to radius spread
            if wetland_bounds:
                min_lon, min_lat, max_lon, max_lat = wetland_bounds
                offset_lon = random.uniform(min_lon, max_lon)
                offset_lat = random.uniform(min_lat, max_lat)
            else:
                offset_lon = coords[0] + random.uniform(-spread, spread)
                offset_lat = coords[1] + random.uniform(-spread, spread)

            dp = Datapoint(
                form_id=form.id,
                name=f"fake-reporter-{site.code}-{idx}",
                site_id=site.id,
                geo={"type": "Point", "coordinates": [offset_lon, offset_lat]},
                status="APPROVED",
                submitter="System Test Seeder",
                duration=120,
            )
            db.add(dp)
            db.flush()

            # Add incident_type answer
            ans_type = Answer(
                datapoint_id=dp.id,
                question_id=question_type.id,
                name="incident_type",
                options=[template["type_value"]],
                value=float(template["type_value"]),
                index=0,
            )
            db.add(ans_type)

            # Add incident_description answer using media_attachment to satisfy FK constraints  # noqa
            ans_desc = Answer(
                datapoint_id=dp.id,
                question_id=(
                    question_desc.id
                    if question_desc
                    else (
                        question_media.id
                        if question_media
                        else question_type.id
                    )
                ),
                name="incident_description",
                options=[],
                value=None,
                index=0 if (question_desc or question_media) else 1,
            )
            # Store the description text in 'name'
            # column where text answers reside
            ans_desc.name = template["desc"]
            db.add(ans_desc)

            logger.info(
                f"Seeded {template['severity']} incident for site: {site.name} at [{offset_lat:.4f}, {offset_lon:.4f}]"  # noqa
            )

    db.commit()
    logger.info("Fake submission seeding completed successfully!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed fake submissions.")
    parser.add_argument(
        "--count",
        type=int,
        default=3,
        help="Number of submissions per site to seed",
    )
    parser.add_argument(
        "--spread",
        type=float,
        default=0.15,
        help="Fallback random coordinate offset range (in degrees) around the site center",  # noqa
    )
    args = parser.parse_args()

    dbSession = SessionLocal()
    try:
        seed_fake_submissions(
            dbSession, num_submissions=args.count, spread=args.spread
        )
    finally:
        dbSession.close()
