"""Retrieval service facade for executing complete RAG retrieval pipeline."""

import logging
import os
import time
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

    def retrieve(self, query: str, top_k: Optional[int] = None, user_id: Optional[str] = None) -> RetrievedContext:
        """
        Executes query retrieval pipeline:
        1. Embed Query (BGE)
        2. Vector Search (FAISS)
        3. Keyword Search (BM25)
        4. Reciprocal Rank Fusion & PostgreSQL Metadata Hydration
        5. User Authorization & Chunk Isolation
        6. Cohere Reranking (optional)
        7. Context Assembly & Citation Extraction
        Returns RetrievedContext object.
        """
        start_time = time.time()
        max_k = int(os.getenv("MAX_TOP_K", "50"))
        requested_k = top_k or SYSTEM_CONFIG.get("top_k_retrieval", 5)
        k = max(1, min(requested_k, max_k))

        # Resolve user context for tenant / ownership retrieval filtering
        effective_user_id = user_id
        if effective_user_id is None:
            try:
                from security.auth import get_current_user
                user = get_current_user()
                if user:
                    effective_user_id = user.get("user_id")
            except Exception:
                effective_user_id = None

        logger.info(f"🔍 RetrievalService executing query: '{query[:80]}...' (top_k={k}, user={effective_user_id})")

        chunks, hybrid_used, rerank_used = self.retriever.retrieve(query, top_k=k, user_id=effective_user_id)
        retrieval_time_ms = (time.time() - start_time) * 1000.0

        retriever_error = getattr(self.retriever, "last_error", None)
        rerank_status = getattr(self.retriever, "last_rerank_status", "disabled")
        empty_reason = getattr(self.retriever, "last_empty_reason", None)

        context = self.context_builder.build_context(
            query=query,
            chunks=chunks,
            retrieval_time_ms=retrieval_time_ms,
            hybrid_used=hybrid_used,
            rerank_used=rerank_used,
            error=retriever_error,
            rerank_status=rerank_status,
            empty_reason=empty_reason,
        )

        logger.info(
            f"✅ RetrievalService completed in {retrieval_time_ms:.1f}ms: "
            f"retrieved {context.total_chunks_retrieved} chunk(s), hybrid={hybrid_used}, rerank={rerank_used}"
        )
        return context
