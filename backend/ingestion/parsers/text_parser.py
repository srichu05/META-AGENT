"""Parser for UTF-8 text files."""

from pathlib import Path

from .base import DocumentParser
from .common import plain_text_document


class TextDocumentParser(DocumentParser):
    def parse(self, path: Path):
        return plain_text_document(path.read_text(encoding="utf-8", errors="replace"))
