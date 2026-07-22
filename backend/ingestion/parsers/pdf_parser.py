"""PyMuPDF parser that retains page numbers for citations."""

from pathlib import Path

from ..cleaning import clean_text
from ..exceptions import DocumentParsingError
from ..types import ParsedBlock, ParsedDocument
from .base import DocumentParser


class PDFDocumentParser(DocumentParser):
    def parse(self, path: Path) -> ParsedDocument:
        try:
            import fitz
        except ImportError as error:
            raise DocumentParsingError("PyMuPDF is not installed.") from error

        try:
            source = fitz.open(path)
        except Exception as error:
            raise DocumentParsingError(f"Unable to open PDF: {error}") from error

        blocks = []
        try:
            for page_number, page in enumerate(source, start=1):
                text = clean_text(page.get_text("text"))
                if text:
                    blocks.append(ParsedBlock(text=text, page_number=page_number))
        finally:
            source.close()

        if not blocks:
            raise DocumentParsingError("The PDF did not contain extractable text.")
        return ParsedDocument(text="\n\n".join(block.text for block in blocks), blocks=blocks)
