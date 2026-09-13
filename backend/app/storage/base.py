from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """Abstraction over where uploaded files physically live. The rest of the app
    only deals in opaque storage keys/paths so this can be swapped for S3 or
    similar without touching callers."""

    @abstractmethod
    def save(self, *, key: str, content: bytes, bucket: str | None = None) -> str:
        """Persist `content` under `key` and return the storage path/URL to record."""
        raise NotImplementedError

    @abstractmethod
    def read(self, path: str, bucket: str | None = None) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def delete(self, path: str, bucket: str | None = None) -> None:
        raise NotImplementedError
