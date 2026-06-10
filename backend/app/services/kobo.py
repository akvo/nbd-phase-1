import os
import uuid
import logging
from typing import List, Dict, Any
from datetime import datetime
import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.form import Form
from app.models.spatial import Basin, Site
from app.models.submission import Datapoint, Answer
from app.models.sync_watermark import SyncWatermark
from app.models.dead_letter import DeadLetter
from app.mail import EmailService
from app.services.storage import StorageService, build_blob_path

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
        self, form_id: str, since_timestamp: str | datetime | None = None
    ) -> List[Dict[str, Any]]:
        url = f"{self.api_url}/api/v2/assets/{form_id}/data.json"
        params = {}
        if since_timestamp:
            if isinstance(since_timestamp, str):
                dt = parse_kobo_timestamp(since_timestamp)
            else:
                dt = since_timestamp
            since_str = dt.strftime("%Y-%m-%dT%H:%M:%S+0000")
            params["query"] = f'{{"_submission_time":{{"$gt":"{since_str}"}}}}'
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
        # (lowercase & stripped)
        normalized_name = form_name.strip().lower()
        db_form = (
            db.query(Form)
            .filter(
                (Form.kobo_asset_id == uid)
                | (func.lower(func.trim(Form.name)) == normalized_name)
            )
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
            since_ts = watermark.last_sync_time
        else:
            # Initial sync: fetch all submissions
            since_ts = None

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

        sync_failures = []

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

            try:
                with db.begin_nested():
                    # Determine spatial anchor
                    # (site_id, basin_id, or wetland_id)
                    selected_site_id = None
                    selected_basin_id = None
                    geo_json = None

                    # 1. Look for explicit site question
                    for question in db_form.questions:
                        if question.name in (
                            "site",
                            "site_id",
                            "site_code",
                            "location_id",
                        ):
                            val = sub.get(question.name)
                            if val is None:
                                suffix = f"/{question.name}"
                                for key, k_val in sub.items():
                                    if key.endswith(suffix):
                                        val = k_val
                                        break
                            if val is None:
                                val = sub.get(str(question.id))

                            if val is not None:
                                site_obj = (
                                    db.query(Site)
                                    .filter(
                                        (Site.code == str(val))
                                        | (Site.name == str(val))
                                    )
                                    .first()
                                )
                                if site_obj:
                                    selected_site_id = site_obj.id
                                    break

                    # 2. If no site is explicitly matched,
                    # check _geolocation for containing basin
                    geolocation = sub.get("_geolocation")
                    if (
                        not selected_site_id
                        and isinstance(geolocation, list)
                        and len(geolocation) >= 2
                    ):
                        lat, lon = geolocation[0], geolocation[1]
                        point = func.ST_SetSRID(
                            func.ST_MakePoint(lon, lat), 4326
                        )
                        containing_basin = (
                            db.query(Basin)
                            .filter(func.ST_Contains(Basin.geom, point))
                            .first()
                        )
                        if containing_basin:
                            selected_basin_id = containing_basin.id
                            geo_json = {
                                "type": "Point",
                                "coordinates": [lon, lat],
                            }

                    # 3. Fallback to default basin
                    if not selected_site_id and not selected_basin_id:
                        selected_basin_id = default_basin.id
                        if (
                            isinstance(geolocation, list)
                            and len(geolocation) >= 2
                        ):
                            geo_json = {
                                "type": "Point",
                                "coordinates": [
                                    geolocation[1],
                                    geolocation[0],
                                ],
                            }

                    # Create Datapoint
                    datapoint = Datapoint(
                        uuid=sub_uuid,
                        form_id=db_form.id,
                        published_version_id=db_form.active_version_id,
                        name=f"kobotoolbox_{sub.get('_id')}",
                        submitter=sub.get("_submitted_by", "KoboToolbox"),
                        created_at=sub_time,
                        site_id=selected_site_id,
                        basin_id=selected_basin_id,
                        status="PENDING",
                        geo=geo_json,
                    )
                    db.add(datapoint)
                    db.flush()

                    # Map answers dynamically
                    for question in db_form.questions:
                        # Direct lookup first
                        val = sub.get(question.name)
                        # Suffix lookup for nested group keys
                        if val is None and question.name:
                            suffix = f"/{question.name}"
                            for key, k_val in sub.items():
                                if key.endswith(suffix):
                                    val = k_val
                                    break
                        # Fallback to ID lookup
                        if val is None:
                            val = sub.get(str(question.id))

                        if val is not None:
                            name_val = None
                            float_val = None
                            options_val = None

                            if question.type == "number":
                                try:
                                    float_val = float(val)
                                except ValueError as e:
                                    raise ValueError(
                                        f"Value '{val}' for numeric question "
                                        f"'{question.name}' is not a valid number: {e}"
                                    )
                                # Validate bounds
                                q_name_lower = (
                                    question.name.strip().lower()
                                    if question.name
                                    else ""
                                )
                                if q_name_lower == "ph":
                                    if not (2.0 <= float_val <= 10.0):
                                        raise ValueError(
                                            f"pH value {float_val} is out of "
                                            f"bounds (2.0-10.0)"
                                        )
                                elif q_name_lower in (
                                    "water_temp",
                                    "water_temperature",
                                ):
                                    if not (5.0 <= float_val <= 50.0):
                                        raise ValueError(
                                            f"water_temp value {float_val} "
                                            f"is out of bounds (5.0-50.0)"
                                        )
                            elif question.type in (
                                "option",
                                "multiple_option",
                            ):
                                if isinstance(val, list):
                                    options_val = val
                                else:
                                    options_val = [str(val)]
                            elif question.type in ("image", "attachment"):
                                attachments = sub.get("_attachments", [])
                                attachment = next(
                                    (
                                        a
                                        for a in attachments
                                        if val == a.get("media_file_basename")
                                    ),
                                    None,
                                )
                                if attachment:
                                    download_url = attachment.get(
                                        "download_url", ""
                                    )
                                    mimetype = attachment.get(
                                        "mimetype", "application/octet-stream"
                                    )
                                    ext = (
                                        val.rsplit(".", 1)[-1]
                                        if "." in val
                                        else "bin"
                                    )
                                    blob_path = build_blob_path("kobo", ext)
                                    response = httpx.get(
                                        download_url, headers=service.headers
                                    )
                                    response.raise_for_status()
                                    StorageService().upload_file(
                                        response.content, blob_path, mimetype
                                    )
                                    name_val = blob_path
                                else:
                                    name_val = str(val)
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

                    # Update watermark per submission
                    if not watermark:
                        watermark = SyncWatermark(
                            source_system="kobotoolbox",
                            form_id=uid,
                            last_sync_time=sub_time,
                        )
                        db.add(watermark)
                    else:
                        if sub_time > watermark.last_sync_time:
                            watermark.last_sync_time = sub_time

                db.commit()
                sync_results["ingested_records"] += 1

            except Exception as e:
                logger.error(
                    f"Ingestion failed for submission {sub_uuid_str}: {e}"
                )

                try:
                    dead_letter = DeadLetter(
                        source_system="kobotoolbox",
                        raw_payload=sub,
                        error_reason=str(e),
                        status="Pending Triage",
                    )
                    db.add(dead_letter)
                    db.commit()
                except Exception as dl_err:
                    logger.error(
                        f"Failed to write dead letter for {sub_uuid_str}: {dl_err}"
                    )
                    db.rollback()

                sync_failures.append(
                    {
                        "uuid": sub_uuid_str,
                        "error": str(e),
                        "submitted_by": sub.get("_submitted_by", "Unknown"),
                    }
                )

        if latest_submission_time:
            logger.info(
                f"Updated Kobo sync watermark for {form_name} to "
                f"{latest_submission_time}"
            )

    # Process aggregated failure email alert
    if sync_failures:
        try:
            from app.models.user import User
            import asyncio

            admins = (
                db.query(User.email)
                .filter(
                    func.lower(User.role) == "admin", User.is_active.is_(True)
                )
                .all()
            )
            admin_emails = [a.email for a in admins]

            if admin_emails:
                html_body = (
                    "<h3>Kobo Ingestion Failures Alert</h3>"
                    "<p>The following submissions failed validation or "
                    "mapping during the hourly sync:</p>"
                    "<table border='1' cellpadding='5' cellspacing='0'>"
                    "<tr><th>Submission UUID</th><th>Submitter</th>"
                    "<th>Error Detail</th></tr>"
                )
                for failure in sync_failures:
                    html_body += (
                        f"<tr><td>{failure['uuid']}</td>"
                        f"<td>{failure['submitted_by']}</td>"
                        f"<td>{failure['error']}</td></tr>"
                    )
                html_body += "</table>"

                email_service = EmailService()
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                if loop.is_running():
                    loop.create_task(
                        email_service.send_email_async(
                            to=admin_emails,
                            subject="[NBD Portal] Kobo Ingestion Failures Alert",
                            html_body=html_body,
                        )
                    )
                else:
                    loop.run_until_complete(
                        email_service.send_email_async(
                            to=admin_emails,
                            subject="[NBD Portal] Kobo Ingestion Failures Alert",
                            html_body=html_body,
                        )
                    )
        except Exception as email_err:
            logger.error(
                f"Failed to send aggregated failure email alert: {email_err}"
            )

    logger.info("KoboToolbox sync finished.")
    return sync_results
