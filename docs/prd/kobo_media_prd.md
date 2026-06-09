# PRD — KoboToolbox Media Extraction & Cloud Offloading

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: PM + Engineering Lead | Target Location: `docs/prd/kobo_media_prd.md` | References: `docs/product_brief.md`
> Status: `Draft — Awaiting Approval`

---

## 1. Overview & Goal

### Problem Statement
The NBD Citizen-Led Wetland Monitoring Platform relies on citizen scientists submitting environmental data, including geotagged photographs, via KoboCollect. To prevent local VM storage exhaustion (limited to 30 GB), these image attachments must not be stored on the local filesystem. Instead, they must be streamed directly from KoboToolbox's public cloud endpoints to our private Google Cloud Storage (GCS) bucket.

Because GCS has a strict private access policy to protect data privacy, the platform must serve these media assets securely by generating 15-minute Time-To-Live (TTL) presigned read URLs whenever an authenticated Admin requests to view the submission photographs on the frontend.

### Core Metric
- **Zero Local Disk Overhead**: All images are streamed/written directly to GCS memory-safely without any permanent or temporary local disk write.
- **100% Secure Access**: Only authenticated Admins can fetch presigned URLs. No public URL exposure.

---

## 2. User Stories & Flows

### Persona
- **Platform Admin / Wetland Reviewer**: Needs to inspect the geotagged photo to verify the environmental conditions reported at a fixed monitoring site before approving the datapoint.

### UAC 3C.1
> Given a citizen scientist has uploaded a photo within a KoboCollect form,
> When the hourly backend worker synchronizes submissions from KoboToolbox,
> Then the photo attachment is automatically extracted, streamed to GCS under the environment-scoped path (`{APP_ENV}/kobo/{uuid}.{ext}`), and stored as a reference in the database (`Answer.name`).
> And when an authenticated Admin requests to view the photo, the FastAPI application generates a secure 15-minute signed URL.

---

## 3. Requirements (Scope Guardrails)

### Must-Have (v1)
- **FR-001**: Detect questions of type `image` or `attachment` during Kobo synchronization in `kobo.py`.
- **FR-002**: For each image/attachment answer, locate the corresponding item inside Kobo's `_attachments` array matching the question value (filename).
- **FR-003**: Fetch the image payload from Kobo's `download_url` using HTTP streaming with Kobo credentials (`Authorization: Token <token>`).
- **FR-004**: Stream the image directly to the GCS bucket under the centralized key path format: `{APP_ENV}/kobo/{uuid}.{ext}`.
- **FR-005**: Save the uploaded GCS blob path reference in the database in the `Answer.name` field.
- **FR-006**: Secure the `/api/v1/storage/presigned-read` endpoint to require authentication and restrict it to authenticated Admins (using the `RoleChecker(["Admin"])` dependency).
- **FR-007**: Raise an exception during sync if download or upload fails so that the record is routed to the Dead-Letter Queue (DLQ).

### Nice-to-Have (v2)
- Auto-extract EXIF GPS metadata from the image to cross-validate the submission's reported GPS coordinates.

### Out of Scope
- Direct image resizing or cropping on the backend.
- Public/unauthenticated reading of Kobo attachments.

---

## 4. Acceptance Criteria

### UAC 3C.1
- Given a Kobo submission with an image attachment, when synced:
  - The photo is downloaded and uploaded to GCS without writing to the local disk.
  - The GCS path matches the env prefix (e.g. `development/kobo/{uuid}.jpg`).
  - `Answer.name` stores the GCS path (e.g., `development/kobo/{uuid}.jpg`).
- Given an Admin requests a signed URL:
  - An authenticated Admin gets a valid 15-minute signed URL from the endpoint.
  - Unauthenticated or non-admin requests to retrieve the signed URL receive a `401 Unauthorized` or `403 Forbidden` response.

---

## 5. Epic & Ballpark Estimation

### Component Breakdown & Complexity Assessment

| Component | Task Description | Complexity | Ballpark Estimate |
|-----------|------------------|------------|-------------------|
| **Sync Worker** | Extract attachments list, stream download/upload to GCS | Medium | 3h |
| **Security & Routers** | Secure the presigned read router for authenticated Admins | Simple | 1h |
| **Testing** | Unit and mock integration tests for media sync and auth gates | Medium | 2h |
| **Total** | | | **~6h / 1 developer day** |
