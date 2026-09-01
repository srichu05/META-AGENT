"""PostgreSQL metadata hydration for retrieved FAISS vector indices."""

import logging
from typing import Dict, List, Tuple

from flask import has_app_context

from models.document import Document, DocumentChunk
from .types import RetrievedChunk

logger = logging.getLogger(__name__)


def _query_chunks_by_indices(vector_indices: List[int]) -> List[DocumentChunk]:
    """Safely query DocumentChunk records, ensuring an active Flask app context if needed."""
    if not has_app_context():
        try:
            from app import app
            with app.app_context():
                return DocumentChunk.query.filter(DocumentChunk.vector_index.in_(vector_indices)).all()
        except Exception as err:
            logger.warning(f"Could not acquire Flask app context for MetadataLookup: {err}")
            return []
    return DocumentChunk.query.filter(DocumentChunk.vector_index.in_(vector_indices)).all()


class MetadataLookupService:
    """Hydrates vector search index results with relational PostgreSQL chunk and document metadata."""

    def hydrate(self, index_score_pairs: List[Tuple[int, float]], default_source: str = "faiss") -> List[RetrievedChunk]:
        """
        Bulk queries PostgreSQL for DocumentChunk & Document records matching vector indices.
        Preserves the ranking order of the input index_score_pairs.
        """
        if not index_score_pairs:
            return []

        index_to_score: Dict[int, float] = {idx: score for idx, score in index_score_pairs}
        vector_indices = list(index_to_score.keys())

        try:
            chunks = _query_chunks_by_indices(vector_indices)


            chunk_map: Dict[int, DocumentChunk] = {chunk.vector_index: chunk for chunk in chunks}
            hydrated: List[RetrievedChunk] = []

            for idx, score in index_score_pairs:
                db_chunk = chunk_map.get(idx)
                if db_chunk is None:
                    logger.warning(f"Vector index {idx} found in FAISS but missing in PostgreSQL database.")
                    continue

                doc = db_chunk.document
                hydrated.append(
                    RetrievedChunk(
                        chunk_id=db_chunk.id,
                        document_id=db_chunk.document_id,
                        filename=doc.filename if doc else "unknown",
                        file_type=doc.file_type if doc else "unknown",
                        page_number=db_chunk.page_number,
                        section_heading=db_chunk.section_heading,
                        char_start=db_chunk.char_start,
                        char_end=db_chunk.char_end,
                        vector_index=db_chunk.vector_index,
                        content=db_chunk.content,
                        score=score,
                        retrieval_source=default_source,
                        upload_timestamp=doc.uploaded_at.isoformat() if doc and doc.uploaded_at else None,
                    )
                )

            return hydrated
        except Exception as error:
            logger.exception(f"PostgreSQL metadata hydration failed: {error}")
            return []
