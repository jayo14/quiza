from dataclasses import dataclass

from app.core.config import settings
from app.core.exceptions import ValidationFailedError

_EXTENSION_TO_FILE_TYPE = {
    ".pdf": "pdf",
    ".doc": "doc",
    ".docx": "docx",
    ".txt": "txt",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
}

_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "image/png",
    "image/jpeg",
}


@dataclass(frozen=True)
class ValidatedUpload:
    file_type: str
    size_bytes: int


def validate_upload(*, filename: str, content_type: str | None, size_bytes: int) -> ValidatedUpload:
    if size_bytes <= 0:
        raise ValidationFailedError("Uploaded file is empty.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise ValidationFailedError(
            f"File exceeds the maximum allowed size of {settings.max_upload_size_mb}MB."
        )

    suffix = _extension_of(filename)
    file_type = _EXTENSION_TO_FILE_TYPE.get(suffix)
    if not file_type:
        raise ValidationFailedError(
            f"Unsupported file extension '{suffix}'. Allowed: "
            f"{', '.join(sorted(_EXTENSION_TO_FILE_TYPE))}."
        )

    if content_type:
        mime = content_type.split(";")[0].strip().lower()
        if mime and mime != "application/octet-stream" and mime not in _ALLOWED_CONTENT_TYPES:
            raise ValidationFailedError(f"Unsupported content type '{content_type}'.")

    return ValidatedUpload(file_type=file_type, size_bytes=size_bytes)


def _extension_of(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()
