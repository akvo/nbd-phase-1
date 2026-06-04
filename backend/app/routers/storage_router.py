from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.services.storage import StorageService

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
    service: StorageService = Depends(get_storage_service),
):
    try:
        url = service.generate_read_signed_url(blob_name)
        return PresignedReadResponse(read_url=url)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate read URL: {str(e)}"
        )
