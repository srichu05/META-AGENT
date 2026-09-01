"""BM25 keyword search engine over document chunks in PostgreSQL."""

import math
import re
import logging
from typing import Dict, List, Set, Tuple

from flask import has_app_context

from models.document import DocumentChunk

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> List[str]:
    """Tokenize and lower-case words/alphanumerics."""
    return re.findall(r"\w+", (text or "").lower())


def _get_all_chunks() -> List[DocumentChunk]:
    """Safely query DocumentChunk table, ensuring an active Flask app context if needed."""
    if not has_app_context():
        try:
            from app import app
            with app.app_context():
                return DocumentChunk.query.all()
        except Exception as err:
            logger.warning(f"Could not acquire Flask app context for BM25 search: {err}")
            return []
    return DocumentChunk.query.all()


class BM25Retriever:
    """BM25 keyword search engine operating over PostgreSQL document chunks."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        """
        Executes BM25 keyword scoring across all stored DocumentChunk records.
        Returns list of (vector_index, bm25_score) sorted descending by score.
        """
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        try:
            chunks = _get_all_chunks()
            if not chunks:
                return []


            N = len(chunks)
            doc_tokens_list: List[List[str]] = [_tokenize(c.content) for c in chunks]
            doc_lens: List[int] = [len(toks) for toks in doc_tokens_list]
            avg_dl = sum(doc_lens) / N if N > 0 else 1.0

            # Compute IDF for query terms
            idf: Dict[str, float] = {}
            for q_term in set(query_tokens):
                n_q = sum(1 for toks in doc_tokens_list if q_term in toks)
                idf[q_term] = math.log((N - n_q + 0.5) / (n_q + 0.5) + 1.0)

            # Score each chunk
            scored: List[Tuple[int, float]] = []
            for chunk, toks, doc_len in zip(chunks, doc_tokens_list, doc_lens):
                score = 0.0
                if doc_len == 0:
                    continue
                tf_dict: Dict[str, int] = {}
                for t in toks:
                    tf_dict[t] = tf_dict.get(t, 0) + 1

                for q_term in query_tokens:
                    freq = tf_dict.get(q_term, 0)
                    if freq > 0:
                        numerator = freq * (self.k1 + 1.0)
                        denominator = freq + self.k1 * (1.0 - self.b + self.b * (doc_len / avg_dl))
                        score += idf.get(q_term, 0.0) * (numerator / denominator)

                if score > 0.0:
                    scored.append((chunk.vector_index, float(score)))

            scored.sort(key=lambda item: item[1], reverse=True)
            return scored[:top_k]
        except Exception as error:
            logger.exception(f"BM25 keyword search failed: {error}")
            return []
