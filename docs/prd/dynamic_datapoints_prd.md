# PRD — Dynamic Datapoints & Polymorphic Ingestion Routing

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: John (PM) | Target Location: `docs/prd/dynamic_datapoints_prd.md`
> Status: `Draft`

---

## I. Overview & Goal

The system needs to store citizen-led submissions from varying ingestion channels (USSD, KoboCollect, web forms). Submissions contain responses to dynamic forms (Layer C) but are physically anchored to different tiers of the geographic hierarchy (Layer A) depending on the context:
- A USSD pollution report may only specify a **Basin** (e.g., Mara Basin).
- An FGD qualitative assessment may specify a **Wetland** (e.g., Mara Floodplain).
- A KoboCollect physico-chemical sample must be anchored to a specific **Site** (e.g., NBD-MARA-001).

The database must support this polymorphic anchoring cleanly, while enforcing strict type safety, data integrity, and mutual exclusivity constraints.

---

## II. User Stories & Flows

### Personas
- **Citizen Scientist**: Submits monthly physico-chemical and ecological measurements at a specific fixed site.
- **Citizen Reporter**: Submits pollution incident alerts from mobile devices (USSD or WhatsApp) linked to a basin.
- **CSO Staff / Reviewer**: Facilitates FGDs and records qualitative scores linked to a wetland region.

### User Journeys
1. **Citizen Reporter (USSD/WhatsApp)**:
   - Enters pollution incident data.
   - Selects "Mara Basin".
   - System successfully creates a `datapoint` linked to a `basin_id` pointing to the Mara Basin UUID (with `wetland_id` and `site_id` as NULL).
2. **Citizen Scientist (Kobo Ingestion)**:
   - System receives a KoboCollect survey payload.
   - If the site UUID is missing or null, the system rejects the submission with a validation error.
   - If valid, the system inserts the `datapoint` with `site_id` set to the site's UUID (with `basin_id` and `wetland_id` as NULL).

---

## III. Scope Guardrails

### Must-Have
- **Polymorphic Ingestion Headers (`datapoint`)**: A header table storing submission metadata, status (`PENDING`, `APPROVED`, `REJECTED`), submitter details, geo coordinates, and version.
- **Polymorphic Foreign Keys**: Three foreign keys (`basin_id`, `wetland_id`, `site_id`) pointing to their respective spatial references.
- **Mutual Exclusivity Constraint**: A PostgreSQL CHECK constraint ensuring exactly one of these foreign keys is populated.
- **Generic Values Store (`answer`)**: An EAV value table capable of storing floats, text, and JSON lists, mapping back to a `datapoint` and a `question`.
- **Composite Index**: Unique index on `(datapoint_id, question_id, index)` to prevent duplicates and accelerate logic engine queries.
- **Identity & Access Model (`users` table)**: Store internal staff (Admin/Reviewer) and external Partners securely.

### Out of Scope
- Actually processing the incoming HTTP payloads from KoboToolbox or Africa's Talking API (deferred to ingestion integration task).
- Defuzzification / Fuzzy logic scoring updates (deferred to scoring pipeline task).
- Integrated Google/Microsoft SSO login flow middleware (handled in auth integration phase).

---

## IV. Acceptance Criteria

### User Acceptance Criteria (UAC)
- **UAC-2.1**: The system successfully saves a USSD pollution report linked to the "Mara Basin" without requiring a specific site or wetland.
- **UAC-2.2**: The system strictly rejects any monthly KoboCollect sampling submission that does not include a valid, non-null `site_id`.
- **UAC-5.1**: The system can verify if a user logging in via Google SSO has been invited by checking if their email exists in the database and retrieving their assigned role (Admin or Reviewer).
- **UAC-5.2**: The system supports standard email/password authentication for the "Partner" role with a hashed password, while allowing password fields to be nullable/blank for SSO-based Admin and Reviewer accounts.

### Technical Acceptance Criteria (TAC)
- **TAC-2.1**: Implement a database `CHECK` constraint enforcing that exactly one of `basin_id`, `wetland_id`, or `site_id` is NOT NULL:
  ```sql
  CHECK ( (basin_id IS NOT NULL)::int + (wetland_id IS NOT NULL)::int + (site_id IS NOT NULL)::int = 1 )
  ```
- **TAC-2.2**: Implement custom validators on schemas/routes to validate context constraints (e.g., if a form is of type "Kobo Survey", `site_id` must be populated).
- **TAC-2.3**: Implement a composite index on `(datapoint_id, question_id)` or `(datapoint_id, question_id, index)` within the answers table to prevent performance degradation when scoring logic executes.
- **TAC-5.1**: Define the `users` table schema:
  - `id` (UUID, Primary Key, defaults to uuid4)
  - `email` (String, Unique, Indexed, NOT NULL)
  - `role` (String/Enum: 'Admin', 'Reviewer', 'Partner', NOT NULL)
  - `organization` (String, nullable)
  - `password_hash` (String, Nullable)
  - `is_active` (Boolean, default=True)
- **TAC-5.2**: Do not store Citizen phone numbers in the `users` table to isolate reviewer/staff identities from public citizen PII. Phone numbers are stored alongside their submissions in the spatial or data points tables.
