# PRD — Phone Number Persistence & Presentation

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: PM + Design Lead | Target Location: `docs/prd/phone_number_persistence_prd.md` | References: `docs/prd/privacy_pipeline_prd.md`, `docs/prd/ussd_pipeline_prd.md`, `docs/prd/whatsapp_pipeline_prd.md`
> Status: `Approved`

---

## 1. Overview

**Problem Statement**:
Currently, the USSD and WhatsApp pipelines handle submitter identities inconsistently:

- WhatsApp saves the phone number under the `name` column as `wa-{phone}` and sets `submitter="WHATSAPP"`.
- USSD does not save the phone number at all in the `datapoint` table (it sets `submitter="USSD"` and `name=sessionId`).

Reviewers and Admins need to verify submissions or contact reporters for follow-up details on reported pollution. To facilitate this, we must persistently save and display the reporter's phone number in the Admin Data Management table under the "Submitter" field, prefixed by the channel name (`ussd-{phone_number}` or `wa-{phone_number}`). At the same time, we must maintain strict PII protection to ensure no phone numbers are leaked via public endpoints or client console logs.

**What we are building**:

1. Unified submission persistence of reporter phone numbers:
   - For **USSD**, save the phone number in the `submitter` column as `ussd-{phoneNumber}`.
   - For **WhatsApp**, save the phone number in the `submitter` column as `wa-{phone_number}`.
2. Admin Dashboard Visibility:
   - Display the phone number prefix (`ussd-` or `wa-` followed by the actual phone number) in the admin data management table.
3. Strict Public PII Masking:
   - Ensure the Pydantic public response schema (`PublicDatapointResponse`) masks the `submitter` field when returning responses to the public portal, leaving zero plaintext phone numbers exposed.

---

## 2. Goals & Success Metrics

| Goal                                   | Success Metric                                                                             | Baseline                                                 | Target                                |
| -------------------------------------- | ------------------------------------------------------------------------------------------ | -------------------------------------------------------- | ------------------------------------- |
| Persist phone numbers across pipelines | All incoming USSD & WhatsApp submissions record the phone number in the `submitter` column | Partially implemented (WhatsApp name only; USSD omitted) | 100% of USSD and WhatsApp submissions |
| Admin Visibility                       | Admins can view full phone numbers in the admin data workspace                             | Missing in table for USSD                                | Fully visible for authenticated roles |
| Public Privacy                         | Zero leaked phone numbers via public APIs or browser network tab logs                      | `submitter` field is not masked                          | 100% masked for all public responses  |

---

## 3. Target Users & Personas

| Persona                | Job-to-be-Done                                                              | Key Frustration                                          | v1 Priority |
| ---------------------- | --------------------------------------------------------------------------- | -------------------------------------------------------- | ----------- |
| **Admin / Reviewer**   | Review incoming submissions and contact reporters for verification/details. | Hard to find reporter contact info for USSD submissions. | Primary     |
| **Public Portal User** | Browse the public map of verified incidents.                                | Privacy concerns if reporter PII is visible.             | Primary     |

---

## 4. User Stories

| ID     | User Story                                                                                                                                                   | Priority (MoSCoW) | FR Reference   |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------- | -------------- |
| US-001 | As an **Admin/Reviewer**, I want to see the phone number of USSD and WhatsApp submitters in the admin dashboard so that I can contact them for verification. | Must Have         | FR-001, FR-002 |
| US-002 | As a **Citizen Reporter**, I want my phone number to be hidden on the public website and API responses so that my identity is kept private.                  | Must Have         | FR-003         |

---

## 5. Functional Requirements

| ID     | Requirement                                                                                                                                                                                                                              | User Story | Priority  |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | --------- |
| FR-001 | For **USSD** submissions, the `submitter` column in `datapoint` MUST be saved as `ussd-{phoneNumber}`.                                                                                                                                   | US-001     | Must Have |
| FR-002 | For **WhatsApp** submissions, the `submitter` column in `datapoint` MUST be saved as `wa-{phone}`.                                                                                                                                       | US-001     | Must Have |
| FR-003 | The public response schema `PublicDatapointResponse` MUST dynamically mask any phone numbers stored in the `submitter` column (e.g. converting `wa-+254712345678` -> `wa-+254*****678` or similar masking) before transmitting payloads. | US-002     | Must Have |

---

## 6. Non-Functional Requirements

| Category      | Requirement         | Metric                                                                                                      |
| ------------- | ------------------- | ----------------------------------------------------------------------------------------------------------- |
| **Security**  | PII Leak Prevention | Zero plaintext phone numbers in `/api/v1/submissions` response payload (even in nested fields or dev tools) |
| **Usability** | Consistency         | Submitter format `{pipeline}-{phone_number}` is consistently formatted and displayed                        |

---

## 7. Acceptance Criteria

### User Acceptance Criteria

- **Given** an admin reviewer logged in to the admin panel, **When** viewing the submissions table, **Then** they see the submitter value displaying `ussd-{phone_number}` or `wa-{phone_number}` in plaintext.
- **Given** a public user visiting the public map, **When** the page fetches incidents from `/api/v1/submissions`, **Then** the `submitter` field in the response contains a masked string (e.g., `wa-+254*****678` or `ussd-+254*****678`) and the full phone number is not exposed.

---

## 8. Change Log

| Version | Date       | Author  | Changes       |
| ------- | ---------- | ------- | ------------- |
| 1.0     | 2026-07-08 | Winston | Initial draft |
