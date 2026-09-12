import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings.base import EmbeddingProvider
from app.ai.embeddings.service import get_embedding_provider
from app.ai.rag.chunking import chunk_pages
from app.ai.rag.parsers import get_parser_for
from app.ai.vectorstore.base import EmbeddingRecord
from app.ai.vectorstore.service import get_vector_store
from app.core.exceptions import ValidationFailedError
from app.db.session import SessionLocal
from app.models.document_chunk import DocumentChunk
from app.models.enums import MaterialStatus
from app.models.material import Material
from app.storage.local import get_storage_backend

logger = logging.getLogger(__name__)


async def ingest_material(
    db: Session, material: Material, file_bytes: bytes, embedding_provider: EmbeddingProvider | None = None
) -> None:
    """Runs the full RAG ingestion pipeline for one material: parse -> clean/chunk
    -> embed -> store vectors. Mutates `material.status` in place and commits; never
    raises past its own boundary so a bad upload can't take down the background task
    runner, it just leaves the material in `failed` with an explanation."""

    try:
        provider = embedding_provider or get_embedding_provider()
        parser = get_parser_for(material.file_type)
        pages = parser.parse(file_bytes)
        chunks = chunk_pages(pages)

        if not chunks:
            raise ValidationFailedError(
                "No extractable text was found in this file. It may be empty, "
                "scanned without OCR-friendly quality, or corrupted."
            )

        db.query(DocumentChunk).filter(DocumentChunk.material_id == material.id).delete()

        chunk_rows = [
            DocumentChunk(
                material_id=material.id,
                user_id=material.user_id,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                section=chunk.section,
                content=chunk.content,
            )
            for chunk in chunks
        ]
        db.add_all(chunk_rows)
        db.flush()  # assign ids without committing yet

        embeddings = await provider.embed_documents([row.content for row in chunk_rows])

        vector_store = get_vector_store(db)
        vector_store.add_many(
            [
                EmbeddingRecord(
                    chunk_id=row.id,
                    material_id=material.id,
                    user_id=material.user_id,
                    embedding=embedding,
                )
                for row, embedding in zip(chunk_rows, embeddings, strict=True)
            ],
            commit=False,
        )

        material.status = MaterialStatus.READY
        material.processing_error = None
        db.add(material)
        db.commit()

    except Exception as exc:
        db.rollback()
        logger.exception("Material ingestion failed for material_id=%s", material.id)
        material.status = MaterialStatus.FAILED
        material.processing_error = f"{type(exc).__name__}: {str(exc)[:500]}"
        db.add(material)
        db.commit()


async def run_ingestion_for_material(material_id: str) -> None:
    """Entry point for background-task execution: owns its own DB session since it
    runs after the originating HTTP request has already returned."""

    db = SessionLocal()
    try:
        result = db.execute(select(Material).where(Material.id == material_id).with_for_update())
        material = result.scalar_one_or_none()
        if material is None:
            logger.warning("run_ingestion_for_material: material %s not found", material_id)
            return

        if material.status == MaterialStatus.PROCESSING:
            logger.info("run_ingestion_for_material: material %s already PROCESSING, skipping", material_id)
            return

        material.status = MaterialStatus.PROCESSING
        db.add(material)
        db.commit()

        try:
            storage = get_storage_backend()
            file_bytes = storage.read(material.storage_path)
        except Exception as exc:
            logger.exception("Failed to read storage for material %s", material_id)
            material.status = MaterialStatus.FAILED
            material.processing_error = f"Failed to read stored file: {exc}"
            db.add(material)
            db.commit()
            return

        await ingest_material(db, material, file_bytes)
    finally:
        db.close()
