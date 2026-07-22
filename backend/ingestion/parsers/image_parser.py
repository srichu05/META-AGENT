"""Image parser backed by the isolated PaddleOCR engine."""

from pathlib import Path

from ..ocr import PaddleOCREngine
from ..types import ParsedBlock, ParsedDocument
from .base import DocumentParser


class ImageDocumentParser(DocumentParser):
    def __init__(self, ocr_engine=None):
        self.ocr_engine = ocr_engine or PaddleOCREngine()

    def parse(self, path: Path) -> ParsedDocument:
        text = self.ocr_engine.extract_text(path)
        return ParsedDocument(text=text, blocks=[ParsedBlock(text=text, page_number=1)])
