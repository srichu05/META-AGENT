"""Data contracts shared across parsing, chunking, and storage components."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class ParsedBlock:
    text: str
    page_number: Optional[int] = None
    section_heading: Optional[str] = None


@dataclass(frozen=True)
class ParsedDocument:
    text: str
    blocks: List[ParsedBlock]


@dataclass(frozen=True)
class ChunkDraft:
    chunk_id: str
    content: str
    position: int
    page_number: Optional[int]
    section_heading: Optional[str]
    char_start: int
    char_end: int


@dataclass(frozen=True)
class StoredUpload:
    document_id: str
    filename: str
    stored_filename: str
    file_type: str
    storage_path: Path
