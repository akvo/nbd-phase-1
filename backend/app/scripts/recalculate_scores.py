"""Recalculate Health Scores, Sampling Records, and FGD Records.

This script replays all approved submissions in chronological order to
recalculate live scores, parameters, and fuzzy logic adjustments.
"""

import sys
import argparse
import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import SessionLocal
from app.models.spatial import Site, Wetland, Basin
from app.models.form import Form, FormType
from app.models.submission import Datapoint, SubmissionStatus
from app.models.sampling_record import SamplingRecord
from app.models.health_score import HealthScore
from app.models.fgd_record import FgdRecord
from app.services.scoring import get_handler
from app.services.reconciliation import reconcile_lab_datapoint

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def recalculate_scores(
    db: Session,
    site_code: Optional[str] = None,
    basin_code: Optional[str] = None,
) -> dict:
    """Recomputes all derived scores for approved submissions."""
    logger.info(
        "Starting score recalculation (site_code=%s, basin_code=%s)...",
        site_code,
        basin_code,
    )

    # 1. Determine target sites and wetlands
    site_query = db.query(Site)
    if site_code:
        site_query = site_query.filter(
            (func.lower(Site.code) == site_code.strip().lower())
            | (func.lower(Site.name) == site_code.strip().lower())
        )
    if basin_code:
        site_query = (
            site_query.join(Wetland, Site.wetland_id == Wetland.id)
            .join(Basin, Wetland.basin_id == Basin.id)
            .filter(
                (func.lower(Basin.code) == basin_code.strip().lower())
                | (func.lower(Basin.name) == basin_code.strip().lower())
            )
        )

    target_sites = site_query.all()
    target_site_ids = [s.id for s in target_sites]
    logger.info(
        "Found %d target site(s) for recalculation.", len(target_sites)
    )

    if target_sites:
        target_wetland_ids = list(
            {s.wetland_id for s in target_sites if s.wetland_id}
        )
    else:
        target_wetland_ids = [w.id for w in db.query(Wetland).all()]

    # 2. Clear existing derived records for target scope
    if target_site_ids:
        deleted_scores = (
            db.query(HealthScore)
            .filter(HealthScore.site_id.in_(target_site_ids))
            .delete(synchronize_session=False)
        )
        deleted_samplings = (
            db.query(SamplingRecord)
            .filter(SamplingRecord.site_id.in_(target_site_ids))
            .delete(synchronize_session=False)
        )
    else:
        deleted_scores = db.query(HealthScore).delete(
            synchronize_session=False
        )
        deleted_samplings = db.query(SamplingRecord).delete(
            synchronize_session=False
        )

    if target_wetland_ids:
        deleted_fgds = (
            db.query(FgdRecord)
            .filter(FgdRecord.wetland_id.in_(target_wetland_ids))
            .delete(synchronize_session=False)
        )
    else:
        deleted_fgds = db.query(FgdRecord).delete(synchronize_session=False)

    logger.info(
        "Purged derived history: %d HealthScores, "
        "%d SamplingRecords, %d FgdRecords.",
        deleted_scores,
        deleted_samplings,
        deleted_fgds,
    )
    db.flush()

    # 3. Process Form 3 (Indigenous Knowledge) in chronological order
    ik_handler = get_handler(FormType.INDIGENOUS_KNOWLEDGE)
    ik_dps_query = (
        db.query(Datapoint)
        .join(Form, Datapoint.form_id == Form.id)
        .filter(
            Form.type == FormType.INDIGENOUS_KNOWLEDGE.value,
            Datapoint.status == SubmissionStatus.APPROVED,
        )
    )
    if target_wetland_ids:
        ik_dps_query = ik_dps_query.filter(
            Datapoint.wetland_id.in_(target_wetland_ids)
        )

    ik_dps = ik_dps_query.order_by(Datapoint.created_at.asc()).all()
    processed_ik = 0
    if ik_handler:
        for dp in ik_dps:
            try:
                ik_handler.score_submission(db, dp)
                processed_ik += 1
            except Exception as e:
                logger.error(
                    "Error recalculating IK submission %d: %s", dp.id, e
                )
    logger.info(
        "Processed %d Indigenous Knowledge submission(s).",
        processed_ik,
    )
    db.flush()

    # 4. Process Form 2 (Monthly Sampling) in chronological order
    sampling_handler = get_handler(FormType.CITIZEN_SCIENTIST)
    sampling_dps_query = (
        db.query(Datapoint)
        .join(Form, Datapoint.form_id == Form.id)
        .filter(
            Form.type == FormType.CITIZEN_SCIENTIST.value,
            Datapoint.status == SubmissionStatus.APPROVED,
        )
    )
    if target_site_ids:
        sampling_dps_query = sampling_dps_query.filter(
            Datapoint.site_id.in_(target_site_ids)
        )

    sampling_dps = sampling_dps_query.order_by(
        Datapoint.created_at.asc()
    ).all()
    processed_samplings = 0
    if sampling_handler:
        for dp in sampling_dps:
            try:
                sampling_handler.score_submission(db, dp)
                processed_samplings += 1
            except Exception as e:
                logger.error(
                    "Error recalculating Sampling submission %d: %s", dp.id, e
                )
    logger.info(
        "Processed %d Monthly Sampling submission(s).", processed_samplings
    )
    db.flush()

    # 5. Run Lab QA auto-reconciliation for Form 4 submissions
    lab_dps_query = (
        db.query(Datapoint)
        .join(Form, Datapoint.form_id == Form.id)
        .filter(
            Form.type == FormType.LAB_QA.value,
            Datapoint.status == SubmissionStatus.APPROVED,
        )
    )
    if target_site_ids:
        lab_dps_query = lab_dps_query.filter(
            Datapoint.site_id.in_(target_site_ids)
        )

    lab_dps = lab_dps_query.all()
    processed_lab = 0
    for lab_dp in lab_dps:
        try:
            reconcile_lab_datapoint(db, lab_dp.id)
            processed_lab += 1
        except Exception as e:
            db.rollback()
            logger.warning(
                "Lab reconciliation warning for report %d: %s", lab_dp.id, e
            )

    logger.info(
        "Completed Lab QA reconciliation for %d report(s).", processed_lab
    )

    db.commit()
    logger.info("Score recalculation successfully completed!")

    return {
        "processed_ik": processed_ik,
        "processed_samplings": processed_samplings,
        "processed_lab": processed_lab,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Recalculate NBD health scores and sampling records."
    )
    parser.add_argument(
        "--site-id",
        type=str,
        default=None,
        help=(
            "Optional site code (e.g. NBD-SIO-001) or site name "
            "to filter recalculation."
        ),
    )
    parser.add_argument(
        "--basin",
        type=str,
        default=None,
        help=(
            "Optional basin code (e.g. SIO_SITEKO or MARA) "
            "to filter recalculation."
        ),
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        recalculate_scores(db, site_code=args.site_id, basin_code=args.basin)
    except Exception as e:
        logger.error("Failed to recalculate scores: %s", e)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
