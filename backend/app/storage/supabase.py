from app.core.config import settings
from app.storage.base import StorageBackend


class SupabaseStorageBackend(StorageBackend):
    def __init__(
        self, url: str | None = None, key: str | None = None, bucket_name: str | None = None
    ) -> None:
        from supabase import create_client

        supa_url = url or settings.effective_supabase_url
        supa_key = key or settings.effective_supabase_key
        if not supa_url or not supa_key:
            raise ValueError(
                "SUPABASE_URL (or SUPBASE_URL) and SUPABASE_KEY (or SUPABASE_ANON_KEY) must be set when using Supabase storage backend."
            )
        self._client = create_client(supa_url, supa_key)
        self._bucket_name = bucket_name or settings.supabase_storage_bucket

    def save(self, *, key: str, content: bytes, bucket: str | None = None) -> str:
        self._client.storage.from_(bucket or self._bucket_name).upload(
            path=key,
            file=content,
            file_options={"upsert": "true"},
        )
        return key

    def read(self, path: str, bucket: str | None = None) -> bytes:
        return self._client.storage.from_(bucket or self._bucket_name).download(path)

    def delete(self, path: str, bucket: str | None = None) -> None:
        self._client.storage.from_(bucket or self._bucket_name).remove([path])
