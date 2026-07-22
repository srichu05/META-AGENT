"""Parser for Markdown files with retained heading metadata."""

from pathlib import Path

from .base import DocumentParser
from .common import markdown_document


class MarkdownDocumentParser(DocumentParser):
    def parse(self, path: Path):
        return markdown_document(path.read_text(encoding="utf-8", errors="replace"))
