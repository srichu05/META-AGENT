"""Citation-ready metadata construction for document chunks."""

from datetime import datetime
from typing import Dict, Iterable, List

from .types import ChunkDraft


def build_chunk_metadata(
    document_id: str,
    filename: str,
    file_type: str,
    uploaded_at: datetime,
    chunks: Iterable[ChunkDraft],
) -> List[Dict[str, object]]:
    """Build uniform metadata without coupling chunking to persistence."""
    timestamp = uploaded_at.isoformat()
    return [
        {
            "document_id": document_id,
            "chunk_id": chunk.chunk_id,
            "filename": filename,
            "file_type": file_type,
            "page_number": chunk.page_number,
            "section_heading": chunk.section_heading,
            "upload_timestamp": timestamp,
            "chunk_position": chunk.position,
            "char_start": chunk.char_start,
            "char_end": chunk.char_end,
        }
        for chunk in chunks
    ]
