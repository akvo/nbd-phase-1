import logging
import time
import os
from datetime import datetime, timedelta
import httpx
from sqlalchemy import desc
from apscheduler.schedulers.blocking import BlockingScheduler
from app.database import SessionLocal
from app.models.whatsapp_session import WhatsAppSession
from app.models.audit_log import AuditLog
from app.mail import EmailService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


alert_states = {
    "ussd": {"last_alerted": None, "is_failing": False},
    "whatsapp": {"last_alerted": None, "is_failing": False},
}


def monitor_webhook_endpoints():
    logger.info("Running webhook watchdog check...")
    db = SessionLocal()
    try:
        from app.models.user import User

        # Ensure system user exists
        User.get_or_create_system_user(db)

        endpoints = {
            "ussd": {
                "entity_type": "ussd_webhook",
                "ping_url": "http://backend:8000/api/v1/ussd",
                "display_name": "USSD webhook (/api/v1/ussd)",
            },
            "whatsapp": {
                "entity_type": "whatsapp_webhook",
                "ping_url": "http://backend:8000/api/v1/whatsapp/webhook",
                "display_name": "WhatsApp webhook (/api/v1/whatsapp/webhook)",
            },
        }

        ops_emails_str = os.getenv(
            "OPS_EMAIL_RECIPIENTS", "alerts@nbd-wetland.org"
        )
        ops_emails = [
            email.strip()
            for email in ops_emails_str.split(",")
            if email.strip()
        ]

        for name, info in endpoints.items():
            entity_type = info["entity_type"]
            cutoff = datetime.utcnow() - timedelta(minutes=5)
            logs = (
                db.query(AuditLog)
                .filter(
                    AuditLog.entity_type == entity_type,
                    AuditLog.action == "POST",
                    AuditLog.timestamp >= cutoff,
                )
                .order_by(desc(AuditLog.timestamp))
                .all()
            )

            continuous_failures = 0
            if logs:
                for log in logs:
                    if log.entity_id == "ERROR" or (
                        log.entity_id.isdigit() and int(log.entity_id) >= 500
                    ):
                        continuous_failures += 1
                    else:
                        break
            else:
                # No traffic in last 5 minutes. Run diagnostic ping
                try:
                    r = httpx.get(info["ping_url"], timeout=5.0)
                    if r.status_code >= 500:
                        continuous_failures = 5
                except Exception:
                    continuous_failures = 5

            # Retrieve alert state from DB
            last_alert_log = (
                db.query(AuditLog)
                .filter(
                    AuditLog.entity_type == entity_type,
                    AuditLog.action.in_(["ALERT", "ALERT_RESOLVED"]),
                )
                .order_by(desc(AuditLog.timestamp))
                .first()
            )

            is_failing = last_alert_log and last_alert_log.action == "ALERT"
            last_alerted = last_alert_log.timestamp if is_failing else None

            if continuous_failures >= 5:
                logger.warning(
                    f"Webhook {name} is failing "
                    f"(continuous_failures={continuous_failures})"
                )

                now = datetime.utcnow()
                if (
                    not last_alerted
                    or (now - last_alerted).total_seconds() > 3600
                ):
                    logger.info(
                        f"Sending failure alert email for {name} "
                        f"to {ops_emails}"
                    )
                    email_service = EmailService()

                    import asyncio

                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    coro = email_service.send_alert_email(
                        to=ops_emails,
                        subject=(
                            f"[CRITICAL ALERT] {info['display_name']} "
                            f"webhook is DOWN"
                        ),
                        status_message="CRITICAL DOWNTIME",
                        description=(
                            f"The monitoring watchdog detected that the "
                            f"{info['display_name']} endpoint has returned "
                            f"continuous errors or been unreachable for "
                            f"the last 5 minutes."
                        ),
                        alert_level="danger",
                        details_headers=["Metric", "Value"],
                        details_table=[
                            ["Endpoint", info["display_name"]],
                            [
                                "Continuous Failure Checks",
                                str(continuous_failures),
                            ],
                            [
                                "Triggered Timestamp",
                                now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            ],
                        ],
                    )
                    if loop.is_running():
                        loop.create_task(coro)
                    else:
                        loop.run_until_complete(coro)

                    # Log the alert to DB to persist the state
                    sys_user = User.get_or_create_system_user(db)
                    alert_log = AuditLog(
                        actor_id=sys_user.id,
                        action="ALERT",
                        entity_type=entity_type,
                        entity_id="ALERT_SENT",
                        timestamp=now,
                    )
                    db.add(alert_log)
                    db.commit()
            else:
                if is_failing:
                    logger.info(f"Webhook {name} has recovered.")
                    email_service = EmailService()

                    import asyncio

                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    now = datetime.utcnow()
                    now_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")
                    coro = email_service.send_alert_email(
                        to=ops_emails,
                        subject=(
                            f"[RECOVERY] {info['display_name']} "
                            f"webhook is UP"
                        ),
                        status_message="RESOLVED / HEALTHY",
                        description=(
                            f"The monitoring watchdog detected that the "
                            f"{info['display_name']} endpoint has recovered "
                            f"and is now responding normally."
                        ),
                        alert_level="info",
                        details_headers=["Metric", "Value"],
                        details_table=[
                            ["Endpoint", info["display_name"]],
                            ["Recovery Timestamp", now_str],
                        ],
                    )
                    if loop.is_running():
                        loop.create_task(coro)
                    else:
                        loop.run_until_complete(coro)

                    # Log recovery to DB to persist the state
                    sys_user = User.get_or_create_system_user(db)
                    recovery_log = AuditLog(
                        actor_id=sys_user.id,
                        action="ALERT_RESOLVED",
                        entity_type=entity_type,
                        entity_id="RESOLVED",
                        timestamp=now,
                    )
                    db.add(recovery_log)
                    db.commit()
    except Exception as e:
        logger.error(f"Error in monitor_webhook_endpoints: {e}")
    finally:
        db.close()


def hourly_kobotoolbox_pull():
    logger.info("Executing hourly KoboToolbox data pull...")
    from app.services.kobo import sync_kobo_submissions

    db = SessionLocal()
    try:
        results = sync_kobo_submissions(db)
        logger.info(
            "KoboToolbox sync: Processed %d forms, Ingested %d records.",
            results.get("processed_forms", 0),
            results.get("ingested_records", 0),
        )
        if results.get("errors"):
            logger.warning("KoboToolbox sync errors: %s", results["errors"])
    except Exception as e:
        logger.error("Error pulling data from KoboToolbox: %s", e)
    finally:
        db.close()
    logger.info("KoboToolbox pull completed.")


def monthly_gee_ingest():
    logger.info("Executing monthly GEE batch ingestion...")

    # Placeholder logic for GEE batch ingestions
    time.sleep(5)
    logger.info("GEE batch ingestion completed successfully.")


def cleanup_whatsapp_sessions():
    """Delete WhatsApp sessions older than 24 hours.

    Runs hourly to comply with Meta's 24-hour messaging window policy
    and to prevent stale session state from accumulating.
    """
    logger.info("Pruning stale WhatsApp sessions (>24h)...")
    cutoff = datetime.utcnow() - timedelta(hours=24)
    db = SessionLocal()
    try:
        deleted = (
            db.query(WhatsAppSession)
            .filter(WhatsAppSession.created_at < cutoff)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info("Removed %d expired WhatsApp session(s).", deleted)
    except Exception as exc:
        db.rollback()
        logger.error("Session cleanup failed: %s", exc)
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Initializing APScheduler daemon...")
    scheduler = BlockingScheduler()

    # Schedule hourly KoboToolbox pulls
    scheduler.add_job(hourly_kobotoolbox_pull, "cron", hour="*")

    # Schedule monthly GEE batch ingestions
    # (runs on the 1st of every month at 00:00)
    scheduler.add_job(monthly_gee_ingest, "cron", day=1, hour=0, minute=0)

    # Schedule hourly WhatsApp session cleanup
    scheduler.add_job(cleanup_whatsapp_sessions, "cron", hour="*")

    # Schedule webhook watchdog check (every minute)
    # scheduler.add_job(monitor_webhook_endpoints, "cron", minute="*")

    logger.info("Scheduler configured. Starting loop...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
