from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
import os
from pydantic import BaseModel
from app.services.storage import StorageService
from app.dependencies.auth import RoleChecker
from app.models.user import User

router = APIRouter(prefix="/api/v1/storage", tags=["storage"])


class PresignedUploadRequest(BaseModel):
    file_name: str
    content_type: str


class PresignedUploadResponse(BaseModel):
    upload_url: str
    blob_name: str


class PresignedReadResponse(BaseModel):
    read_url: str


def get_storage_service() -> StorageService:
    try:
        return StorageService()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Storage configuration error: {str(e)}"
        )


@router.post("/presigned-upload", response_model=PresignedUploadResponse)
def get_upload_url(
    payload: PresignedUploadRequest,
    current_user: User = Depends(RoleChecker(["Admin"])),
    service: StorageService = Depends(get_storage_service),
):
    try:
        url = service.generate_upload_signed_url(
            payload.file_name, payload.content_type
        )
        return PresignedUploadResponse(
            upload_url=url, blob_name=payload.file_name
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate upload URL: {str(e)}"
        )


@router.get("/presigned-read", response_model=PresignedReadResponse)
def get_read_url(
    blob_name: str = Query(
        ..., description="The name of the blob file in the bucket"
    ),
    current_user: User = Depends(RoleChecker(["Admin"])),
    service: StorageService = Depends(get_storage_service),
):
    try:
        url = service.generate_read_signed_url(blob_name)
        return PresignedReadResponse(read_url=url)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate read URL: {str(e)}"
        )


@router.put("/upload/{blob_name:path}")
async def upload_file_binary(
    blob_name: str,
    request: Request,
    expires: int = Query(..., description="Expiration epoch timestamp"),
    signature: str = Query(..., description="HMAC-SHA256 signature"),
    service: StorageService = Depends(get_storage_service),
):
    # Verify HMAC signature and expiration
    import time

    if int(time.time()) > expires:
        raise HTTPException(
            status_code=403, detail="Request signature has expired"
        )

    if not service.verify_signature(blob_name, expires, signature):
        raise HTTPException(
            status_code=403, detail="Invalid request signature"
        )

    try:
        body = await request.body()
        content_type = request.headers.get(
            "content-type", "application/octet-stream"
        )
        service.upload_file(body, blob_name, content_type)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to write file to disk: {str(e)}"
        )


@router.get("/files/{blob_name:path}")
def get_file(
    blob_name: str,
    expires: int = Query(..., description="Expiration epoch timestamp"),
    signature: str = Query(..., description="HMAC-SHA256 signature"),
    service: StorageService = Depends(get_storage_service),
):
    # Verify HMAC signature and expiration
    import time

    if int(time.time()) > expires:
        raise HTTPException(
            status_code=403, detail="Request signature has expired"
        )

    if not service.verify_signature(blob_name, expires, signature):
        raise HTTPException(
            status_code=403, detail="Invalid request signature"
        )

    file_path = service.get_file_path(blob_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)
