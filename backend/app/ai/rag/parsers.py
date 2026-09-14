import io
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.exceptions import ValidationFailedError


@dataclass(frozen=True)
class ParsedPage:
    page_number: int | None
    text: str


class DocumentParser(ABC):
    """Abstraction over turning raw file bytes into extracted text. Callers depend
    only on this interface, keyed off `file_type`, so a new format only needs a new
    implementation plus a registration in `get_parser_for`."""

    @abstractmethod
    def parse(self, content: bytes) -> list[ParsedPage]:
        raise NotImplementedError


class PdfParser(DocumentParser):
    def parse(self, content: bytes) -> list[ParsedPage]:
        import pymupdf  # PyMuPDF (fitz is deprecated)

        try:
            doc = pymupdf.open(stream=content, filetype="pdf")
        except Exception as exc:
            raise ValidationFailedError(f"Could not read PDF file: {exc}") from exc

        try:
            pages = [ParsedPage(page_number=i + 1, text=page.get_text()) for i, page in enumerate(doc)]
            return pages
        finally:
            doc.close()


class DocxParser(DocumentParser):
    def parse(self, content: bytes) -> list[ParsedPage]:
        import docx

        try:
            document = docx.Document(io.BytesIO(content))
        except Exception as exc:
            raise ValidationFailedError(f"Could not read DOCX file: {exc}") from exc

        text = "\n".join(p.text for p in document.paragraphs if p.text.strip())
        return [ParsedPage(page_number=None, text=text)]


class TxtParser(DocumentParser):
    def parse(self, content: bytes) -> list[ParsedPage]:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="replace")
        return [ParsedPage(page_number=None, text=text)]


class ImageParser(DocumentParser):
    """OCRs a single uploaded image via pytesseract. Requires the system `tesseract`
    binary; raises a clear, catchable error if it isn't installed rather than
    crashing the ingestion pipeline."""

    def parse(self, content: bytes) -> list[ParsedPage]:
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise ValidationFailedError("OCR dependencies are not installed.") from exc

        try:
            image = Image.open(io.BytesIO(content))
            text = pytesseract.image_to_string(image)
        except Exception as exc:
            raise ValidationFailedError(f"Could not OCR image: {exc}") from exc

        return [ParsedPage(page_number=None, text=text)]


_PARSERS: dict[str, type[DocumentParser]] = {
    "pdf": PdfParser,
    "docx": DocxParser,
    "doc": DocxParser,
    "txt": TxtParser,
    "image": ImageParser,
}


def get_parser_for(file_type: str) -> DocumentParser:
    parser_cls = _PARSERS.get(file_type)
    if not parser_cls:
        raise ValidationFailedError(f"No parser available for file type '{file_type}'.")
    return parser_cls()
