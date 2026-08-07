"""Retrieval service facade for executing complete RAG retrieval pipeline."""

import time
import logging
from typing import Optional

from config import SYSTEM_CONFIG
from .context_builder import ContextBuilder
from .hybrid import HybridRetriever
from .types import RetrievedContext

logger = logging.getLogger(__name__)


class RetrievalService:
    """High-level orchestration service for query retrieval, hybrid search, ranking, and context building."""

    def __init__(
        self,
        retriever: HybridRetriever = None,
        context_builder: ContextBuilder = None,
    ):
        self.retriever = retriever or HybridRetriever()
        self.context_builder = context_builder or ContextBuilder()

    def retrieve(self, query: str, top_k: Optional[int] = None) -> RetrievedContext:
        """
        Executes query retrieval pipeline:
        1. Embed Query (BGE)
        2. Vector Search (FAISS)
        3. Keyword Search (BM25)
        4. Reciprocal Rank Fusion & PostgreSQL Metadata Hydration
        5. Cohere Reranking (optional)
        6. Context Assembly & Citation Extraction
        Returns RetrievedContext object.
        """
        start_time = time.time()
        k = top_k or SYSTEM_CONFIG.get("top_k_retrieval", 5)

        logger.info(f"🔍 RetrievalService executing query: '{query[:80]}...' (top_k={k})")

        chunks, hybrid_used, rerank_used = self.retriever.retrieve(query, top_k=k)
        retrieval_time_ms = (time.time() - start_time) * 1000.0

        context = self.context_builder.build_context(
            query=query,
            chunks=chunks,
            retrieval_time_ms=retrieval_time_ms,
            hybrid_used=hybrid_used,
            rerank_used=rerank_used,
        )

        logger.info(
            f"✅ RetrievalService completed in {retrieval_time_ms:.1f}ms: "
            f"retrieved {context.total_chunks_retrieved} chunk(s), hybrid={hybrid_used}, rerank={rerank_used}"
        )
        return context
