import os
import json
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


def _resolve_kobo_other_text(sub: dict, question_name: str) -> str | None:
    """
    Looks up the free-text "allow other" companion field from a Kobo
    submission payload.

    Kobo is inconsistent with its naming: the companion key may appear
    as any of the four patterns below.  We try them in order and return
    the first non-empty value found, or None.

    Patterns tried (for question_name='plants'):
        1. others_plants
        2. other_plants
        3. plants_other
        4. plants_others

    Each pattern is also checked as a nested-group suffix
    (e.g. ``group/others_plants``) to handle XLSForm groups.
    """
    candidates = [
        f"others_{question_name}",
        f"other_{question_name}",
        f"{question_name}_other",
        f"{question_name}_others",
    ]
    for candidate in candidates:
        # Direct key lookup
        val = sub.get(candidate)
        if val is not None:
            return str(val)
        # Nested group suffix lookup (e.g. "group/others_plants")
        suffix = f"/{candidate}"
        for key, k_val in sub.items():
            if key.endswith(suffix) and k_val is not None:
                return str(k_val)

    # Fallback to fuzzy substring match for truncated keys (XLSForm limits)
    # e.g. "ecological/others_main_activities_observe"
    # for "main_activities_observed"
    if len(question_name) > 10:
        prefix_part = question_name[:10]
        for key, k_val in sub.items():
            if k_val is not None:
                key_lower = key.lower()
                if prefix_part in key_lower:
                    last_part = key_lower.split("/")[-1]
                    if (
                        last_part.startswith("others_")
                        or last_part.startswith("other_")
                        or last_part.endswith("_other")
                        or last_part.endswith("_others")
                        or "others_" in last_part
                        or "other_" in last_part
                    ):
                        return str(k_val)
    return None


def _apply_env_filter(form_name: str) -> str | None:
    """
    Applies environment-specific Kobo form name filtering.

    Reads KOBO_FORM_NAME_PREFIX and KOBO_FORM_NAME_SUFFIX
    from the environment.
    Returns the normalized (stripped + lowercased) form name
    for DB lookup, or None if the form does not match the
    configured filter and should be skipped.

    Matching is case-insensitive. Stripping uses len() offset on the original
    string to preserve mid-string casing before final lowercasing.
    """
    prefix = os.getenv("KOBO_FORM_NAME_PREFIX", "").strip().lower()
    suffix = os.getenv("KOBO_FORM_NAME_SUFFIX", "").strip().lower()
    name_lower = form_name.lower()

    print(
        f"[KOBO SYNC] Processing Kobo Form: '{form_name}' (Prefix config: '{prefix}', Suffix config: '{suffix}')"  # noqa
    )

    if prefix and not name_lower.startswith(prefix):
        print(f"[KOBO SYNC] - SKIPPED: does not match prefix '{prefix}'")
        logger.debug(
            f"Skipping Kobo form '{form_name}': "
            f"does not match prefix '{prefix}'"
        )
        return None

    if suffix and not name_lower.endswith(suffix):
        print(f"[KOBO SYNC] - SKIPPED: does not match suffix '{suffix}'")
        logger.debug(
            f"Skipping Kobo form '{form_name}': "
            f"does not match suffix '{suffix}'"
        )
        return None

    # Strip from original (offset by len) to preserve mid-string casing
    stripped = form_name
    if prefix:
        stripped = stripped[len(prefix) :]  # noqa
    if suffix:
        stripped = stripped[: len(stripped) - len(suffix)]

    normalized = stripped.strip().lower()
    print(f"[KOBO SYNC] - MATCHED: Normalized name is '{normalized}'")
    return normalized


def sync_kobo_submissions(db: Session) -> Dict[str, Any]:
    logger.info("Starting KoboToolbox submissions sync...")
    try:
        return _sync_kobo_submissions_core(db)
    except Exception as e:
        _send_sync_crash_alert(db, e)
        raise e


def _sync_kobo_submissions_core(db: Session) -> Dict[str, Any]:
    service = KoboService()
    sync_results = {"processed_forms": 0, "ingested_records": 0, "errors": []}
    sync_failures = []

    try:
        forms = service.get_forms()
    except Exception as e:
        logger.error(f"Failed to fetch forms list from KoboToolbox: {e}")
        raise e

    # Get a default polymorphic anchor
    default_basin = db.query(Basin).first()
    if not default_basin:
        err_msg = "No Basin found in database to act as polymorphic anchor."
        logger.error(err_msg)
        raise ValueError(err_msg)

    for form in forms:
        form_name = form.get("name")
        uid = form.get("uid")
        if not form_name or not uid:
            continue

        # Match by kobo_asset_id first, then fallback to form name
        # (lowercase & stripped)
        normalized_name = _apply_env_filter(form_name)
        if normalized_name is None:
            continue

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

        for sub in submissions:
            payload_str = json.dumps(sub, indent=2)
            logger.debug(
                f"[KOBO SYNC] Fetched raw submission payload:\n{payload_str}"
            )
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
                                        (
                                            func.lower(Site.code)
                                            == func.lower(str(val))
                                        )
                                        | (
                                            func.lower(Site.name)
                                            == func.lower(str(val))
                                        )
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
                        submitter=sub.get("_submitted_by") or "KoboToolbox",
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
                        # 1. Determine if this question
                        # belongs to a repeatable group
                        is_repeat = (
                            question.question_group.repeatable
                            if question.question_group
                            else False
                        )

                        # Collect list of (value, index) to process
                        mappings = []

                        if is_repeat:
                            repeat_list = None
                            suffix = f"/{question.name}"
                            for k, v in sub.items():
                                if (
                                    isinstance(v, list)
                                    and len(v) > 0
                                    and isinstance(v[0], dict)
                                ):
                                    # Verify if this list belongs
                                    # to our repeatable question
                                    first_item = v[0]
                                    if question.name in first_item or any(
                                        rk.endswith(suffix)
                                        for rk in first_item.keys()
                                    ):
                                        repeat_list = v
                                        break
                            if repeat_list:
                                for idx, item in enumerate(repeat_list):
                                    item_val = item.get(question.name)
                                    if item_val is None:
                                        for rk, rv in item.items():
                                            if rk.endswith(suffix):
                                                item_val = rv
                                                break
                                    if item_val is not None:
                                        mappings.append((item_val, idx))
                        else:
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
                                mappings.append((val, 0))

                        for val, idx in mappings:
                            name_val = None
                            float_val = None
                            options_val = None

                            if question.type == "number":
                                try:
                                    float_val = float(val)
                                except ValueError as e:
                                    raise ValueError(
                                        f"Value '{val}' for numeric question "
                                        f"'{question.name}' is not a valid "
                                        f"number: {e}"
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
                                    if (
                                        question.type == "multiple_option"
                                        and isinstance(val, str)
                                    ):
                                        options_val = [
                                            x.strip()
                                            for x in val.split(" ")
                                            if x.strip()
                                        ]
                                    else:
                                        options_val = [str(val)]
                                # Capture free-text "allow other" companion
                                # field if the question has allowOther=True.
                                # The extra JSONB may store the flag as
                                # camelCase (JSON seed) or snake_case (router).
                                q_extra = question.extra or {}
                                has_allow_other = q_extra.get(
                                    "allowOther"
                                ) or q_extra.get("allow_other")
                                if has_allow_other and question.name:
                                    other_text = _resolve_kobo_other_text(
                                        sub, question.name
                                    )
                                    if other_text:
                                        name_val = other_text
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
                                index=idx,
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
                        f"Failed to write dead letter for "
                        f"{sub_uuid_str}: {dl_err}"
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
                email_service = EmailService()
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                failures_table = [
                    [f["uuid"], f["submitted_by"], f["error"]]
                    for f in sync_failures
                ]

                coro = email_service.send_alert_email(
                    to=admin_emails,
                    subject="[NBD Portal] Kobo Ingestion Failures Alert",
                    status_message="QUARANTINED SUBMISSIONS",
                    description=(
                        "The following submissions failed validation or "
                        "mapping during the hourly sync and have been "
                        "quarantined in the dead-letter queue (DLQ):"
                    ),
                    alert_level="warning",
                    details_headers=[
                        "Submission UUID",
                        "Submitter",
                        "Error Detail",
                    ],
                    details_table=failures_table,
                )

                if loop.is_running():
                    loop.create_task(coro)
                else:
                    loop.run_until_complete(coro)
        except Exception as email_err:
            logger.error(
                f"Failed to send aggregated failure email alert: {email_err}"
            )

    logger.info("KoboToolbox sync finished.")
    return sync_results


def _send_sync_crash_alert(db: Session, error: Exception):
    try:
        from app.models.user import User
        import traceback
        import asyncio

        admins = (
            db.query(User.email)
            .filter(func.lower(User.role) == "admin", User.is_active.is_(True))
            .all()
        )
        admin_emails = [a.email for a in admins]
        if not admin_emails:
            return

        email_service = EmailService()
        tb_str = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        coro = email_service.send_alert_email(
            to=admin_emails,
            subject="[CRITICAL ALERT] Kobo Sync Service Crash",
            status_message="SERVICE CRASHED",
            description=(
                "The KoboToolbox background synchronization service has "
                "crashed due to an unhandled exception."
            ),
            alert_level="danger",
            details_headers=["Error Type", "Error Message"],
            details_table=[[type(error).__name__, str(error)]],
            traceback=tb_str,
        )
        if loop.is_running():
            loop.create_task(coro)
        else:
            loop.run_until_complete(coro)
    except Exception as email_err:
        logger.error(f"Failed to send sync crash email alert: {email_err}")
