# LLD — Application Monitoring & Alert Hooks

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Tech Lead / Senior Engineer | Target Location: `docs/lld/application_monitoring_lld.md` | References: `docs/prd/application_monitoring_prd.md`
> Status: `Approved` | Open Questions Remaining: `0`

---

## 1. Overview & Scope

This low-level design document details the implementation of Task 7: Application Monitoring & Alert Hooks.

### Component / Module
* **`WebhookWatchdogService`**: Background check runs every 1 minute in `scheduler.py` to check the health of Africa's Talking USSD and WhatsApp webhooks.
* **`EmailService`**: Renders styled Jinja2 HTML alert and invite emails and resolves default CTA URLs (`{FRONTEND_URL}/admin/data` and `{FRONTEND_URL}/login`) at call time via `_resolve_frontend_url()` (falling back to `http://localhost:3000`).
* **`KoboSyncAlertHook`**: Executes `KoboService._get_with_retry()` and `download_attachment()` for transient Kobo API retries, throttles crash notifications with `AuditLog` (`entity_type="kobo_sync"`) cooldown (`KOBO_CRASH_ALERT_COOLDOWN_SECONDS=14400`) and `[RECOVERY]` emails, and excludes `SYSTEM_USER_EMAIL` (`system@nbd-wetland.org`) from human admin recipients.
* **`WhatsAppSessionCleanup`**: Automated task verified and tested to prune stale sessions (> 24 hours old) daily.

### PRD References
* **UAC-01**: Webhook Monitoring & 5-minute continuous failure window alert.
* **UAC-02**: Kobo sync failure alert to Admins.
* **UAC-03**: DLQ quarantine alerts to Admins.
* **UAC-04**: Styled responsive HTML email template matching NBD visual branding.
* **TAC-01**: Webhook Watchdog scheduler implementation querying `audit_logs`.
* **TAC-02**: WhatsApp session pruning hourly execution.

### Out of Scope
* Integration with Datadog, PagerDuty, or Sentry.
* Frontend status dashboard.

---

## 2. Component & Class Design

We will extend `EmailService` and build a `WebhookWatchdog` inside the scheduler.

```mermaid
classDiagram
    class EmailService {
        +send_email_async(to: list, subject: str, html_body: str, text_body: str) bool
        +send_alert_email(to: list, subject: str, status_message: str, description: str, alert_level: str, action_url: str) bool
        +send_invite_email(to: str, role: str, invited_by: str, login_url: str) bool
    }

    class WebhookWatchdog {
        +monitor_webhook_endpoints(db: Session) void
        -check_recent_audit_logs(db: Session, endpoint: str, window_minutes: int) bool
        -ping_endpoint(endpoint: str) bool
        -trigger_alert(endpoint: str, reason: str) void
    }

    class scheduler {
        +hourly_kobotoolbox_pull() void
        +cleanup_whatsapp_sessions() void
        +monitor_webhook_endpoints() void
    }

    scheduler --> WebhookWatchdog : invokes
    WebhookWatchdog --> EmailService : sends email via
```

### Class Responsibilities:
| Class | Responsibility | SOLID Principle |
|-------|---------------|-----------------|
| `EmailService` | Loads SMTP configuration, renders HTML alert and invite templates, resolves `FRONTEND_URL` defaults via `_resolve_frontend_url()`, and sends asynchronous emails. | SRP — single email delivery domain concern. |
| `WebhookWatchdog` | Performs availability checks, audits error codes from the database logs, pings endpoints on zero-traffic state, and throttles alert dispatch. | SRP — separate concern from core scheduling. |
| `scheduler.py` | Orchestrates the periodic execution of the monitoring, sync, and pruning tasks. | SRP — scheduling loop driver. |

---

## 3. Sequence Diagrams

### 3.1 Webhook Check Failure Path (5-Minute Window & Alerting)

```mermaid
sequenceDiagram
    participant Scheduler as APScheduler (1 min)
    participant Watchdog as WebhookWatchdog
    participant DB as PostgreSQL DB
    participant API as Webhook Endpoint
    participant Mail as EmailService

    Scheduler->>Watchdog: monitor_webhook_endpoints()
    Watchdog->>DB: Query audit_logs for "/api/v1/ussd" & "/api/v1/whatsapp/webhook" (last 5 min)
    DB-->>Watchdog: logs (e.g. 500 error codes or no traffic)
    alt No Traffic Logs
        Watchdog->>API: Diagnostic Ping (GET /api/healthz or internal ping)
        API-->>Watchdog: Timeout or 5xx
    end
    alt Failures persist >= 5 minutes
        Watchdog->>Watchdog: Check Alert Cooldown / Throttle State
        alt Cooldown Active
            Watchdog-->>Scheduler: Muted (No email sent)
        else Cooldown Inactive
            Watchdog->>Mail: send_alert_email(ops_list, "CRITICAL: Webhook Down", template, context)
            Mail-->>Watchdog: OK
            Watchdog->>Watchdog: Update last_alerted timestamp (Activate 1-hour cooldown)
        end
    end
    Watchdog-->>Scheduler: Finished
```

### 3.2 Kobo Ingestion Retry, Crash Cooldown & DLQ Alerting Path

```mermaid
sequenceDiagram
    participant Cron as APScheduler
    participant Ingest as sync_kobo_submissions
    participant Client as KoboService._get_with_retry
    participant DB as PostgreSQL DB
    participant Mail as EmailService

    Cron->>Ingest: sync_kobo_submissions(db)
    Ingest->>Client: get_forms() / get_submissions() / download_attachment()
    alt Transient 429/5xx or timeout exhausts retries
        Client-->>Ingest: Raise exception
        Ingest->>DB: db.rollback() & query latest kobo_sync AuditLog
        alt Latest action == ALERT within KOBO_CRASH_ALERT_COOLDOWN_SECONDS
            Ingest-->>Cron: Suppress duplicate crash email
        else No active alert or cooldown expired
            Ingest->>DB: Query active human Admins (exclude SYSTEM_USER_EMAIL)
            Ingest->>Mail: send_alert_email(action_url={FRONTEND_URL}/admin/data)
            Ingest->>DB: INSERT AuditLog(action="ALERT", entity_type="kobo_sync", entity_id="ALERT_SENT")
        end
    else Sync executes
        alt Validation fails for record
            Ingest->>DB: Insert record into dead_letters (DLQ)
        end
        opt Any quarantined failures
            Ingest->>DB: Query active human Admins (exclude SYSTEM_USER_EMAIL)
            Ingest->>Mail: send_alert_email(human_admins, "[NBD Portal] Kobo Ingestion Failures Alert")
        end
        opt Sync finishes cleanly (errors == []) and latest kobo_sync AuditLog == ALERT
            Ingest->>DB: Query active human Admins (exclude SYSTEM_USER_EMAIL)
            Ingest->>Mail: send_alert_email(human_admins, "[RECOVERY] ...", alert_level="info")
            Ingest->>DB: INSERT AuditLog(action="ALERT_RESOLVED", entity_type="kobo_sync", entity_id="RESOLVED")
        end
    end
    Ingest-->>Cron: Complete
```

---

## 4. API Contracts

### 4.1 Mock Webhook Failure Endpoint (Testing Only)
`GET /api/v1/test/mock-webhook-failure`
* **Purpose**: Simulates a webhook failure by writing a dummy error log entry to `audit_logs` (or setting a mock flag) to test the 5-minute continuous failure window logic.
* **Query Parameters**:
  * `endpoint` (Required): String, either `ussd` or `whatsapp`.
  * `status_code` (Optional): Integer, default `500`.
* **Response `200 OK`**:
  ```json
  {
    "status": "logged",
    "endpoint": "/api/v1/ussd",
    "logged_status_code": 500
  }
  ```

---

## 5. Database Schema

No new tables are introduced. Webhook logs and alert state transitions persist to the existing `audit_logs` table using the seeded **System User** (`SYSTEM_USER_EMAIL` in `backend/app/models/user.py`):

* **System User Email**: `system@nbd-wetland.org` (`SYSTEM_USER_EMAIL`)
* **Role**: `Admin` (explicitly excluded from alert email recipients by `_get_human_admin_emails()`)

### Audit Log Fields Mapping for Webhook Calls:
* `actor_id`: UUID of the system user.
* `action`: HTTP Method (e.g. `"POST"`), or `"ALERT"` / `"ALERT_RESOLVED"`.
* `entity_type`: `"ussd_webhook"` or `"whatsapp_webhook"`.
* `entity_id`: Status Code returned by the handler (e.g., `"200"`, `"500"`, `"503"`, `"ERROR"`), `"ALERT_SENT"`, or `"RESOLVED"`.

### Audit Log Fields Mapping for Kobo Sync Alerts:
* `actor_id`: UUID of `SYSTEM_USER_EMAIL`.
* `action`: `"ALERT"` (crash notification dispatched) or `"ALERT_RESOLVED"` (recovery notice dispatched). State transitions use append-only `INSERT` rows because `audit_logs_immutable_trigger` blocks `UPDATE` and `DELETE`.
* `entity_type`: `"kobo_sync"`.
* `entity_id`: `"ALERT_SENT"` or `"RESOLVED"`.

### Index Strategy:
The existing composite index `idx_audit_logs_entity` on `(entity_type, entity_id)` and the `timestamp` column supports fast queries for recent webhook logs and latest alert state.

---

## 6. Logic & Algorithms

### Webhook Availability Logic (Every 1 Minute)
```
FUNCTION monitor_webhook_endpoints():
    FOR EACH endpoint IN ["ussd_webhook", "whatsapp_webhook"]:
        // Query database logs
        recent_logs = SELECT * FROM audit_logs
                      WHERE entity_type = endpoint
                      AND timestamp >= NOW() - 5 minutes
                      ORDER BY timestamp DESC

        continuous_failures = 0
        total_requests = LENGTH(recent_logs)

        IF total_requests > 0:
            FOR log IN recent_logs:
                IF INT(log.entity_id) >= 500 OR log.entity_id == "ERROR":
                    continuous_failures += 1
                ELSE:
                    # Healthy log found, break continuous failure chain
                    BREAK
        ELSE:
            # Zero traffic. Run diagnostic ping
            status = diagnostic_ping(endpoint)
            IF status >= 500 or status == "TIMEOUT":
                continuous_failures = 5 # Trigger alert immediately

        IF continuous_failures >= 5:
            IF NOT is_muted(endpoint):
                dispatch_ops_alert(endpoint, "Continuous failures detected in the last 5 minutes.")
                mark_muted(endpoint)
        ELSE:
            IF is_muted(endpoint):
                dispatch_ops_recovery(endpoint)
                unmark_muted(endpoint)
```

### Kobo Sync Crash Cooldown & Recovery Logic (Hourly)
```
FUNCTION _send_sync_crash_alert(db, error):
    db.rollback()
    latest = SELECT * FROM audit_logs
             WHERE entity_type = "kobo_sync"
             AND action IN ("ALERT", "ALERT_RESOLVED")
             ORDER BY timestamp DESC LIMIT 1

    cooldown = INT(ENV["KOBO_CRASH_ALERT_COOLDOWN_SECONDS"] or 14400)
    IF latest AND latest.action == "ALERT" AND (NOW() - latest.timestamp) < cooldown:
        RETURN // Suppress duplicate outage email

    recipients = _get_human_admin_emails(db) // Exclude SYSTEM_USER_EMAIL
    IF EMPTY(recipients):
        RETURN

    EmailService().send_alert_email(to=recipients, subject="[CRITICAL ALERT] ...", alert_level="danger")
    INSERT INTO audit_logs (actor_id=sys_user.id, action="ALERT", entity_type="kobo_sync", entity_id="ALERT_SENT")

FUNCTION _maybe_send_sync_recovery_alert(db):
    // Invoked when sync completes with zero errors
    latest = SELECT * FROM audit_logs
             WHERE entity_type = "kobo_sync"
             AND action IN ("ALERT", "ALERT_RESOLVED")
             ORDER BY timestamp DESC LIMIT 1

    IF latest AND latest.action == "ALERT":
        recipients = _get_human_admin_emails(db)
        IF NOT EMPTY(recipients):
            EmailService().send_alert_email(to=recipients, subject="[RECOVERY] ...", alert_level="info")
        INSERT INTO audit_logs (actor_id=sys_user.id, action="ALERT_RESOLVED", entity_type="kobo_sync", entity_id="RESOLVED")
```

---

## 7. Design Patterns

* **Observer Pattern / Hooks**: Kobo sync compiles quarantined payloads and notifies active human admins (excluding `SYSTEM_USER_EMAIL`) via `EmailService`.
* **Append-Only State Persistence**: Both webhook watchdogs and Kobo sync crash alerting persist `ALERT` and `ALERT_RESOLVED` transitions in `audit_logs` so cooldown and recovery state survive worker restarts.
* **Dynamic URL Resolution**: `EmailService` resolves `action_url` (`{FRONTEND_URL}/admin/data`) and `login_url` (`{FRONTEND_URL}/login`) at call time via `_resolve_frontend_url()` so production emails never render hardcoded `localhost` links.

---

## 8. Error Handling & Edge Cases

| Scenario | Detection | Mitigation |
|----------|-----------|------------|
| SMTP Service Down | SMTP connection timeout / exception. | Catch exception, log error to standard logger, write warning to system output. Do not crash background loop. |
| Zero traffic on webhook | Length of recent `audit_logs` is 0. | Trigger active ping to local backend webhook endpoints to verify responsiveness. |
| Transient Kobo API `429`/`5xx` or timeout | `KoboService._get_with_retry()` catches `HTTPStatusError` (`429`, `500`, `502`, `503`, `504`), `TimeoutException`, or `TransportError`. | Retry with bounded exponential backoff, jitter, and `Retry-After` handling before tripping crash alerting. |
| Dirty SQLAlchemy session on sync crash | Unhandled exception inside `sync_kobo_submissions()` transaction. | Call `db.rollback()` inside `_send_sync_crash_alert()` prior to querying `audit_logs` and `users`. |
| Memory leak in Scheduler | Continuous run of APScheduler. | Keep alert state variables localized and minimal. Close DB sessions in `try-finally` blocks. |

---

## 9. Non-Functional Design Decisions

### Performance
* Queries on `audit_logs` are limited to the past 5 minutes, keeping DB read overhead extremely low.
* Emails are compiled and sent asynchronously using `fastapi_mail` to prevent locking the main scheduler loop.

### Security
* The system email template exposes stack traces only to registered Admin/Ops email lists, avoiding public exposure.
* System user credentials used for automated logs do not have password hashes, preventing login attempts.
