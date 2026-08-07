"""Modular reranker interface & Cohere Rerank adapter."""

import logging
from typing import List

import requests

from config import API_CONFIG, RAG_CONFIG
from .types import RetrievedChunk

logger = logging.getLogger(__name__)


class RerankerInterface:
    """Base interface for chunk reranking components."""

    def rerank(self, query: str, chunks: List[RetrievedChunk], top_k: int = 5) -> List[RetrievedChunk]:
        """Rerank and score chunks against query."""
        raise NotImplementedError


class PassThroughReranker(RerankerInterface):
    """Fallback pass-through reranker that maintains current score ordering."""

    def rerank(self, query: str, chunks: List[RetrievedChunk], top_k: int = 5) -> List[RetrievedChunk]:
        return sorted(chunks, key=lambda c: c.score, reverse=True)[:top_k]


class CohereRerankerAdapter(RerankerInterface):
    """Reranks retrieved chunks using Cohere's Rerank API (if configured)."""

    def __init__(self, api_key: str = None, model: str = None):
        cfg = API_CONFIG.get("COHERE", {})
        self.api_key = api_key or cfg.get("api_key")
        self.model = model or RAG_CONFIG.get("cohere_rerank_model", "rerank-v3.5")
        self.base_url = "https://api.cohere.com/v2/rerank"

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and RAG_CONFIG.get("cohere_rerank_enabled", False))

    def rerank(self, query: str, chunks: List[RetrievedChunk], top_k: int = 5) -> List[RetrievedChunk]:
        if not chunks:
            return []

        if not self.is_available:
            logger.debug("Cohere Rerank is disabled or missing API key. Using pass-through ranking.")
            return PassThroughReranker().rerank(query, chunks, top_k=top_k)

        try:
            documents = [chunk.content for chunk in chunks]
            payload = {
                "model": self.model,
                "query": query,
                "documents": documents,
                "top_n": min(top_k, len(chunks)),
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            response = requests.post(self.base_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            reranked_chunks: List[RetrievedChunk] = []

            for item in results:
                idx = item.get("index")
                score = item.get("relevance_score", 0.0)
                if idx is not None and 0 <= idx < len(chunks):
                    original_chunk = chunks[idx]
                    original_chunk.score = float(score)
                    original_chunk.retrieval_source = f"{original_chunk.retrieval_source}+cohere_rerank"
                    reranked_chunks.append(original_chunk)

            return reranked_chunks if reranked_chunks else PassThroughReranker().rerank(query, chunks, top_k=top_k)

        except Exception as error:
            logger.warning(f"Cohere Rerank failed ({error}). Falling back to original ranking.")
            return PassThroughReranker().rerank(query, chunks, top_k=top_k)
