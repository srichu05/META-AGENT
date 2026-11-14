"""Comprehensive test suite for Phase 3.1 Semantic Caching."""

import time
import unittest
from datetime import datetime, timedelta
import numpy as np

from app import app
from cache.eligibility import CacheEligibilityPolicy
from cache.normalization import (
    compute_context_hash,
    compute_query_hash,
    compute_scope_hash,
    normalize_query,
)
from cache.safeguards import (
    MathEquivalenceValidator,
    extract_numbers,
    extract_operators,
    extract_units,
)
from cache.service import SemanticCacheService
from cache.types import CacheEntry, CacheResult, CacheStats
from database import db
from graph.state import DebateGraphState, create_initial_state
from graph.workflow import MathDebateGraph


class MockEmbeddingService:
    """Fast, deterministic embedding mock for unit tests."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def generate(self, texts):
        results = []
        for text in texts:
            # Deterministic pseudo-vector from text hash
            seed = sum(ord(c) for c in text.lower())
            np.random.seed(seed % (2**31 - 1))
            vec = np.random.randn(self.dimension).astype(np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            results.append(vec)
        return np.array(results, dtype=np.float32)


def _create_sample_state(
    query: str = "Solve 2x + 4 = 10",
    answer: str = "x = 3",
    success: bool = True,
    partial_execution: bool = False,
    failed_node: str = None,
    error: str = None,
) -> DebateGraphState:
    state = create_initial_state(query)
    state["final_answer"] = answer
    state["partial_execution"] = partial_execution
    state["failed_node"] = failed_node
    state["error"] = error
    state["planner_output"] = {"topic": "algebra", "needs_retrieval": False}
    state["retrieved_context"] = {"total_chunks_retrieved": 0, "chunks": []}
    state["managed_context"] = {"formatted_context": "", "citations": []}
    state["solver_outputs"] = {
        "solver_1": {
            "success": success,
            "answer": answer,
            "solution": f"Step 1: 2x = 6\nStep 2: {answer}",
            "actual_provider": "GEMINI",
            "actual_model": "gemini-2.5-flash",
            "confidence": 0.95,
        }
    }
    state["reflection_output"] = {
        "contradictions_found": False,
        "hallucination_detected": False,
        "summary": "Verified correct.",
    }
    state["judge_output"] = {
        "success": success,
        "best_agent": "solver_1",
        "best_solution": answer,
        "score": 0.95,
        "confidence": 0.95,
        "metrics": {"correctness": 0.95},
    }
    state["citations"] = []
    state["debate_history"] = [{"node": "Planner", "timestamp": "2026-11-09T10:00:00Z"}]
    return state


class TestSemanticCacheUnit(unittest.TestCase):
    """Unit tests for cache normalization, mathematical safeguards, and eligibility."""

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_normalization_removes_fillers_and_standardizes(self):
        """Verify normalization standardizes math symbols and removes conversational prefixes."""
        q1 = "Can you please calculate the value of 2x + 4 = 10?"
        norm1 = normalize_query(q1)
        self.assertIn("2x + 4 = 10", norm1)
        self.assertNotIn("please", norm1)
        self.assertNotIn("?", norm1)

        # LaTeX symbols
        q2 = r"$\frac{1}{2} \times 4 + \pi$"
        norm2 = normalize_query(q2)
        self.assertIn("(1) / (2)", norm2)
        self.assertIn("*", norm2)
        self.assertIn("pi", norm2)
        self.assertNotIn(r"\times", norm2)

    def test_number_extraction(self):
        """Verify extractor parses integers, floats, fractions, and constants."""
        text = "Find roots of 2x^2 + 5.5x - 3 = 0 with fraction 1/2 and constant pi"
        nums = extract_numbers(text)
        self.assertIn(2.0, nums)
        self.assertIn(5.5, nums)
        self.assertIn(3.0, nums)
        self.assertIn(0.5, nums)  # 1/2
        self.assertIn(3.14159, nums)  # pi

    def test_operator_extraction(self):
        """Verify extractor identifies mathematical operators and relations."""
        text = "det(A) = ad - bc >= 0 and sqrt(x) != y"
        ops = extract_operators(text)
        self.assertIn("det", ops)
        self.assertIn("=", ops)
        self.assertIn("-", ops)
        self.assertIn(">=", ops)
        self.assertIn("sqrt", ops)
        self.assertIn("!=", ops)

    def test_safeguard_rejects_different_numbers(self):
        """Ensure questions with different numbers fail validation even if structurally identical."""
        q1 = "Solve 2x + 5 = 15"
        q2 = "Solve 2x + 6 = 15"
        is_equiv, reason = MathEquivalenceValidator.validate_semantic_equivalence(q1, q2)
        self.assertFalse(is_equiv)
        self.assertIn("Numerical values differ", reason)

    def test_safeguard_rejects_different_operators(self):
        """Ensure questions with different operators are rejected."""
        q1 = "Find roots of x^2 - 4 = 0"
        q2 = "Find roots of x^2 + 4 = 0"
        is_equiv, reason = MathEquivalenceValidator.validate_semantic_equivalence(q1, q2)
        self.assertFalse(is_equiv)
        self.assertIn("operators differ", reason)

    def test_safeguard_rejects_different_units(self):
        """Ensure questions asking for different physical units are rejected."""
        q1 = "What is the car velocity in meters per second?"
        q2 = "What is the car velocity in kilometers per hour?"
        is_equiv, reason = MathEquivalenceValidator.validate_semantic_equivalence(q1, q2)
        self.assertFalse(is_equiv)
        self.assertIn("units differ", reason)

    def test_safeguard_rejects_different_operations(self):
        """Ensure questions with different intent keywords are rejected."""
        q1 = "Calculate the determinant of matrix A"
        q2 = "Calculate the eigenvalues of matrix A"
        is_equiv, reason = MathEquivalenceValidator.validate_semantic_equivalence(q1, q2)
        self.assertFalse(is_equiv)
        self.assertIn("intents differ", reason)

    def test_safeguard_accepts_equivalent_rephrasing(self):
        """Ensure equivalent rephrasings with identical math invariants pass."""
        q1 = "Using Euler's identity, what is the value of e^(i * pi) + 1?"
        q2 = "What is the value of e^(i * pi) + 1 according to Euler's identity?"
        is_equiv, reason = MathEquivalenceValidator.validate_semantic_equivalence(q1, q2)
        self.assertTrue(is_equiv)
        self.assertIsNone(reason)

    def test_eligibility_policy_rules(self):
        """Verify CacheEligibilityPolicy accepts valid debates and rejects faulty states."""
        # Valid state
        valid_state = _create_sample_state()
        eligible, reason = CacheEligibilityPolicy.is_eligible(valid_state)
        self.assertTrue(eligible)
        self.assertIsNone(reason)

        # Rejected: partial execution
        partial_state = _create_sample_state(partial_execution=True)
        eligible, reason = CacheEligibilityPolicy.is_eligible(partial_state)
        self.assertFalse(eligible)
        self.assertIn("partial", reason)

        # Rejected: failed node
        failed_node_state = _create_sample_state(failed_node="Solver_2")
        eligible, reason = CacheEligibilityPolicy.is_eligible(failed_node_state)
        self.assertFalse(eligible)
        self.assertIn("failed node", reason)

        # Rejected: provider rate limit or error string in final answer
        err_state = _create_sample_state(
            answer="All cloud providers in order ['GEMINI', 'GROQ'] failed (RATE_LIMIT HTTP 429)"
        )
        eligible, reason = CacheEligibilityPolicy.is_eligible(err_state)
        self.assertFalse(eligible)
        self.assertIn("provider error", reason)

        # Rejected: judge marked unsuccessful
        bad_judge_state = _create_sample_state()
        bad_judge_state["judge_output"]["success"] = False
        eligible, reason = CacheEligibilityPolicy.is_eligible(bad_judge_state)
        self.assertFalse(eligible)
        self.assertIn("unsuccessful", reason)


class TestSemanticCacheService(unittest.TestCase):
    """Integration tests for SemanticCacheService behavior, TTL, and capacity limits."""

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app_context = self.app.app_context()
        self.app_context.push()

        self.mock_emb = MockEmbeddingService()
        self.config = {
            "enabled": True,
            "similarity_threshold": 0.90,
            "exact_match_enabled": True,
            "ttl_seconds": 604800,
            "max_entries": 5,
            "namespace": "test_namespace",
            "schema_version": "v1.0",
        }
        self.cache = SemanticCacheService(config=self.config, embedding_service=self.mock_emb)
        self.cache.clear()

    def tearDown(self):
        self.cache.clear()
        self.app_context.pop()

    def test_exact_cache_hit_and_miss(self):
        """Verify exact match lookup succeeds and misses properly on unknown query."""
        query = "Solve for x in 3x + 9 = 24"
        state = _create_sample_state(query=query, answer="x = 5")

        # Miss initially
        res_before = self.cache.get(query)
        self.assertIsNone(res_before)
        self.assertEqual(self.cache.stats.misses, 1)

        # Set
        stored = self.cache.set(query, state, execution_time_ms=1200.0)
        self.assertTrue(stored)

        # Exact Hit
        res_after = self.cache.get(query)
        self.assertIsNotNone(res_after)
        self.assertTrue(res_after.hit)
        self.assertEqual(res_after.hit_type, "exact")
        self.assertEqual(res_after.similarity, 1.0)
        self.assertEqual(res_after.entry.final_answer, "x = 5")
        self.assertEqual(self.cache.stats.exact_hits, 1)

        # Verify state reconstruction
        reconstructed = res_after.to_graph_state(current_query=query)
        self.assertTrue(reconstructed["is_cached"])
        self.assertEqual(reconstructed["cache_hit_type"], "exact")
        self.assertEqual(reconstructed["final_answer"], "x = 5")

    def test_semantic_cache_hit_with_identical_vector(self):
        """Verify semantic similarity lookup hits when vector matches and math is identical."""
        q1 = "Solve 2x + 4 = 10"
        state = _create_sample_state(query=q1, answer="x = 3")
        self.cache.set(q1, state, execution_time_ms=800.0)

        # Rephrased query where mock returns high similarity
        # Here we mock embedding service to return candidate vector for q2
        q2 = "Find x in 2x + 4 = 10"
        vec_q1 = self.mock_emb.generate([normalize_query(q1)])[0]
        self.mock_emb.generate = lambda texts: np.array([vec_q1] * len(texts), dtype=np.float32)

        result = self.cache.get(q2)
        self.assertIsNotNone(result)
        self.assertTrue(result.hit)
        self.assertEqual(result.hit_type, "semantic")
        self.assertAlmostEqual(result.similarity, 1.0, places=3)
        self.assertEqual(result.entry.final_answer, "x = 3")
        self.assertEqual(self.cache.stats.semantic_hits, 1)

    def test_ttl_expiration(self):
        """Verify entry expires after configured TTL."""
        short_ttl_config = dict(self.config)
        short_ttl_config["ttl_seconds"] = 1  # 1 second TTL
        cache = SemanticCacheService(config=short_ttl_config, embedding_service=self.mock_emb)

        query = "Calculate 7 * 8"
        state = _create_sample_state(query=query, answer="56")
        cache.set(query, state, execution_time_ms=500.0)

        # Immediate lookup -> hit
        res1 = cache.get(query)
        self.assertIsNotNone(res1)
        self.assertTrue(res1.hit)

        # Wait 1.1s for expiration
        time.sleep(1.1)

        # Post-expiration lookup -> miss
        res2 = cache.get(query)
        self.assertIsNone(res2)

    def test_capacity_limit_and_lru_eviction(self):
        """Verify oldest entries are evicted when max capacity is exceeded."""
        cap_config = dict(self.config)
        cap_config["max_entries"] = 2
        cache = SemanticCacheService(config=cap_config, embedding_service=self.mock_emb)

        state1 = _create_sample_state(query="Solve x + 1 = 2", answer="x = 1")
        state2 = _create_sample_state(query="Solve x + 2 = 4", answer="x = 2")
        state3 = _create_sample_state(query="Solve x + 3 = 6", answer="x = 3")

        cache.set("Solve x + 1 = 2", state1)
        cache.set("Solve x + 2 = 4", state2)
        self.assertEqual(len(cache._memory_entries), 2)

        # Adding 3rd entry triggers eviction of oldest
        cache.set("Solve x + 3 = 6", state3)
        self.assertLessEqual(len(cache._memory_entries), 2)
        self.assertEqual(cache.stats.evictions, 1)

        # First entry should be evicted
        res_evicted = cache.get("Solve x + 1 = 2")
        self.assertIsNone(res_evicted)

        # Third entry should still be present
        res_present = cache.get("Solve x + 3 = 6")
        self.assertIsNotNone(res_present)

    def test_disabled_cache_behavior(self):
        """Verify disabled cache completely bypasses storage and lookup."""
        disabled_config = dict(self.config)
        disabled_config["enabled"] = False
        cache = SemanticCacheService(config=disabled_config, embedding_service=self.mock_emb)

        state = _create_sample_state()
        stored = cache.set("Solve x + 1 = 2", state)
        self.assertFalse(stored)

        res = cache.get("Solve x + 1 = 2")
        self.assertIsNone(res)

    def test_context_mismatch_prevents_hit(self):
        """Verify candidate with different retrieved context hash is rejected."""
        q = "According to reference guide, what is Euler's identity?"
        state = _create_sample_state(query=q, answer="e^(i*pi) + 1 = 0")

        # Cache with context hash 'doc_hash_A'
        self.cache.set(q, state, context="Document A content")

        # Query with different context 'Document B content'
        res = self.cache.get(q, context="Document B completely different content")
        self.assertIsNone(res)


class TestWorkflowCacheIntegration(unittest.TestCase):
    """End-to-end integration test verifying MathDebateGraph cache hit and miss execution."""

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app_context = self.app.app_context()
        self.app_context.push()

        self.mock_emb = MockEmbeddingService()
        self.cache_service = SemanticCacheService(
            config={
                "enabled": True,
                "similarity_threshold": 0.92,
                "exact_match_enabled": True,
                "ttl_seconds": 604800,
                "max_entries": 100,
                "namespace": "workflow_test",
                "schema_version": "v1.0",
            },
            embedding_service=self.mock_emb,
        )
        self.cache_service.clear()
        self.graph = MathDebateGraph(cache_service=self.cache_service)

    def tearDown(self):
        self.cache_service.clear()
        self.app_context.pop()

    def test_workflow_first_run_misses_second_run_hits(self):
        """Verify first graph execution executes nodes, while second query hits cache instantly."""
        query = "Solve for x in 5x - 10 = 0"

        # Pre-seed valid eligible state into cache to avoid unneeded external LLM calls in unit test
        sample_state = _create_sample_state(query=query, answer="x = 2")
        stored = self.cache_service.set(query, sample_state, execution_time_ms=4500.0)
        self.assertTrue(stored)

        # Graph execution should hit cache directly
        t0 = time.time()
        result_state = self.graph.execute(query)
        elapsed = time.time() - t0

        self.assertTrue(result_state.get("is_cached"))
        self.assertEqual(result_state.get("cache_hit_type"), "exact")
        self.assertEqual(result_state.get("final_answer"), "x = 2")
        self.assertEqual(result_state.get("current_node"), "SemanticCache")
        # Sub-second execution
        self.assertLess(elapsed, 0.5)

        # Verify stats reflect hit
        stats = self.cache_service.get_stats()
        self.assertEqual(stats["exact_hits"], 1)
        self.assertEqual(stats["total_hits"], 1)
        self.assertEqual(stats["latency_saved_ms_total"], 4500.0)

    def test_cache_backend_failure_does_not_crash_graph(self):
        """Verify graph continues execution even if cache raises unexpected exceptions."""
        broken_cache = SemanticCacheService(
            config={"enabled": True},
            embedding_service=self.mock_emb,
        )
        # Force exception on get
        broken_cache.get = lambda q, ctx=None: (_ for _ in ()).throw(RuntimeError("Simulated DB Disk Crash"))
        broken_cache.get = lambda q, ctx=None, **kwargs: (_ for _ in ()).throw(RuntimeError("Simulated DB Disk Crash"))

        graph = MathDebateGraph(cache_service=broken_cache)
        from unittest.mock import patch

        dummy_solver = lambda s: {**s, "solver_outputs": {"solver_1": {"success": True, "answer": "42"}}}
        dummy_judge = lambda s: {**s, "final_answer": "42", "judge_output": {"success": True, "best_agent": "solver_1", "best_solution": "42"}}

        with patch.object(graph, "_compiled_graph", None):
            with patch("graph.workflow.planner_node", side_effect=lambda s: {**s, "planner_output": {"needs_retrieval": False}}):
                with patch("graph.workflow.solver_1_node", side_effect=dummy_solver):
                    with patch("graph.workflow.solver_2_node", side_effect=dummy_solver):
                        with patch("graph.workflow.solver_3_node", side_effect=dummy_solver):
                            with patch("graph.workflow.reflection_node", side_effect=lambda s: s):
                                with patch("graph.workflow.judge_node", side_effect=dummy_judge):
                                    final_state = graph.execute("Solve x = 42")
                                    self.assertIsNotNone(final_state)
                                    self.assertEqual(final_state.get("final_answer"), "42")


if __name__ == "__main__":
    unittest.main()
