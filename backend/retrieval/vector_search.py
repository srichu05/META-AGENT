"""FAISS vector search engine for query embedding & similarity index matching."""

import logging
from typing import List, Tuple

import numpy as np

from config import INGESTION_CONFIG, SYSTEM_CONFIG
from ingestion.embeddings import BGEEmbeddingService
from ingestion.faiss_store import FAISSVectorStore

logger = logging.getLogger(__name__)


class FAISSQueryEngine:
    """Generates query embeddings and executes FAISS inner-product vector search."""

    def __init__(
        self,
        vector_store: FAISSVectorStore = None,
        embedding_service: BGEEmbeddingService = None,
    ):
        self.vector_store = vector_store or FAISSVectorStore(
            INGESTION_CONFIG["faiss_index_path"],
            SYSTEM_CONFIG["embedding_dimension"],
        )
        self.embedding_service = embedding_service or BGEEmbeddingService(
            SYSTEM_CONFIG["embedding_model"],
            INGESTION_CONFIG["embedding_batch_size"],
            SYSTEM_CONFIG["embedding_dimension"],
        )

    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        """
        Embed query and perform FAISS similarity search.
        Returns list of (vector_index, score) tuples.
        """
        if not query or not query.strip():
            return []

        if self.vector_store.vector_count == 0:
            logger.info("FAISS vector store is empty. Returning 0 vector results.")
            return []

        try:
            query_vector = self.embedding_service.generate([query.strip()])
            scores, indices = self.vector_store.search(query_vector, top_k=top_k)

            results: List[Tuple[int, float]] = []
            if indices.size > 0 and scores.size > 0:
                for idx, score in zip(indices[0], scores[0]):
                    if idx >= 0:
                        results.append((int(idx), float(score)))

            return results
        except Exception as error:
            logger.exception(f"FAISS vector search failed for query '{query[:50]}...': {error}")
            return []
