from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings.base import EmbeddingProvider
from app.ai.embeddings.service import get_embedding_provider
from app.ai.vectorstore.service import get_vector_store
from app.models.document_chunk import DocumentChunk


async def retrieve_relevant_chunks(
    db: Session,
    *,
    user_id: str,
    query: str,
    material_id: str | None = None,
    top_k: int = 5,
    embedding_provider: EmbeddingProvider | None = None,
) -> list[DocumentChunk]:
    """Embeds `query` and returns the top-k most relevant chunks, always scoped to
    `user_id` at the vector-store level so retrieval can never cross into another
    student's material."""

    provider = embedding_provider or get_embedding_provider()
    query_embedding = await provider.embed_one(query)

    vector_store = get_vector_store(db)
    results = vector_store.search(
        query_embedding=query_embedding, user_id=user_id, top_k=top_k, material_id=material_id
    )
    if not results:
        return []

    chunk_ids = [r.chunk_id for r in results]
    # Belt-and-suspenders: re-assert ownership at the relational layer too, in case
    # a future vector store implementation ever forgets to filter correctly.
    rows = db.scalars(
        select(DocumentChunk).where(
            DocumentChunk.id.in_(chunk_ids), DocumentChunk.user_id == user_id
        )
    ).all()

    rows_by_id = {row.id: row for row in rows}
    ordered = [rows_by_id[cid] for cid in chunk_ids if cid in rows_by_id]
    return ordered
