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
from app.models.management_action import ManagementAction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_fake_submissions(db: Session, num_submissions: int = 3) -> None:
    logger.info(
        f"Starting fake submission seeding (count target: {num_submissions} per site)..."  # noqa
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

        # A. Seed HealthScore to show the correct A-E status on dashboard
        existing_health = (
            db.query(HealthScore)
            .filter(HealthScore.site_id == site.id)
            .first()
        )

        if not existing_health:
            selected_class = health_classes_distribution[
                idx_site % len(health_classes_distribution)
            ]
            # Map score ranges based on class
            if selected_class == "A":
                score = 0.92
            elif selected_class == "B":
                score = 0.74
            elif selected_class == "C":
                score = 0.52
            elif selected_class == "D":
                score = 0.31
            else:
                score = 0.12

            health_score = HealthScore(
                site_id=site.id,
                wqi_score=score,
                composite_score=score,
                ik_signal_value=score,
                adjusted_score=score,
                health_class=selected_class,
                calculated_at=datetime.utcnow(),
            )
            db.add(health_score)
            logger.info(
                f"Seeded HealthScore class {selected_class} for site: {site.name}"  # noqa
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

        # C. Seed Pollution reports
        # (approved Datapoints) with random coordinates offset
        for idx in range(num_submissions):
            template = incident_templates[idx % len(incident_templates)]
            # Create a randomized offset
            # coordinate so markers do not stack on top of each other
            offset_lon = coords[0] + random.uniform(-0.04, 0.04)
            offset_lat = coords[1] + random.uniform(-0.04, 0.04)

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
    args = parser.parse_args()

    dbSession = SessionLocal()
    try:
        seed_fake_submissions(dbSession, num_submissions=args.count)
    finally:
        dbSession.close()
