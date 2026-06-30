# PRD — Twilio WhatsApp Migration

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: PM + Winston (Architect) | Target Location: `docs/prd/twilio_whatsapp_migration_prd.md` | References: `docs/prd/whatsapp_pipeline_prd.md`
> Status: `Approved` (Pending User Sign-off)

---

## 1. Overview

**One-liner**:
Migrate the backend WhatsApp ingestion pipeline from direct Meta Cloud API integration to Twilio, updating webhook signature verification, inbound payload parsing, media retrieval, and outbound messaging.

**Brief / Problem Reference**:
Refers to the existing Meta WhatsApp integration (`docs/prd/whatsapp_pipeline_prd.md` and `whatsapp_service.py`). Using Twilio simplifies configuration, improves webhook payload handling, and provides a stable API for messaging and media downloads.

**What we are building**:
We are refactoring the WhatsApp router and service to integrate with Twilio instead of Meta Cloud API:

1. **Credentials Management**: Update env config to load Twilio Account SID, Auth Token, and Twilio WhatsApp Sender Number.
2. **Webhook Verification**: Replace Meta's hub validation (`GET /webhook`) and signature check (`X-Hub-Signature-256`) with Twilio's HTTP request validator (`X-Twilio-Signature`).
3. **Payload Parsing**: Transition inbound webhook handling from JSON payloads to form-urlencoded payloads containing Twilio parameters (`From`, `Body`, `NumMedia`, `MediaUrl0`, `MediaContentType0`).
4. **Media Retrieval**: Update the media downloader to fetch public/auth-protected media directly from Twilio's URL and stream to Google Cloud Storage.
5. **Outbound Messaging**: Update the message sender to post to Twilio's Messages endpoint.

---

## 2. Goals & Success Metrics

| Goal                        | Success Metric                                                                                                                       | Baseline         | Target                 | Owner     |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ---------------- | ---------------------- | --------- |
| Seamless migration          | High-fidelity parity of the stateful questionnaire flow (Consent -> Incident Selection -> Media -> Location -> Confirmation -> Save) | Meta Integration | 100% functional parity | Dev       |
| Twilio webhook security     | 100% webhook signature verification success rate for legitimate Twilio requests                                                      | Meta Signature   | 100% Twilio Signature  | Architect |
| Media ingestion reliability | Successful GCS streaming of image/video attachments sent via Twilio                                                                  | Meta API stream  | > 98% upload success   | Dev       |

---

## 3. Target Users & Personas

| Persona          | Job-to-be-Done                                                        | Key Frustration                                                 | v1 Priority |
| ---------------- | --------------------------------------------------------------------- | --------------------------------------------------------------- | ----------- |
| Citizen Reporter | Submit environmental alerts quickly with visual proof using WhatsApp. | Session interruptions, slow responses, or failed media uploads. | Primary     |

---

## 4. User Stories

| ID     | User Story                                                                                                                                                      | Priority (MoSCoW) | FR Reference |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ------------ |
| US-001 | As a **Citizen Reporter**, I want my WhatsApp reports to be processed identically through the questionnaire state machine regardless of the underlying gateway. | Must Have         | FR-001       |
| US-002 | As a **Developer**, I want webhook endpoints secured with Twilio signature validation so that only authentic Twilio events are processed.                       | Must Have         | FR-002       |
| US-003 | As a **System Operator**, I want all environment variables unified under Twilio config parameters to ease deployment.                                           | Must Have         | FR-003       |

---

## 5. Functional Requirements

| ID     | Requirement                                                                                                                                                                                                                                                           | User Story | Priority  |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | --------- |
| FR-001 | **Outbound Twilio API Client**: The backend MUST send text messages using the Twilio Messages API `POST /2010-04-01/Accounts/{AccountSid}/Messages.json` using Basic Authentication.                                                                                  | US-001     | Must Have |
| FR-002 | **Inbound Webhook Signature Verification**: The backend MUST validate incoming webhook POST requests from Twilio using the `X-Twilio-Signature` header and the raw URL / payload data.                                                                                | US-002     | Must Have |
| FR-003 | **Form-Urlencoded Payload Ingestion**: The backend MUST parse incoming Twilio form parameters (`From`, `Body`, `NumMedia`, `MediaUrl0`, `MediaContentType0`).                                                                                                         | US-001     | Must Have |
| FR-004 | **Media Download Integration**: The backend MUST fetch attachments directly from the URL provided in `MediaUrl0` (and downstream media URLs if multiple are sent) and stream them into the unified GCS bucket.                                                        | US-001     | Must Have |
| FR-005 | **Cleanup GET Webhook**: Since Twilio webhook validation doesn't require a Meta-style `GET /webhook` challenge response, the GET endpoint can be simplified/removed or made a basic health check, but for compatibility we will clean up or document its replacement. | US-003     | Must Have |

---

## 6. Non-Functional Requirements

| Category          | Requirement            | Metric                                                                                                                                                                           |
| ----------------- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Security**      | Signature Verification | Validate incoming Twilio webhook signature using the standard algorithm (either using the official `twilio` library or manual signature computation with the Twilio Auth Token). |
| **Compatibility** | Backward Compatibility | Maintain the exact same database state transitions (`whatsapp_sessions`) and completed Datapoint/Answer schema structures.                                                       |
| **Performance**   | Webhook Response       | Respond with a basic 200 OK or TwiML response within 3 seconds to avoid webhook retries.                                                                                         |

---

## 7. Scope Boundaries

**In Scope**:

- Refactoring `backend/app/routers/whatsapp_router.py` to verify Twilio request signature and parse incoming form-urlencoded parameters.
- Refactoring `backend/app/services/whatsapp_service.py` to use Twilio REST API for messages and media.
- Refactoring `backend/app/dependencies/whatsapp_config.py` (renaming to `twilio_config.py` or updating class fields) to use Twilio env parameters.
- Updating tests in `backend/tests/test_whatsapp.py` to match the Twilio payload and signature verification.

**Out of Scope**:

- Front-end layout or workspace changes.
- Database schema changes (the existing `whatsapp_sessions` table remains unchanged).

---

## 8. Epic & Ballpark Estimation

| Component                                                                          | Complexity | Ballpark Estimate |
| ---------------------------------------------------------------------------------- | ---------- | ----------------- |
| Dependency Updates (`twilio` library addition if preferred or direct httpx client) | Simple     | 0.2 Day           |
| Config & Env Variable Updates                                                      | Simple     | 0.2 Day           |
| Webhook Router Refactor (Twilio Signature & Form parsing)                          | Medium     | 0.8 Day           |
| Webhook Service Refactor (Twilio Send & Media stream)                              | Medium     | 0.8 Day           |
| Integration & Unit Tests Migration                                                 | Medium     | 1.0 Day           |

**Total Estimated Effort**: ~3.0 Developer Days

---

## 9. Rollout & Rollback Plan

- **Rollout**: Configure the new Twilio env variables (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_NUMBER`, `TWILIO_WEBHOOK_URL`) on the target environment and deploy the refactored backend. Update the Twilio console webhook url to point to `/api/v1/whatsapp/webhook`.
- **Rollback**: Revert code commits to Meta-based implementation and restore Meta credentials in the environment.
