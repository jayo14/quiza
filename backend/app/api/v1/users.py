import uuid

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.user import UserRead
from app.storage.local import get_storage_backend

router = APIRouter(prefix="/users", tags=["users"])

PROFILE_IMAGES_BUCKET = "profile-images"


@router.get("/me", response_model=UserRead)
def get_my_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.put("/me", response_model=UserRead)
def update_my_profile(
    name: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if name is not None:
        current_user.name = name
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/avatar", response_model=UserRead)
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="File must be a JPEG, PNG, WebP, or GIF image.")

    max_size = 5 * 1024 * 1024  # 5MB
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="Image must be under 5 MB.")

    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
    key = f"avatars/{current_user.id}/{uuid.uuid4().hex}.{ext}"

    from app.core.config import settings
    supa_url = settings.effective_supabase_url
    if not supa_url:
        raise HTTPException(status_code=500, detail="Storage is not configured.")

    storage = get_storage_backend()

    # Delete old avatar if exists
    if current_user.profile_image:
        try:
            old_path = current_user.profile_image.split(f"/{PROFILE_IMAGES_BUCKET}/")[-1]
            if old_path and old_path != key:
                storage.delete(old_path, bucket=PROFILE_IMAGES_BUCKET)
        except Exception:
            pass

    # Upload new avatar
    storage.save(key=key, content=content, bucket=PROFILE_IMAGES_BUCKET)

    # Build public URL
    public_url = f"{supa_url}/storage/v1/object/public/{PROFILE_IMAGES_BUCKET}/{key}"

    current_user.profile_image = public_url
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user
