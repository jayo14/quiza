import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.material import Material
from app.models.user import User
from app.storage.local import get_storage_backend
from app.utils.file_validation import validate_upload
from app.ai.vectorstore.service import get_vector_store

def create_material(
    db: Session, *, user: User, filename: str, content_type: str | None, content: bytes, title: str | None
) -> Material:
    validated = validate_upload(filename=filename, content_type=content_type, size_bytes=len(content))

    storage = get_storage_backend()
    storage_key = f"materials/{user.id}/{uuid.uuid4().hex}_{filename}"
    storage_path = storage.save(key=storage_key, content=content)

    material = Material(
        user_id=user.id,
        filename=filename,
        file_type=validated.file_type,
        file_size=validated.size_bytes,
        title=title or filename,
        storage_path=storage_path,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def list_materials(db: Session, *, user: User) -> list[Material]:
    stmt = select(Material).where(Material.user_id == user.id).order_by(Material.created_at.desc())
    return list(db.scalars(stmt).all())


def get_owned_material(db: Session, *, user: User, material_id: str) -> Material:
    material = db.get(Material, material_id)
    # 404 (not 403) on a material owned by someone else, so ownership can't be
    # probed by enumerating ids.
    if not material or material.user_id != user.id:
        raise NotFoundError("Material not found.")
    return material


def delete_material(db: Session, *, user: User, material_id: str) -> None:
    material = get_owned_material(db, user=user, material_id=material_id)

    vector_store = get_vector_store(db)
    vector_store.delete_material(material_id=material.id, user_id=user.id, commit=False)

    storage = get_storage_backend()
    storage.delete(material.storage_path)

    for quiz in list(material.quizzes):
        db.delete(quiz)

    db.delete(material)
    db.commit()
