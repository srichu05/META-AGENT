"""Conservative text preprocessing that preserves mathematical notation."""

import re
import unicodedata
from typing import List


def clean_text(value: str) -> str:
    """Normalize Unicode and whitespace without rewriting equations or paragraphs."""
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))
    normalized = re.sub(r"[^\S\n]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def split_paragraphs(value: str) -> List[str]:
    """Return non-empty paragraphs while retaining intentional line breaks."""
    return [paragraph.strip() for paragraph in re.split(r"\n\s*\n", clean_text(value)) if paragraph.strip()]
