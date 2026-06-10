# LLD — KoboToolbox Media Extraction & Cloud Offloading

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) | Target Location: `docs/lld/kobo_media_lld.md` | References: `docs/prd/kobo_media_prd.md`
> Status: `Approved`

---

## 1. Overview & Scope

**Component / Module**:
- `app.services.kobo` (`sync_kobo_submissions` extraction & download integration)
- `app.services.storage` (`StorageService`, `build_blob_path`, `stream_upload_async`)
- `app.routers.storage_router` (Securing `/api/v1/storage/presigned-read` endpoint)

**PRD References**:
- `docs/prd/kobo_media_prd.md` (FR-001 through FR-007)

---

## 2. Dynamic GCS Path & Data Flow

For Kobo media extraction, we reuse the centralized GCS path pattern:
```
{APP_ENV}/kobo/{uuid}.{ext}
```
where `pipeline` is set to `"kobo"`.

### Data Flow Execution

1. **Submission Attachment Discovery**:
   - For each `Question` with type `QuestionType.image` or `QuestionType.attachment`, check if the submission payload has a non-null answer (which is the filename, e.g. `image1.jpg`).
   - Look up the submission payload's `_attachments` array list to find the element where `filename` matches the question response value.

2. **Streaming Download/Upload**:
   - Use `httpx.stream("GET", download_url, headers=self.headers)` to open a streaming connection to Kobo.
   - Pass the response's async chunk generator directly to `StorageService().stream_upload_async(blob_name, chunks, content_type)`.
   - Ensure the download-and-upload runs entirely in memory without writing the file to the local disk.

3. **Database Reference Persistence**:
   - Save the generated GCS path (e.g. `development/kobo/{uuid}.{ext}`) as the `Answer.name` value.

---

## 3. Router Security Gate (RBAC Check)

The storage read endpoint in `app/routers/storage_router.py` must enforce Admin-level verification:

```python
from app.dependencies.auth import RoleChecker

@router.get("/presigned-read", response_model=PresignedReadResponse)
def get_read_url(
    blob_name: str = Query(..., description="The name of the blob file in the bucket"),
    current_user: User = Depends(RoleChecker(["Admin"])),
    service: StorageService = Depends(get_storage_service),
):
    ...
```

---

## 4. Error Handling & DLQ Isolation

- If a photo download from KoboToolbox or upload to GCS fails due to network timeout or auth error, the process must raise an exception.
- The outer submission loop will catch this exception, roll back the current nested transaction, create a `DeadLetter` quarantine record, and aggregate the sync error for email reporting to admins.
