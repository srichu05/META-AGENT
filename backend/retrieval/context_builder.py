"""Context assembly and citation extraction for retrieved document chunks."""

import logging
from typing import List, Tuple

from config import RAG_CONFIG
from .types import Citation, RetrievedChunk, RetrievedContext

logger = logging.getLogger(__name__)


class CitationBuilder:
    """Extracts uniform source attribution markers from retrieved chunks."""

    def build_citations(self, chunks: List[RetrievedChunk]) -> List[Citation]:
        citations: List[Citation] = []
        for chunk in chunks:
            location_parts = []
            if chunk.page_number is not None:
                location_parts.append(f"p. {chunk.page_number}")
            if chunk.section_heading:
                location_parts.append(f"section: {chunk.section_heading}")

            loc_str = f" ({', '.join(location_parts)})" if location_parts else ""
            citation_id = f"[{chunk.filename}{loc_str}]"

            snippet = chunk.content[:150] + "..." if len(chunk.content) > 150 else chunk.content
            citations.append(
                Citation(
                    citation_id=citation_id,
                    filename=chunk.filename,
                    file_type=chunk.file_type,
                    page_number=chunk.page_number,
                    section_heading=chunk.section_heading,
                    chunk_id=chunk.chunk_id,
                    snippet=snippet,
                )
            )
        return citations


class ContextBuilder:
    """Formats retrieved chunks into clean, prompt-ready context blocks within token/char budgets."""

    def __init__(self, max_context_length: int = None, citation_builder: CitationBuilder = None):
        self.max_context_length = max_context_length or RAG_CONFIG.get("max_context_length", 4000)
        self.citation_builder = citation_builder or CitationBuilder()

    def build_context(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        retrieval_time_ms: float = 0.0,
        hybrid_used: bool = False,
        rerank_used: bool = False,
    ) -> RetrievedContext:
        """Assembles structured prompt context and citations within character budget."""
        if not chunks:
            return RetrievedContext(
                query=query,
                formatted_context="No relevant document context found.",
                chunks=[],
                citations=[],
                total_chunks_retrieved=0,
                retrieval_time_ms=retrieval_time_ms,
                hybrid_used=hybrid_used,
                rerank_used=rerank_used,
            )

        citations = self.citation_builder.build_citations(chunks)
        formatted_blocks: List[str] = []
        current_len = 0
        accepted_chunks: List[RetrievedChunk] = []

        for chunk, citation in zip(chunks, citations):
            block = (
                f"--- Reference Document: {citation.citation_id} ---\n"
                f"File Type: {chunk.file_type} | Source: {chunk.retrieval_source} | Score: {chunk.score:.4f}\n"
                f"Content:\n{chunk.content.strip()}\n"
            )
            if current_len + len(block) > self.max_context_length and accepted_chunks:
                logger.info(f"Context length budget ({self.max_context_length} chars) reached. Truncating chunks.")
                break

            formatted_blocks.append(block)
            accepted_chunks.append(chunk)
            current_len += len(block)

        formatted_context = "\n".join(formatted_blocks)
        return RetrievedContext(
            query=query,
            formatted_context=formatted_context,
            chunks=accepted_chunks,
            citations=citations[: len(accepted_chunks)],
            total_chunks_retrieved=len(accepted_chunks),
            retrieval_time_ms=retrieval_time_ms,
            hybrid_used=hybrid_used,
            rerank_used=rerank_used,
        )
