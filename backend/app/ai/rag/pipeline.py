from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ai.rag.retrieval import retrieve_relevant_chunks
from app.models.document_chunk import DocumentChunk

DEFAULT_MAX_CONTEXT_CHARS = 8000


@dataclass(frozen=True)
class RetrievedContext:
    text: str
    chunk_ids: list[str]
    source_references: list[str]
    has_context: bool = True


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

    seen_content: set[str] = set()
    source_counts: dict[str, int] = {}
    max_per_source = 2
    candidates: list[DocumentChunk] = []

    for chunk in chunks:
        normalized = chunk.content.strip()
        if normalized in seen_content:
            continue
        seen_content.add(normalized)
        ref = _reference_for(chunk)
        if source_counts.get(ref, 0) >= max_per_source:
            continue
        source_counts[ref] = source_counts.get(ref, 0) + 1
        candidates.append(chunk)

    parts: list[str] = []
    chunk_ids: list[str] = []
    references: list[str] = []
    total = 0

    for chunk in candidates:
        reference = _reference_for(chunk)
        piece = f"[Source: {reference}]\n{chunk.content}"
        if total + len(piece) > max_chars and parts:
            remaining = max_chars - total
            if remaining > 100:
                piece = piece[:remaining] + " [truncated]"
                parts.append(piece)
                total += len(piece)
            break
        parts.append(piece)
        chunk_ids.append(chunk.id)
        references.append(reference)
        total += len(piece)

    return RetrievedContext(
        text="\n\n".join(parts),
        chunk_ids=chunk_ids,
        source_references=references,
        has_context=bool(parts),
    )


async def get_context_for_query(
    db: Session,
    *,
    user_id: str,
    query: str,
    material_id: str | None = None,
    material_ids: list[str] | None = None,
    top_k: int = 5,
    max_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> RetrievedContext:
    all_raw = []
    if material_ids:
        per_k = max(top_k // len(material_ids), 3)
        for mid in material_ids:
            all_raw.extend(await retrieve_relevant_chunks(db, user_id=user_id, query=query, material_id=mid, top_k=per_k))
    elif material_id:
        all_raw = await retrieve_relevant_chunks(db, user_id=user_id, query=query, material_id=material_id, top_k=top_k)
    else:
        all_raw = await retrieve_relevant_chunks(db, user_id=user_id, query=query, top_k=top_k)
    all_raw.sort(key=lambda t: t[1], reverse=True)
    all_chunks = [chunk for chunk, _score in all_raw]
    return assemble_context(all_chunks, max_chars=max_chars)
