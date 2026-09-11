import re
from dataclasses import dataclass

from app.ai.rag.parsers import ParsedPage

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150


@dataclass(frozen=True)
class Chunk:
    chunk_index: int
    content: str
    page_number: int | None
    section: str | None


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_pages(
    pages: list[ParsedPage],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Chunk]:
    """Clean and split parsed pages into overlapping character-based chunks, keeping
    each chunk tagged with the page (and best-effort section heading) it came from."""

    if chunk_overlap >= chunk_size:
        chunk_overlap = chunk_size // 4

    chunks: list[Chunk] = []
    index = 0

    for page in pages:
        text = clean_text(page.text)
        if not text:
            continue

        section = _guess_section(text)
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            piece = text[start:end]
            if end < len(text):
                piece = _refine_split(piece)
            piece = piece.strip()
            if piece:
                chunks.append(
                    Chunk(chunk_index=index, content=piece, page_number=page.page_number, section=section)
                )
                index += 1
            if end == len(text):
                break
            refined_len = len(piece)
            start = start + refined_len - chunk_overlap

    return chunks


def _refine_split(text: str) -> str:
    tail_200 = text[-200:]
    para_pos = tail_200.rfind("\n\n")
    if para_pos >= 0:
        return text[: -200 + para_pos]
    tail_100 = text[-100:]
    sent_pos = tail_100.rfind(". ")
    if sent_pos >= 0:
        return text[: -100 + sent_pos + 1]
    return text


def _guess_section(text: str) -> str | None:
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    if 0 < len(first_line) <= 100:
        return first_line
    return None
