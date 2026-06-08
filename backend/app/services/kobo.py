import os
import uuid
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
import httpx
from sqlalchemy.orm import Session
from app.models.form import Form, Question
from app.models.spatial import Basin
from app.models.submission import Datapoint, Answer
from app.models.sync_watermark import SyncWatermark

logger = logging.getLogger(__name__)


class KoboService:
    def __init__(self):
        self.api_url = os.getenv(
            "KOBOTOOLBOX_API_URL", "https://eu.kobotoolbox.org"
        ).rstrip("/")
        self.api_token = os.getenv("KOBOTOOLBOX_API_TOKEN")
        self.headers = {}
        if self.api_token:
            self.headers["Authorization"] = f"Token {self.api_token}"

    def get_forms(self) -> List[Dict[str, Any]]:
        url = f"{self.api_url}/api/v2/assets.json"
        with httpx.Client() as client:
            response = client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])

    def get_submissions(
        self, form_id: str, since_timestamp: str | None = None
    ) -> List[Dict[str, Any]]:
        url = f"{self.api_url}/api/v2/assets/{form_id}/data.json"
        params = {}
        if since_timestamp:
            import json

            params["query"] = json.dumps(
                {"_submission_time": {"$gt": since_timestamp}}
            )
        with httpx.Client() as client:
            response = client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])


def parse_kobo_timestamp(ts_str: str | None) -> datetime:
    if not ts_str:
        return datetime.utcnow()
    cleaned = ts_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except ValueError:
        return datetime.utcnow()


def sync_kobo_submissions(db: Session) -> Dict[str, Any]:
    logger.info("Starting KoboToolbox submissions sync...")
    service = KoboService()
    sync_results = {"processed_forms": 0, "ingested_records": 0, "errors": []}

    try:
        forms = service.get_forms()
    except Exception as e:
        logger.error(f"Failed to fetch forms list from KoboToolbox: {e}")
        sync_results["errors"].append(str(e))
        return sync_results

    # Get a default polymorphic anchor
    default_basin = db.query(Basin).first()
    if not default_basin:
        logger.error(
            "No Basin found in database to act as polymorphic anchor."
        )
        sync_results["errors"].append("No Basin found for polymorphic anchor.")
        return sync_results

    for form in forms:
        form_name = form.get("name")
        uid = form.get("uid")
        if not form_name or not uid:
            continue

        # Match by kobo_asset_id first, then fallback to form name
        db_form = (
            db.query(Form)
            .filter((Form.kobo_asset_id == uid) | (Form.name == form_name))
            .first()
        )
        if not db_form:
            continue

        # If matched by name but kobo_asset_id is not set, update it
        if not db_form.kobo_asset_id:
            db_form.kobo_asset_id = uid
            db.commit()

        logger.info(
            f"Syncing submissions for form: {form_name} (Kobo UID: {uid})"
        )
        sync_results["processed_forms"] += 1

        # Check watermark
        watermark = (
            db.query(SyncWatermark)
            .filter(
                SyncWatermark.source_system == "kobotoolbox",
                SyncWatermark.form_id == uid,
            )
            .first()
        )

        if watermark:
            since_ts = watermark.last_sync_time.isoformat() + "Z"
        else:
            # Fallback: last 60 minutes
            since_ts = (
                datetime.utcnow() - timedelta(minutes=60)
            ).isoformat() + "Z"

        try:
            submissions = service.get_submissions(
                uid, since_timestamp=since_ts
            )
        except Exception as e:
            logger.error(
                f"Failed to fetch submissions for form {form_name}: {e}"
            )
            sync_results["errors"].append(f"Form {form_name}: {e}")
            continue

        latest_submission_time = None

        for sub in submissions:
            sub_uuid_str = sub.get("_uuid")
            sub_time_str = sub.get("_submission_time")

            if not sub_uuid_str:
                continue

            try:
                sub_uuid = uuid.UUID(sub_uuid_str)
            except ValueError:
                continue

            # Check idempotency
            exists = (
                db.query(Datapoint).filter(Datapoint.uuid == sub_uuid).first()
            )
            if exists:
                logger.info(f"Submission {sub_uuid} already exists. Skipping.")
                continue

            sub_time = parse_kobo_timestamp(sub_time_str)

            if (
                latest_submission_time is None
                or sub_time > latest_submission_time
            ):
                latest_submission_time = sub_time

            # Create Datapoint
            datapoint = Datapoint(
                uuid=sub_uuid,
                form_id=db_form.id,
                published_version_id=db_form.active_version_id,
                submitter=sub.get("_submitted_by", "KoboToolbox"),
                created_at=sub_time,
                basin_id=default_basin.id,
                status="PENDING",
                geo=sub.get("_geolocation"),
            )
            db.add(datapoint)
            db.flush()

            # Map answers dynamically
            for question in db_form.questions:
                val = sub.get(question.name) or sub.get(question.id)
                if val is not None:
                    name_val = None
                    float_val = None
                    options_val = None

                    if question.type == "number":
                        try:
                            float_val = float(val)
                        except ValueError:
                            name_val = str(val)
                    elif question.type in ("option", "multiple_option"):
                        if isinstance(val, list):
                            options_val = val
                        else:
                            options_val = [str(val)]
                    else:
                        name_val = str(val)

                    answer = Answer(
                        datapoint_id=datapoint.id,
                        question_id=question.id,
                        name=name_val,
                        value=float_val,
                        options=options_val,
                        created_at=sub_time,
                    )
                    db.add(answer)

            sync_results["ingested_records"] += 1

        # Update watermark
        if latest_submission_time:
            if not watermark:
                watermark = SyncWatermark(
                    source_system="kobotoolbox",
                    form_id=uid,
                    last_sync_time=latest_submission_time,
                )
                db.add(watermark)
            else:
                watermark.last_sync_time = latest_submission_time
            db.commit()
            logger.info(
                f"Updated Kobo sync watermark for {form_name} to {latest_submission_time}"
            )

    logger.info("KoboToolbox sync finished.")
    return sync_results
