from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ai.rag.retrieval import retrieve_relevant_chunks
from app.models.document_chunk import DocumentChunk

DEFAULT_MAX_CONTEXT_CHARS = 6000


@dataclass(frozen=True)
class RetrievedContext:
    text: str
    chunk_ids: list[str]
    source_references: list[str]


def _reference_for(chunk: DocumentChunk) -> str:
    if chunk.page_number is not None:
        return f"page {chunk.page_number}"
    if chunk.section:
        return chunk.section
    return f"chunk {chunk.chunk_index}"


def assemble_context(
    chunks: list[DocumentChunk], *, max_chars: int = DEFAULT_MAX_CONTEXT_CHARS
) -> RetrievedContext:
    """Formats retrieved chunks into a single LLM-ready context block, each chunk
    tagged with a citeable source reference, truncated to a character budget."""

    parts: list[str] = []
    chunk_ids: list[str] = []
    references: list[str] = []
    total = 0

    for chunk in chunks:
        reference = _reference_for(chunk)
        piece = f"[Source: {reference}]\n{chunk.content}"
        if total + len(piece) > max_chars and parts:
            break
        parts.append(piece)
        chunk_ids.append(chunk.id)
        references.append(reference)
        total += len(piece)

    return RetrievedContext(text="\n\n".join(parts), chunk_ids=chunk_ids, source_references=references)


async def get_context_for_query(
    db: Session,
    *,
    user_id: str,
    query: str,
    material_id: str | None = None,
    top_k: int = 5,
    max_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> RetrievedContext:
    chunks = await retrieve_relevant_chunks(
        db, user_id=user_id, query=query, material_id=material_id, top_k=top_k
    )
    return assemble_context(chunks, max_chars=max_chars)
