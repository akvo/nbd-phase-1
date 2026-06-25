import logging
import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from app.database import SessionLocal
from app.models.form import Form, Question, FormNames
from app.models.spatial import Site, Wetland
from app.models.submission import Datapoint, Answer
from app.models.health_score import HealthScore
from app.models.sampling_record import SamplingRecord
from app.models.management_action import ManagementAction
from app.models.fgd_record import FgdRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_fake_submission(
    db: Session,
    form_id: int,
    site_id: uuid.UUID = None,
    basin_id: uuid.UUID = None,
    wetland_id: uuid.UUID = None,
    submitter: str = "System Test Seeder",
    status: str = "APPROVED",
    created_at: datetime = None,
    answers: dict = None,
    geo: dict = None,
) -> Datapoint:
    if created_at is None:
        created_at = datetime.utcnow()
    dp = Datapoint(
        form_id=form_id,
        name=f"fake-{submitter.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}",  # noqa
        site_id=site_id,
        basin_id=basin_id,
        wetland_id=wetland_id,
        status=status,
        submitter=submitter,
        duration=120,
        created_at=created_at,
        geo=geo,
    )
    db.add(dp)
    db.flush()

    if answers:
        for q_name, ans_payload in answers.items():
            question = (
                db.query(Question)
                .filter(Question.form_id == form_id, Question.name == q_name)
                .first()
            )
            if not question:
                continue

            if isinstance(ans_payload, dict):
                val = ans_payload.get("value")
                opts = ans_payload.get("options", [])
                text_name = ans_payload.get("name", q_name)
            else:
                val = None
                opts = []
                text_name = q_name
                if isinstance(ans_payload, list):
                    opts = ans_payload
                elif isinstance(ans_payload, (int, float)):
                    val = float(ans_payload)
                else:
                    text_name = str(ans_payload)

            ans = Answer(
                datapoint_id=dp.id,
                question_id=question.id,
                name=text_name,
                options=opts,
                value=val,
                index=0,
            )
            db.add(ans)

    return dp


def seed_fake_submissions(
    db: Session, num_submissions: int = 10, spread: float = 0.15
) -> None:
    logger.info(
        f"Starting fake submission seeding (count target: {num_submissions} per site, fallback spread: {spread})...."  # noqa
    )

    # 1. Fetch Forms
    pollution_form = (
        db.query(Form)
        .filter(Form.name == FormNames.POLLUTION_REPORTING)
        .first()
    )
    sampling_form = (
        db.query(Form).filter(Form.name == FormNames.WETLAND_SAMPLING).first()
    )
    ik_form = (
        db.query(Form)
        .filter(Form.name == FormNames.INDIGENOUS_KNOWLEDGE)
        .first()
    )
    lab_qa_form = db.query(Form).filter(Form.name == FormNames.LAB_QA).first()

    if not all([pollution_form, sampling_form, ik_form, lab_qa_form]):
        logger.error(
            "One or more forms not found in the database. Please run form seeder first."  # noqa
        )
        return

    # Delete all submissions created by the seeder across all forms
    deleted_count = (
        db.query(Datapoint)
        .filter(Datapoint.submitter == "System Test Seeder")
        .delete(synchronize_session=False)
    )
    if deleted_count > 0:
        logger.info(f"Deleted {deleted_count} existing fake submissions.")

    # 2. Fetch all sites and wetlands
    sites = db.query(Site).all()
    if not sites:
        logger.error("No sites found. Please run spatial seeder first.")
        return

    wetlands = db.query(Wetland).all()

    # Define incident templates for pollution reports
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

    health_classes_distribution = ["A", "B", "C", "D", "E"]

    # ---
    # A. Seed Sites
    # (SamplingRecords, HealthScores, Lab QA, and Pollution Reports)
    # ---
    for idx_site, site in enumerate(sites):
        # Extract coordinates
        if site.geom:
            point = to_shape(site.geom)
            coords = [point.x, point.y]
        else:
            coords = [34.5678, -1.2345]

        # Clear existing domain history for this site
        db.query(HealthScore).filter(HealthScore.site_id == site.id).delete(
            synchronize_session=False
        )
        db.query(SamplingRecord).filter(
            SamplingRecord.site_id == site.id
        ).delete(synchronize_session=False)

        selected_class = health_classes_distribution[
            idx_site % len(health_classes_distribution)
        ]
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

        # 1. Generate 5 historical records spanning 28 days back (weekly)
        now = datetime.utcnow()
        for offset_days in [28, 21, 14, 7, 0]:
            record_time = now - timedelta(days=offset_days)
            variance = random.uniform(-0.18, 0.18)
            score = max(0.05, min(0.98, base_score + variance))

            # HealthScore record
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

            # Cycle through water levels to prevent flat lines
            w_levels = ["MEDIUM", "HIGH", "LOW", "MEDIUM", "HIGH"]
            w_idx = {28: 0, 21: 1, 14: 2, 7: 3, 0: 4}[offset_days]
            w_level = w_levels[w_idx]

            # SamplingRecord parameters
            # conforming to SDD ranges per health class
            if selected_class == "A":
                ph = 7.2 + random.uniform(-0.3, 0.3)
                temp = 22.0 + random.uniform(-1.0, 1.0)
                do = 8.0 + random.uniform(-0.5, 0.5)
                macrophytes = max(0.0, 2.0 + random.uniform(-1.0, 1.0))
                cpue = 15.0 + random.uniform(-2.0, 2.0)
            elif selected_class == "B":
                ph = 7.5 + random.uniform(-0.5, 0.5)
                temp = 23.0 + random.uniform(-1.5, 1.5)
                do = 7.0 + random.uniform(-0.8, 0.8)
                macrophytes = max(0.0, 10.0 + random.uniform(-3.0, 3.0))
                cpue = 12.0 + random.uniform(-2.0, 2.0)
            elif selected_class == "C":
                ph = 6.5 + random.uniform(-0.8, 0.8)
                temp = 25.0 + random.uniform(-2.0, 2.0)
                do = 5.5 + random.uniform(-1.0, 1.0)
                macrophytes = 25.0 + random.uniform(-5.0, 5.0)
                cpue = 8.0 + random.uniform(-1.5, 1.5)
            elif selected_class == "D":
                ph = 5.8 + random.uniform(-1.0, 1.0)
                temp = 26.0 + random.uniform(-3.0, 3.0)
                do = 3.5 + random.uniform(-1.2, 1.2)
                macrophytes = 55.0 + random.uniform(-10.0, 10.0)
                cpue = 4.0 + random.uniform(-1.0, 1.0)
            else:  # E
                ph = 4.5 + random.uniform(-1.5, 1.5)
                temp = 28.0 + random.uniform(-4.0, 4.0)
                do = 1.5 + random.uniform(-1.0, 1.0)
                macrophytes = 85.0 + random.uniform(-10.0, 10.0)
                cpue = 1.0 + random.uniform(-0.5, 0.5)

            sampling_rec = SamplingRecord(
                site_id=site.id,
                ph_value=max(2.0, min(10.0, ph)),
                temp_value=max(5.0, min(50.0, temp)),
                do_value=max(0.5, min(35.0, do)),
                invasive_macrophytes=max(0.0, min(100.0, macrophytes)),
                cpue_value=max(0.0, cpue),
                water_level=w_level,
                sampled_at=record_time,
            )
            db.add(sampling_rec)
            db.flush()

            # Seed APPROVED Datapoint matching this SamplingRecord
            create_fake_submission(
                db=db,
                form_id=sampling_form.id,
                site_id=site.id,
                submitter="System Test Seeder",
                status="APPROVED",
                created_at=record_time,
                answers={
                    "site_id": str(site.id),
                    "sampling_id": f"SMP-{site.code}-{offset_days}",
                    "ph": float(sampling_rec.ph_value),
                    "temp": float(sampling_rec.temp_value),
                    "do": float(sampling_rec.do_value),
                    "invasive_percent": float(
                        sampling_rec.invasive_macrophytes
                    ),
                    "target_species": "Tilapia",
                    "total_catch": float(sampling_rec.cpue_value * 2),
                    "fishing_effort": 2.0,
                    "water_level": [w_level.lower()],
                },
            )

        # 2. Seed PENDING Monthly Sampling Report
        create_fake_submission(
            db=db,
            form_id=sampling_form.id,
            site_id=site.id,
            submitter="System Test Seeder",
            status="PENDING",
            created_at=now,
            answers={
                "site_id": str(site.id),
                "sampling_id": f"SMP-{site.code}-PENDING",
                "ph": 7.4,
                "temp": 24.5,
                "do": 6.8,
                "invasive_percent": 12.0,
                "target_species": "Tilapia",
                "total_catch": 30.0,
                "fishing_effort": 3.0,
                "water_level": ["medium"],
            },
        )

        # 3. Seed APPROVED Lab QA Reports (2 per site)
        for lab_idx in range(2):
            create_fake_submission(
                db=db,
                form_id=lab_qa_form.id,
                site_id=site.id,
                submitter="System Test Seeder",
                status="APPROVED",
                created_at=now - timedelta(days=15 * (lab_idx + 1)),
                answers={
                    "site_id": str(site.id),
                    "lab_ph": 7.0 + random.uniform(-0.5, 0.5),
                    "lab_temperature": 23.0 + random.uniform(-2.0, 2.0),
                    "lab_dissolved_oxygen": 6.5 + random.uniform(-1.0, 1.0),
                    "bod": 2.0 + random.uniform(-0.5, 0.5),
                    "orthophosphate": 0.05 + random.uniform(-0.02, 0.02),
                    "nitrate": 1.2 + random.uniform(-0.3, 0.3),
                    "mercury": 0.001,
                    "heavy_metals": "None detected",
                    "total_nitrogen": 1.5,
                    "total_phosphorus": 0.08,
                },
            )

        # 4. Seed PENDING Lab QA Report (1 per site)
        create_fake_submission(
            db=db,
            form_id=lab_qa_form.id,
            site_id=site.id,
            submitter="System Test Seeder",
            status="PENDING",
            created_at=now,
            answers={
                "site_id": str(site.id),
                "lab_ph": 7.1,
                "lab_temperature": 24.0,
                "lab_dissolved_oxygen": 6.8,
                "bod": 1.8,
                "orthophosphate": 0.04,
                "nitrate": 1.0,
                "mercury": 0.0,
                "heavy_metals": "None",
                "total_nitrogen": 1.4,
                "total_phosphorus": 0.07,
            },
        )

        # 5. Seed Management Actions templates for
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

        # Determine spatial boundaries from parent wetland
        wetland_bounds = None
        if site.wetland and site.wetland.geom:
            try:
                wetland_shape = to_shape(site.wetland.geom)
                wetland_bounds = wetland_shape.bounds
            except Exception as e:
                logger.warning(
                    f"Could not parse wetland geometry for site {site.name}: {e}"  # noqa
                )

        # 6. Seed APPROVED Pollution reports (EAV Submissions)
        for idx in range(num_submissions):
            template = incident_templates[idx % len(incident_templates)]
            if wetland_bounds:
                min_lon, min_lat, max_lon, max_lat = wetland_bounds
                offset_lon = random.uniform(min_lon, max_lon)
                offset_lat = random.uniform(min_lat, max_lat)
            else:
                offset_lon = coords[0] + random.uniform(-spread, spread)
                offset_lat = coords[1] + random.uniform(-spread, spread)

            create_fake_submission(
                db=db,
                form_id=pollution_form.id,
                site_id=site.id,
                submitter="System Test Seeder",
                status="APPROVED",
                created_at=now - timedelta(days=idx),
                geo={"type": "Point", "coordinates": [offset_lon, offset_lat]},
                answers={
                    "incident_type": {
                        "value": float(template["type_value"]),
                        "options": [template["type_value"]],
                    },
                    "incident_description": {
                        "name": f"{template['desc']} Observed near {site.name}.",  # noqa
                        "value": None,
                        "options": [],
                    },
                    "location_id": "84318c6e-b3f4-419b-8647-7977a4ee709a",  # Mock sub-county UUID # noqa
                },
            )

        # 7. Seed PENDING Pollution report (1 per site)
        create_fake_submission(
            db=db,
            form_id=pollution_form.id,
            site_id=site.id,
            submitter="System Test Seeder",
            status="PENDING",
            created_at=now,
            geo={"type": "Point", "coordinates": [coords[0], coords[1]]},
            answers={
                "incident_type": {
                    "value": 1.0,
                    "options": [1],
                },
                "incident_description": {
                    "name": f"Pending report: Water colour is slightly darker than usual at {site.name}.",  # noqa
                    "value": None,
                    "options": [],
                },
                "location_id": "84318c6e-b3f4-419b-8647-7977a4ee709a",
            },
        )

    # ---
    # B. Seed Wetlands
    # (FGD / Indigenous Knowledge Submissions & FgdRecords)
    # ---
    for wetland in wetlands:
        # Clear existing FGD records
        db.query(FgdRecord).filter(FgdRecord.wetland_id == wetland.id).delete(
            synchronize_session=False
        )

        # 1. Seed 5 APPROVED FGD Sessions & FgdRecords
        for idx in range(5):
            record_time = now - timedelta(days=8 * idx)

            # Cycle trends to make them unique
            fish_trends = ["Same", "Slight", "Moderate", "Severe"]
            clarity_trends = ["Same", "Somewhat Worse", "Much Worse"]
            vegetation_trends = ["Same", "Partial Loss", "Severe Loss"]

            fish_t = fish_trends[idx % len(fish_trends)]
            clarity_t = clarity_trends[idx % len(clarity_trends)]
            veg_t = vegetation_trends[idx % len(vegetation_trends)]

            # Save domain record directly
            fgd_rec = FgdRecord(
                wetland_id=wetland.id,
                fish_abundance=fish_t,
                water_clarity=clarity_t,
                vegetation_cover=veg_t,
                conducted_at=record_time,
            )
            db.add(fgd_rec)
            db.flush()

            # Save FGD approved EAV Datapoint
            create_fake_submission(
                db=db,
                form_id=ik_form.id,
                wetland_id=wetland.id,
                submitter="System Test Seeder",
                status="APPROVED",
                created_at=record_time,
                answers={
                    "wetland_id": str(wetland.id),
                    "dependent_population": {
                        "value": 2.0,
                        "options": [2],
                    },
                    "wetland_uses": f"FGD session {idx + 1}: Domestic use, livestock watering, small irrigation.",  # noqa
                    "major_threats": "Siltation, overgrazing, agricultural expansion.",  # noqa
                    "land_use": "Subsistence farming",
                    "area": "450 sq km",
                    "fish_abundance_change": {
                        "name": fish_t,
                        "options": [fish_t],
                    },
                    "water_clarity_change": {
                        "name": clarity_t,
                        "options": [clarity_t],
                    },
                    "vegetation_cover_change": {
                        "name": veg_t,
                        "options": [veg_t],
                    },
                    "biodiversity_change": {
                        "value": 0.6,
                        "options": [0.6],
                    },
                    "floods_regularity_change": {
                        "name": "Same",
                        "options": ["Same"],
                    },
                },
            )

        # 2. Seed PENDING FGD Session Report
        create_fake_submission(
            db=db,
            form_id=ik_form.id,
            wetland_id=wetland.id,
            submitter="System Test Seeder",
            status="PENDING",
            created_at=now,
            answers={
                "wetland_id": str(wetland.id),
                "dependent_population": {
                    "value": 3.0,
                    "options": [3],
                },
                "wetland_uses": "Livestock watering and brick making.",
                "major_threats": "Overgrazing and sand harvesting.",
                "land_use": "Pastoralism",
                "area": "450 sq km",
                "fish_abundance_change": {
                    "name": "Slight",
                    "options": ["Slight"],
                },
                "water_clarity_change": {
                    "name": "Somewhat Worse",
                    "options": ["Somewhat Worse"],
                },
                "vegetation_cover_change": {
                    "name": "Partial Loss",
                    "options": ["Partial Loss"],
                },
                "biodiversity_change": {
                    "value": 0.3,
                    "options": [0.3],
                },
                "floods_regularity_change": {
                    "name": "Same",
                    "options": ["Same"],
                },
            },
        )

    db.commit()
    logger.info("Fake submission seeding completed successfully!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed fake submissions.")
    parser.add_argument(
        "--count",
        type=int,
        default=10,
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
