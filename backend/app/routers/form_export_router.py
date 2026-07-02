import traceback
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.form_export import FormExportService
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/api/v1")


@router.get(
    "/forms/{form_id}/export/json",
    dependencies=[Depends(get_current_user)],
)
def export_form_json(
    form_id: int,
    draft: bool = False,
    db: Session = Depends(get_db),
):
    try:
        blueprint = FormExportService.generate_blueprint_json(
            db, form_id, draft
        )
        return blueprint
    except ValueError as e:
        print(f"export_form_json ValueError: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        print(f"export_form_json unexpected error: {type(e).__name__} - {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/forms/{form_id}/export/xlsform",
    dependencies=[Depends(get_current_user)],
)
def export_form_xlsform(
    form_id: int,
    draft: bool = False,
    db: Session = Depends(get_db),
):
    try:
        file_stream = FormExportService.generate_xlsform(db, form_id, draft)
        filename = f"form_{form_id}_xlsform.xlsx"
        headers = {"Content-Disposition": f"attachment; filename={filename}"}
        return StreamingResponse(
            file_stream,
            media_type="application/vnd.openpyxlformats-officedocument"
            ".spreadsheetml.sheet",
            headers=headers,
        )
    except ValueError as e:
        print(f"export_form_xlsform ValueError: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        print(
            f"export_form_xlsform unexpected error: {type(e).__name__} - {e}"
        )
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/reference/spatial-cascade/csv",
    dependencies=[Depends(get_current_user)],
)
def export_spatial_cascade_csv(db: Session = Depends(get_db)):
    try:
        output = FormExportService.generate_spatial_cascade_csv(db)
        headers = {
            "Content-Disposition": "attachment; filename=spatial_cascade.csv"
        }
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers=headers,
        )
    except Exception as e:
        print(f"export_spatial_cascade_csv error: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
