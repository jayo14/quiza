import uuid

from fastapi import APIRouter, Depends, UploadFile, File

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["users"])

PROFILE_IMAGES_BUCKET = "profile-images"


@router.get("/me", response_model=UserRead)
def get_my_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.put("/me", response_model=UserRead)
def update_my_profile(
    name: str | None = None,
    current_user: User = Depends(get_current_user),
) -> User:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        if name is not None:
            current_user.name = name
        db.add(current_user)
        db.commit()
        db.refresh(current_user)
        return current_user
    finally:
        db.close()


@router.post("/me/avatar", response_model=UserRead)
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> User:
    from app.db.session import SessionLocal

    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="File must be a JPEG, PNG, WebP, or GIF image.")

    max_size = 5 * 1024 * 1024  # 5MB
    content = await file.read()
    if len(content) > max_size:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Image must be under 5 MB.")

    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
    key = f"avatars/{current_user.id}/{uuid.uuid4().hex}.{ext}"

    db = SessionLocal()
    try:
        from supabase import create_client

        supa_url = settings.effective_supabase_url
        supa_key = settings.effective_supabase_key
        if not supa_url or not supa_key:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail="Storage is not configured.")

        client = create_client(supa_url, supa_key)

        # Create bucket if it doesn't exist
        try:
            client.storage.get_bucket(PROFILE_IMAGES_BUCKET)
        except Exception:
            try:
                client.storage.create_bucket(PROFILE_IMAGES_BUCKET, {"public": True})
            except Exception:
                pass  # bucket may already exist

        # Delete old avatar if exists
        if current_user.profile_image:
            try:
                old_path = current_user.profile_image.split(f"/{PROFILE_IMAGES_BUCKET}/")[-1]
                if old_path and old_path != key:
                    client.storage.from_(PROFILE_IMAGES_BUCKET).remove([old_path])
            except Exception:
                pass

        # Upload new avatar
        client.storage.from_(PROFILE_IMAGES_BUCKET).upload(
            path=key,
            file=content,
            file_options={"upsert": "true", "content-type": file.content_type},
        )

        # Build public URL
        public_url = f"{supa_url}/storage/v1/object/public/{PROFILE_IMAGES_BUCKET}/{key}"

        current_user.profile_image = public_url
        db.add(current_user)
        db.commit()
        db.refresh(current_user)
        return current_user
    finally:
        db.close()
