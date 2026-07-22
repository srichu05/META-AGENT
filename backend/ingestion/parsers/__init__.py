"""Independent document parsers and a file-type registry."""

from .docx_parser import DOCXDocumentParser
from .image_parser import ImageDocumentParser
from .markdown_parser import MarkdownDocumentParser
from .pdf_parser import PDFDocumentParser
from .text_parser import TextDocumentParser


class DocumentParserRegistry:
    """Selects a parser without coupling upload storage to parsing behavior."""

    def __init__(self):
        self.parsers = {
            "pdf": PDFDocumentParser(),
            "docx": DOCXDocumentParser(),
            "txt": TextDocumentParser(),
            "markdown": MarkdownDocumentParser(),
            "image": ImageDocumentParser(),
        }

    def get_parser(self, file_type):
        return self.parsers[file_type]


__all__ = ["DocumentParserRegistry"]
