import os
from pathlib import Path

from app.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    def __init__(self, root_dir: str) -> None:
        self._root = Path(root_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        # Prevent path traversal outside the storage root regardless of how `path`
        # was constructed upstream.
        resolved = (self._root / path).resolve()
        if not str(resolved).startswith(str(self._root.resolve())):
            raise ValueError("Resolved path escapes the storage root.")
        return resolved

    def save(self, *, key: str, content: bytes) -> str:
        destination = self._resolve(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return key

    def read(self, path: str) -> bytes:
        return self._resolve(path).read_bytes()

    def delete(self, path: str) -> None:
        resolved = self._resolve(path)
        if resolved.exists():
            os.remove(resolved)


def get_storage_backend() -> StorageBackend:
    from app.core.config import settings

    if settings.storage_backend == "local":
        return LocalStorageBackend(settings.storage_dir)
    if settings.storage_backend == "supabase":
        from app.storage.supabase import SupabaseStorageBackend

        return SupabaseStorageBackend()
    raise ValueError(f"Unsupported storage backend: {settings.storage_backend}")
