"""Context Manager service - Deduplicates, organizes, and formats retrieved RAG context for solvers."""

import hashlib
import logging
from typing import Any, Dict, List, Set, Tuple

from config import RAG_CONFIG
from retrieval.types import Citation, RetrievedChunk, RetrievedContext

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages retrieved document context: deduplication, filtering, token management, and prompt formatting."""

    def __init__(self, max_context_length: int = None):
        self.max_context_length = max_context_length or RAG_CONFIG.get("max_context_length", 4000)

    def process_context(
        self,
        retrieved_context: RetrievedContext,
        query: str = "",
        min_score_threshold: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Deduplicates, filters, and formats raw retrieved chunks into a clean, solver-ready context package.
        """
        if not retrieved_context or not retrieved_context.chunks:
            logger.info("ContextManager: No retrieved chunks to process.")
            return {
                "formatted_context": "No relevant document context found.",
                "chunks": [],
                "citations": [],
                "total_chunks_processed": 0,
                "deduplicated_count": 0,
                "filtered_count": 0,
            }

        raw_chunks = retrieved_context.chunks
        initial_count = len(raw_chunks)

        # 1. Deduplication by chunk_id, vector_index, or content hash
        unique_chunks: List[RetrievedChunk] = []
        seen_ids: Set[str] = set()
        seen_hashes: Set[str] = set()

        for chunk in raw_chunks:
            # Check unique ID
            if chunk.chunk_id in seen_ids or chunk.vector_index in seen_ids:
                continue

            # Check content hash
            content_hash = hashlib.md5(chunk.content.strip().encode("utf-8")).hexdigest()
            if content_hash in seen_hashes:
                continue

            seen_ids.add(chunk.chunk_id)
            seen_ids.add(str(chunk.vector_index))
            seen_hashes.add(content_hash)
            unique_chunks.append(chunk)

        deduplicated_count = initial_count - len(unique_chunks)

        # 2. Score threshold filtering
        filtered_chunks = [c for c in unique_chunks if c.score >= min_score_threshold]
        filtered_count = len(unique_chunks) - len(filtered_chunks)
        if not filtered_chunks:
            filtered_chunks = unique_chunks  # Fallback if all were below threshold

        # 3. Sort by score descending
        filtered_chunks.sort(key=lambda c: c.score, reverse=True)

        # 4. Context Budget & Prompt Formatting
        formatted_blocks: List[str] = []
        citations: List[Dict[str, Any]] = []
        accepted_chunks: List[RetrievedChunk] = []
        current_length = 0

        for idx, chunk in enumerate(filtered_chunks, start=1):
            location_str = ""
            if chunk.page_number is not None:
                location_str += f" (p. {chunk.page_number})"
            if chunk.section_heading:
                location_str += f" [section: {chunk.section_heading}]"

            citation_label = f"[{chunk.filename}{location_str}]"
            block = (
                f"--- Reference Context #{idx} {citation_label} ---\n"
                f"File: {chunk.filename} | Type: {chunk.file_type} | Similarity Score: {chunk.score:.4f}\n"
                f"Content:\n{chunk.content.strip()}\n"
            )

            if current_length + len(block) > self.max_context_length and accepted_chunks:
                logger.info(f"ContextManager: Reached length limit ({self.max_context_length} chars). Truncating remaining chunks.")
                break

            formatted_blocks.append(block)
            accepted_chunks.append(chunk)
            current_length += len(block)

            snippet = chunk.content[:150] + "..." if len(chunk.content) > 150 else chunk.content
            citations.append({
                "citation_id": citation_label,
                "filename": chunk.filename,
                "file_type": chunk.file_type,
                "page_number": chunk.page_number,
                "section_heading": chunk.section_heading,
                "chunk_id": chunk.chunk_id,
                "snippet": snippet,
            })

        formatted_context_string = "\n".join(formatted_blocks) if formatted_blocks else "No relevant document context found."

        logger.info(
            f"ContextManager: Processed {initial_count} chunks → {len(accepted_chunks)} accepted "
            f"(deduped: {deduplicated_count}, filtered: {filtered_count}, length: {current_length} chars)."
        )

        return {
            "formatted_context": formatted_context_string,
            "chunks": [c.to_dict() for c in accepted_chunks],
            "citations": citations,
            "total_chunks_processed": len(accepted_chunks),
            "deduplicated_count": deduplicated_count,
            "filtered_count": filtered_count,
            "character_count": current_length,
        }
