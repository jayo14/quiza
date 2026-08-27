from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from sqlalchemy.orm import Session

from app.ai.rag.ingestion import run_ingestion_for_material
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.material import MaterialRead
from app.services import material_service

router = APIRouter(prefix="/materials", tags=["materials"])


@router.post("", response_model=MaterialRead, status_code=201)
async def upload_material(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    title: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaterialRead:
    content = await file.read()
    material = material_service.create_material(
        db,
        user=current_user,
        filename=file.filename or "upload",
        content_type=file.content_type,
        content=content,
        title=title,
    )
    # Parsing, chunking, embedding, and vector storage all happen off the request
    # thread so upload latency doesn't scale with document size or AI provider RTT.
    background_tasks.add_task(run_ingestion_for_material, material.id)
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
