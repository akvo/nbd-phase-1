# LLD — Submission Details & Moderation Management

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) / Amelia (Developer) | Target Location: `docs/lld/submission_details_management_lld.md`
> Initiative/Epic: Submission Details & Moderation Management

---

## 1. Backend REST API Routing (`backend/app/routers/admin_api.py`)

### 1.1 GET Submission details
- **Endpoint**: `GET /api/v1/admin/submissions/{id}`
- **Security**: Requires Admin/Reviewer authorization.
- **Description**: Returns all raw dynamic question fields, coordinate values, and user metadata for a single submission.

### 1.2 PUT Edit submission answers
- **Endpoint**: `PUT /api/v1/admin/submissions/{id}`
- **Request Schema**:
  ```python
  class UpdateSubmissionSchema(BaseModel):
      answers: List[AnswerInputSchema]
  ```
- **Description**: Updates the JSONB values of the answers inside the raw ingestion tables for that submission, then triggers scoring recalculations.

---

## 2. Frontend Layout & Components (`frontend/src/app/admin/data/`)

### 2.1 Expanded Row Detail Accordion
- Render inline detailed table when an admin clicks a row inside the admin workspace table:
  - Submitter profile card (Name, Phone number, Role).
  - Questionnaire answers table showing question title next to readable answer values.
  - Image preview container showing interactive GCS media thumbnails.

### 2.2 Confirmation Dialogs
- Add popup confirmation wrappers (e.g., using shadcn `<AlertDialog>`) for Approve, Reject, and Delete buttons.
- Display a clear warning and require user action to confirm the status modification.

### 2.3 Interactive Edit Form Route (`frontend/src/app/admin/data/edit/[submissionId]/`)
- Set up a new sub-page route that fetches the submission ID and form schema from the API.
- Mount the dynamic form component pre-filled with the current answers.
- Wire submission events to call the backend update PUT API and display success alerts.

---

## 3. Verification & Testing Plan
- Write integration tests in `tests/test_admin_api.py` validating the GET and PUT endpoints for submission details and editing actions.
- Verify UI component state constraints and confirm the active filters default to pending status sorted ascending.
