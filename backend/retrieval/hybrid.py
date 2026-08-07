"""Hybrid retrieval engine combining FAISS vector search and BM25 keyword search."""

import logging
from typing import Dict, List, Tuple

from config import RAG_CONFIG
from .bm25_search import BM25Retriever
from .metadata_lookup import MetadataLookupService
from .reranker import CohereRerankerAdapter
from .types import RetrievedChunk
from .vector_search import FAISSQueryEngine

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Merges semantic FAISS vector search and keyword BM25 search using Reciprocal Rank Fusion (RRF)."""

    def __init__(
        self,
        vector_engine: FAISSQueryEngine = None,
        bm25_engine: BM25Retriever = None,
        metadata_lookup: MetadataLookupService = None,
        reranker: CohereRerankerAdapter = None,
    ):
        self.vector_engine = vector_engine or FAISSQueryEngine()
        self.bm25_engine = bm25_engine or BM25Retriever()
        self.metadata_lookup = metadata_lookup or MetadataLookupService()
        self.reranker = reranker or CohereRerankerAdapter()

        self.hybrid_enabled = RAG_CONFIG.get("hybrid_enabled", True)
        self.faiss_weight = RAG_CONFIG.get("faiss_weight", 0.7)
        self.bm25_weight = RAG_CONFIG.get("bm25_weight", 0.3)

    def retrieve(self, query: str, top_k: int = 5) -> Tuple[List[RetrievedChunk], bool, bool]:
        """
        Executes hybrid retrieval over FAISS and BM25, merges scores via RRF,
        hydrates metadata from PostgreSQL, and applies optional Cohere reranking.
        Returns: (chunks, hybrid_used, rerank_used)
        """
        fetch_k = top_k * 3

        # 1. FAISS Vector Search
        faiss_results = self.vector_engine.search(query, top_k=fetch_k)

        # 2. BM25 Keyword Search
        bm25_results: List[Tuple[int, float]] = []
        hybrid_used = False
        if self.hybrid_enabled:
            bm25_results = self.bm25_engine.search(query, top_k=fetch_k)
            hybrid_used = bool(bm25_results)

        if not faiss_results and not bm25_results:
            return [], False, False

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_k = 60
        combined_scores: Dict[int, float] = {}
        source_tags: Dict[int, str] = {}

        # Process FAISS rank scores
        for rank, (v_idx, score) in enumerate(faiss_results, start=1):
            rrf_score = self.faiss_weight * (1.0 / (rrf_k + rank))
            combined_scores[v_idx] = combined_scores.get(v_idx, 0.0) + rrf_score
            source_tags[v_idx] = "faiss"

        # Process BM25 rank scores
        for rank, (v_idx, score) in enumerate(bm25_results, start=1):
            rrf_score = self.bm25_weight * (1.0 / (rrf_k + rank))
            combined_scores[v_idx] = combined_scores.get(v_idx, 0.0) + rrf_score
            if v_idx in source_tags:
                source_tags[v_idx] = "hybrid"
            else:
                source_tags[v_idx] = "bm25"

        sorted_pairs = sorted(combined_scores.items(), key=lambda item: item[1], reverse=True)[:fetch_k]

        # 4. PostgreSQL Metadata Hydration
        hydrated_chunks = self.metadata_lookup.hydrate(sorted_pairs)

        # Update retrieval_source tag on chunks
        for chunk in hydrated_chunks:
            chunk.retrieval_source = source_tags.get(chunk.vector_index, "faiss")

        # 5. Cohere Reranking
        rerank_used = self.reranker.is_available
        final_chunks = self.reranker.rerank(query, hydrated_chunks, top_k=top_k)

        return final_chunks, hybrid_used, rerank_used
