"""Isolated PaddleOCR integration for image-based learning materials."""

from pathlib import Path
from typing import List, Tuple

from .cleaning import clean_text
from .exceptions import DocumentParsingError


class PaddleOCREngine:
    """Extracts reading-order text from images using PaddleOCR's stable 2.x API."""

    def __init__(self, language: str = "en"):
        self.language = language
        self._ocr = None

    def extract_text(self, image_path: Path) -> str:
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
            except ImportError as error:
                raise DocumentParsingError("PaddleOCR is not installed.") from error
            self._ocr = PaddleOCR(use_angle_cls=True, lang=self.language, show_log=False)

        try:
            result = self._ocr.ocr(str(image_path), cls=True)
        except Exception as error:
            raise DocumentParsingError(f"OCR failed for image upload: {error}") from error

        lines: List[Tuple[float, float, str]] = []
        for page in result or []:
            for entry in page or []:
                if len(entry) < 2 or not entry[0] or not entry[1]:
                    continue
                points, recognition = entry[0], entry[1]
                text = clean_text(str(recognition[0]))
                if not text:
                    continue
                left = min(point[0] for point in points)
                top = min(point[1] for point in points)
                lines.append((top, left, text))

        lines.sort(key=lambda line: (line[0], line[1]))
        text = "\n".join(line[2] for line in lines)
        if not text:
            raise DocumentParsingError("No readable text was detected in the image.")
        return text
