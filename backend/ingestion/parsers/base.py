"""Base contract for file-type-specific parsers."""

from abc import ABC, abstractmethod
from pathlib import Path

from ..types import ParsedDocument


class DocumentParser(ABC):
    @abstractmethod
    def parse(self, path: Path) -> ParsedDocument:
        """Return cleaned text and source-aware blocks for one stored upload."""
