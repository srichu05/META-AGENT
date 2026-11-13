"""Audit Script: Controlled RAG Retrieval Experiment (Phase E).

Evaluates FAISS, BM25, RRF Fusion, and Cohere Reranking under controlled synthetic ground truth.
Does NOT modify application source code, production database, or existing user documents.
"""

import json
import logging
import math
import os
import sys
import tempfile
import time
from typing import Any, Dict, List, Tuple

# Prevent HF network hang
os.environ["HF_HUB_OFFLINE"] = "1"

BACKEND_DIR = r"e:\Meta_Agent_Math_Debate_System\backend"
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from models.meta_agent import MetaAgent
from ingestion.embeddings import BGEEmbeddingService
from ingestion.faiss_store import FAISSVectorStore
from retrieval.types import RetrievedChunk, RetrievedContext
from retrieval.reranker import CohereRerankerAdapter, PassThroughReranker
from evaluation.ragas_evaluator import RAGASEvaluator
from config import RAG_CONFIG

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("RetrievalAudit")

# Auditable corpus of 10 math reference chunks
CONTROLLED_CORPUS = [
    {
        "chunk_id": "chunk_01",
        "topic": "pythagorean_theorem",
        "content": "Pythagorean Theorem: For any right triangle with perpendicular sides a and b and hypotenuse c, the sum of squares is a^2 + b^2 = c^2. For sides 3 and 4, hypotenuse is 5, area is (1/2)*a*b = 6.",
        "filename": "geometry_handbook.pdf",
        "page": 12,
    },
    {
        "chunk_id": "chunk_02",
        "topic": "quadratic_equation",
        "content": "Quadratic Formula: For ax^2 + bx + c = 0, roots are given by x = (-b +- sqrt(b^2 - 4ac)) / (2a). For difference of squares x^2 - 9 = 0, factoring yields (x-3)(x+3)=0 with solutions x=3 and x=-3.",
        "filename": "algebra_core.pdf",
        "page": 45,
    },
    {
        "chunk_id": "chunk_03",
        "topic": "perimeter_area_rectangle",
        "content": "Rectangle Geometry Formulas: Perimeter P = 2*(length + width). Area A = length * width. For length 12m and width 8m, Perimeter = 2*(12+8) = 40m. Area = 12 * 8 = 96 sq meters.",
        "filename": "geometry_handbook.pdf",
        "page": 18,
    },
    {
        "chunk_id": "chunk_04",
        "topic": "speed_distance_time",
        "content": "Uniform Kinematics: Distance = Speed * Time. Speed = Distance / Time. When travelling at 60 mph for 2.5 hours, distance = 60 * 2.5 = 150 miles. For 3.5 hours, distance = 210 miles.",
        "filename": "physics_math.pdf",
        "page": 5,
    },
    {
        "chunk_id": "chunk_05",
        "topic": "simple_probability",
        "content": "Classical Probability: Probability P(E) = (favorable outcomes) / (total equally likely outcomes). In a box with 5 red, 3 blue, 2 green balls (total 10), P(blue) = 3/10 = 0.3.",
        "filename": "probability_stats.pdf",
        "page": 22,
    },
    {
        "chunk_id": "chunk_06",
        "topic": "percentage_discounts",
        "content": "Commercial Mathematics: Discount Amount = Original Price * (Discount Rate / 100). Final Sale Price = Original Price - Discount Amount. A 20% discount on $80 jacket yields $16 discount, final price $64.",
        "filename": "business_math.pdf",
        "page": 30,
    },
    {
        "chunk_id": "chunk_07",
        "topic": "fractions_and_remainders",
        "content": "Fractions and Partitioning: Total units remaining = Total - Eaten. For 24 marbles, giving 1/3 leaves 16 marbles. Giving 1/4 of remaining 16 leaves 12 marbles.",
        "filename": "arithmetic_fundamentals.pdf",
        "page": 14,
    },
    {
        "chunk_id": "chunk_08",
        "topic": "consecutive_integers",
        "content": "Number Theory - Consecutive Integers: Consecutive even integers are expressed as 2n and 2n + 2. If their sum is 46: 2n + (2n + 2) = 46 => 4n = 44 => n = 11. The numbers are 22 and 24.",
        "filename": "discrete_math.pdf",
        "page": 8,
    },
    {
        "chunk_id": "chunk_09",
        "topic": "linear_equations",
        "content": "Linear Equation Isolation: To solve 4x - 12 = 28, add 12 to both sides: 4x = 40. Divide both sides by 4: x = 10.",
        "filename": "algebra_core.pdf",
        "page": 12,
    },
    {
        "chunk_id": "chunk_10",
        "topic": "two_step_arithmetic",
        "content": "Multi-Step Word Problems: If clips sold in April = 48, and May sales = half of April (48 / 2 = 24), then total combined sales = 48 + 24 = 72 clips.",
        "filename": "arithmetic_fundamentals.pdf",
        "page": 3,
    },
]

# 10 test queries with known ground truth target chunk
TEST_QUERIES = [
    {"query": "What is the formula and area for a right triangle with sides 3 and 4?", "target_chunk": "chunk_01"},
    {"query": "Solve the quadratic equation x^2 - 9 = 0 using factoring.", "target_chunk": "chunk_02"},
    {"query": "How do you calculate the perimeter of a rectangle with length 12 and width 8?", "target_chunk": "chunk_03"},
    {"query": "How far will a vehicle travel at 60 miles per hour in 2.5 hours?", "target_chunk": "chunk_04"},
    {"query": "What is the probability of picking a blue ball from a box of red, blue, and green balls?", "target_chunk": "chunk_05"},
    {"query": "How much does an $80 item cost after a 20 percent discount?", "target_chunk": "chunk_06"},
    {"query": "If I give away 1/3 of 24 marbles and then 1/4 of what is left, how many remain?", "target_chunk": "chunk_07"},
    {"query": "The sum of two consecutive even integers is 46, how do I find them?", "target_chunk": "chunk_08"},
    {"query": "How to isolate and solve for x in 4x - 12 = 28?", "target_chunk": "chunk_09"},
    {"query": "How many clips were sold if 48 were sold in April and half as many in May?", "target_chunk": "chunk_10"},
]


def bm25_score_in_memory(query: str, corpus: List[Dict[str, Any]], k1: float = 1.5, b: float = 0.75) -> List[Tuple[int, float]]:
    import re
    query_tokens = re.findall(r"\w+", query.lower())
    if not query_tokens:
        return []

    N = len(corpus)
    doc_tokens = [re.findall(r"\w+", doc["content"].lower()) for doc in corpus]
    doc_lens = [len(toks) for toks in doc_tokens]
    avg_dl = sum(doc_lens) / N if N > 0 else 1.0

    idf = {}
    for q_term in set(query_tokens):
        n_q = sum(1 for toks in doc_tokens if q_term in toks)
        idf[q_term] = math.log((N - n_q + 0.5) / (n_q + 0.5) + 1.0)

    scored = []
    for idx, (doc, toks, dl) in enumerate(zip(corpus, doc_tokens, doc_lens)):
        score = 0.0
        if dl == 0:
            continue
        tf = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        for q_term in query_tokens:
            f = tf.get(q_term, 0)
            if f > 0:
                num = f * (k1 + 1.0)
                den = f + k1 * (1.0 - b + b * (dl / avg_dl))
                score += idf.get(q_term, 0.0) * (num / den)
        if score > 0.0:
            scored.append((idx, float(score)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def main():
    results_file = r"audit\baseline_v1\retrieval_results.jsonl"
    logger.info("Initializing BGE Embedding Service and Temporary FAISS Vector Store...")

    temp_index = tempfile.NamedTemporaryFile(suffix=".faiss", delete=False)
    temp_index_path = temp_index.name
    temp_index.close()

    try:
        embedding_service = BGEEmbeddingService("BAAI/bge-small-en-v1.5", batch_size=4, expected_dimension=384)
        vector_store = FAISSVectorStore(temp_index_path, expected_dimension=384)

        # Index the 10 corpus chunks
        corpus_texts = [c["content"] for c in CONTROLLED_CORPUS]
        vectors = embedding_service.generate(corpus_texts)
        vector_store.append(vectors)
        vector_store.save()

        logger.info(f"Indexed {len(CONTROLLED_CORPUS)} chunks into FAISS vector store ({temp_index_path})")

        reranker = CohereRerankerAdapter()
        ragas_eval = RAGASEvaluator()

        records = []
        faiss_ranks = []
        bm25_ranks = []
        rrf_ranks = []

        for q_idx, item in enumerate(TEST_QUERIES, 1):
            query = item["query"]
            target = item["target_chunk"]
            target_idx = [i for i, c in enumerate(CONTROLLED_CORPUS) if c["chunk_id"] == target][0]

            # 1. FAISS Vector Search
            t0 = time.time()
            q_vec = embedding_service.generate([query])
            scores, indices = vector_store.search(q_vec, top_k=10)
            faiss_time_ms = (time.time() - t0) * 1000.0

            faiss_ordered_indices = [int(i) for i in indices[0] if i >= 0]
            faiss_rank = (faiss_ordered_indices.index(target_idx) + 1) if target_idx in faiss_ordered_indices else 999
            faiss_ranks.append(faiss_rank)

            # 2. BM25 Search
            t0 = time.time()
            bm25_scored = bm25_score_in_memory(query, CONTROLLED_CORPUS)
            bm25_time_ms = (time.time() - t0) * 1000.0
            bm25_ordered_indices = [idx for idx, _ in bm25_scored]
            bm25_rank = (bm25_ordered_indices.index(target_idx) + 1) if target_idx in bm25_ordered_indices else 999
            bm25_ranks.append(bm25_rank)

            # 3. Reciprocal Rank Fusion (RRF k=60, faiss=0.7, bm25=0.3)
            rrf_k = 60
            combined_scores = {}
            for rank, v_idx in enumerate(faiss_ordered_indices, start=1):
                combined_scores[v_idx] = combined_scores.get(v_idx, 0.0) + 0.7 * (1.0 / (rrf_k + rank))
            for rank, v_idx in enumerate(bm25_ordered_indices, start=1):
                combined_scores[v_idx] = combined_scores.get(v_idx, 0.0) + 0.3 * (1.0 / (rrf_k + rank))

            sorted_rrf = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
            rrf_ordered_indices = [idx for idx, _ in sorted_rrf]
            rrf_rank = (rrf_ordered_indices.index(target_idx) + 1) if target_idx in rrf_ordered_indices else 999
            rrf_ranks.append(rrf_rank)

            # 4. Cohere Reranker check
            chunks_obj = [
                RetrievedChunk(
                    chunk_id=CONTROLLED_CORPUS[i]["chunk_id"],
                    document_id="doc_1",
                    filename=CONTROLLED_CORPUS[i]["filename"],
                    file_type="pdf",
                    page_number=CONTROLLED_CORPUS[i]["page"],
                    section_heading=CONTROLLED_CORPUS[i]["topic"],
                    char_start=0,
                    char_end=len(CONTROLLED_CORPUS[i]["content"]),
                    vector_index=i,
                    content=CONTROLLED_CORPUS[i]["content"],
                    score=score,
                    retrieval_source="rrf",
                )
                for i, score in sorted_rrf[:5]
            ]
            t0 = time.time()
            reranked = reranker.rerank(query, chunks_obj, top_k=5)
            reranker_time_ms = (time.time() - t0) * 1000.0

            # 5. RAGAS Evaluation
            top_texts = [c.content for c in reranked]
            ragas_metrics = ragas_eval.evaluate_all(
                question=query,
                reference_answer=CONTROLLED_CORPUS[target_idx]["content"],
                final_answer=CONTROLLED_CORPUS[target_idx]["content"],
                retrieved_context_texts=top_texts,
                expected_context=CONTROLLED_CORPUS[target_idx]["content"],
            )

            rec = {
                "query_id": f"ret_q_{q_idx:03d}",
                "query": query,
                "target_chunk": target,
                "faiss_rank": faiss_rank,
                "faiss_latency_ms": round(faiss_time_ms, 2),
                "bm25_rank": bm25_rank,
                "bm25_latency_ms": round(bm25_time_ms, 2),
                "rrf_rank": rrf_rank,
                "cohere_rerank_available": reranker.is_available,
                "reranker_latency_ms": round(reranker_time_ms, 2),
                "top_1_chunk_id": CONTROLLED_CORPUS[rrf_ordered_indices[0]]["chunk_id"],
                "target_retrieved_in_top1": rrf_rank == 1,
                "target_retrieved_in_top3": rrf_rank <= 3,
                "target_retrieved_in_top5": rrf_rank <= 5,
                "reciprocal_rank": round(1.0 / rrf_rank if rrf_rank <= 10 else 0.0, 4),
                "ragas_heuristic_scores": ragas_metrics,
            }
            records.append(rec)
            logger.info(f"[{q_idx}/10] '{query[:50]}...' -> FAISS Rank={faiss_rank}, BM25 Rank={bm25_rank}, RRF Rank={rrf_rank}")

        with open(results_file, "w", encoding="utf-8") as rf:
            for r in records:
                rf.write(json.dumps(r, ensure_ascii=False) + "\n")

        # Summary Metrics
        n = len(TEST_QUERIES)
        r1 = sum(1 for r in rrf_ranks if r == 1) / n
        r3 = sum(1 for r in rrf_ranks if r <= 3) / n
        r5 = sum(1 for r in rrf_ranks if r <= 5) / n
        mrr = sum(1.0 / r if r <= 10 else 0.0 for r in rrf_ranks) / n

        logger.info("\n=== RETRIEVAL PERFORMANCE SUMMARY ===")
        logger.info(f"Recall@1: {r1:.2%}")
        logger.info(f"Recall@3: {r3:.2%}")
        logger.info(f"Recall@5: {r5:.2%}")
        logger.info(f"Mean Reciprocal Rank (MRR): {mrr:.4f}")
        logger.info(f"Cohere Reranker Active: {reranker.is_available} (cohere_rerank_enabled={RAG_CONFIG.get('cohere_rerank_enabled')})")
        logger.info(f"Results written to: {results_file}")

    finally:
        if os.path.exists(temp_index_path):
            try:
                os.remove(temp_index_path)
            except Exception:
                pass


if __name__ == "__main__":
    main()
