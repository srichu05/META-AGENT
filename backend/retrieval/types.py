"""Data types and value objects for the Draft 2 retrieval pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class RetrievedChunk:
    """A single retrieved document chunk hydrated with database metadata and score."""

    chunk_id: str
    document_id: str
    filename: str
    file_type: str
    page_number: Optional[int]
    section_heading: Optional[str]
    char_start: int
    char_end: int
    vector_index: int
    content: str
    score: float
    retrieval_source: str = "faiss"  # "faiss", "bm25", or "hybrid"
    upload_timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "page_number": self.page_number,
            "section_heading": self.section_heading,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "vector_index": self.vector_index,
            "content": self.content,
            "score": round(float(self.score), 4),
            "retrieval_source": self.retrieval_source,
            "upload_timestamp": self.upload_timestamp,
        }


@dataclass
class Citation:
    """Source attribution object mapping generated context to document origin."""

    citation_id: str  # e.g., "[Doc: calculus_notes.pdf, p. 3]"
    filename: str
    file_type: str
    page_number: Optional[int]
    section_heading: Optional[str]
    chunk_id: str
    snippet: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "citation_id": self.citation_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "page_number": self.page_number,
            "section_heading": self.section_heading,
            "chunk_id": self.chunk_id,
            "snippet": self.snippet,
        }


@dataclass
class RetrievedContext:
    """Complete retrieved context package ready for solver prompt consumption."""

    query: str
    formatted_context: str
    chunks: List[RetrievedChunk] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    total_chunks_retrieved: int = 0
    retrieval_time_ms: float = 0.0
    hybrid_used: bool = False
    rerank_used: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "query": self.query,
            "formatted_context": self.formatted_context,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "citations": [citation.to_dict() for citation in self.citations],
            "total_chunks_retrieved": self.total_chunks_retrieved,
            "retrieval_time_ms": round(float(self.retrieval_time_ms), 2),
            "hybrid_used": self.hybrid_used,
            "rerank_used": self.rerank_used,
        }
