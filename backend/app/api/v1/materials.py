from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

MAX_UPLOAD_SIZE = 25 * 1024 * 1024

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.material import MaterialRead
from app.services import material_service

router = APIRouter(prefix="/materials", tags=["materials"])


@router.post("", response_model=MaterialRead, status_code=201)
async def upload_material(
    file: UploadFile,
    title: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaterialRead:
    if file.size and file.size > MAX_UPLOAD_SIZE:
        from app.core.exceptions import ValidationFailedError
        raise ValidationFailedError(f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024*1024)} MB.")

    content = await file.read()

    if len(content) > MAX_UPLOAD_SIZE:
        from app.core.exceptions import ValidationFailedError
        raise ValidationFailedError(f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024*1024)} MB.")

    material = material_service.create_material(
        db,
        user=current_user,
        filename=file.filename or "upload",
        content_type=file.content_type,
        content=content,
        title=title,
    )

    # Trigger ingestion immediately via Celery
    try:
        from app.tasks import ingest_material_task
        ingest_material_task.delay(material.id)
    except Exception:
        # If Celery/Redis unavailable, ingestion will happen on quiz generation
        pass

    return material


@router.get("", response_model=list[MaterialRead])
def list_materials(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[MaterialRead]:
    return material_service.list_materials(db, user=current_user)


@router.get("/{material_id}", response_model=MaterialRead)
def get_material(
    material_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MaterialRead:
    return material_service.get_owned_material(db, user=current_user, material_id=material_id)


@router.delete("/{material_id}", status_code=204)
def delete_material(
    material_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    material_service.delete_material(db, user=current_user, material_id=material_id)
