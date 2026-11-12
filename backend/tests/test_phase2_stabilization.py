"""Phase 2 Stabilization Test Suite for Meta-Agent Math Debate System."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app
from database import db
from models.document import Document, DocumentChunk
from providers.types import ProviderResponse
from providers.router import ProviderRouter, _categorize_error
from agents.math_solver import MathSolverAgent
from retrieval.types import RetrievedContext, RetrievedChunk
from retrieval.service import RetrievalService
from retrieval.reranker import CohereRerankerAdapter
from graph.workflow import MathDebateGraph
from graph.state import create_initial_state
from evaluation.ragas_evaluator import RAGASEvaluator
from evaluation.types import SingleEvaluationResult, BenchmarkReport


class TestPhase2Stabilization(unittest.TestCase):
    """Verifies all Phase 2 runtime stabilization fixes."""

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        db.session.rollback()
        self.app_context.pop()

    def test_database_schema_and_models(self):
        """Verify PostgreSQL tables and ORM mappings exist and function correctly."""
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()

        self.assertIn("documents", table_names)
        self.assertIn("document_chunks", table_names)
        self.assertIn("alembic_version", table_names)
        # Ensure legacy student table was preserved
        self.assertIn("student", table_names)

    def test_provider_router_error_categorization(self):
        """Verify standardized categorization of API error responses."""
        self.assertEqual(_categorize_error("401 Unauthorized: Invalid API key"), "AUTHENTICATION_ERROR")
        self.assertEqual(_categorize_error("429 ResourceExhausted: rate limit exceeded"), "RATE_LIMIT")
        self.assertEqual(_categorize_error("404 Not Found: model deepseek does not exist"), "MODEL_NOT_FOUND")
        self.assertEqual(_categorize_error("Connection timed out after 10000ms"), "TIMEOUT")
        self.assertEqual(_categorize_error("503 Service Unavailable: overloaded"), "SERVER_ERROR")
        self.assertEqual(_categorize_error("Unknown network fault"), "PROVIDER_ERROR")

    def test_provider_router_fallback_observability(self):
        """Verify that provider fallback populates all required observability metadata."""
        router = ProviderRouter()

        # Mock adapters: GROQ fails, GEMINI succeeds
        mock_groq = MagicMock()
        mock_groq.is_configured = True
        mock_groq.generate.return_value = ProviderResponse(
            success=False,
            provider="GROQ",
            model="llama-3.3-70b-versatile",
            error="404 Model llama-3.3-70b-versatile not found",
        )

        mock_gemini = MagicMock()
        mock_gemini.is_configured = True
        mock_gemini.generate.return_value = ProviderResponse(
            success=True,
            answer="42",
            raw_text="The answer is 42",
            provider="GEMINI",
            model="gemini-2.5-flash",
            latency_ms=350.0,
        )

        router.adapters["GROQ"] = mock_groq
        router.adapters["GEMINI"] = mock_gemini

        res = router.generate(
            prompt="What is the answer?",
            target_provider="GROQ",
            fallback_order=["GROQ", "GEMINI"],
        )

        self.assertTrue(res.success)
        self.assertEqual(res.intended_provider, "GROQ")
        self.assertEqual(res.actual_provider, "GEMINI")
        self.assertEqual(res.actual_model, "gemini-2.5-flash")
        self.assertTrue(res.fallback_occurred)
        self.assertIsNotNone(res.fallback_reason)
        self.assertIn("MODEL_NOT_FOUND", res.fallback_reason)
        self.assertEqual(res.attempts, 2)

        res_dict = res.to_dict()
        self.assertEqual(res_dict["intended_provider"], "GROQ")
        self.assertEqual(res_dict["actual_provider"], "GEMINI")
        self.assertTrue(res_dict["fallback_occurred"])

    def test_solver_agent_fallback_attribution(self):
        """Verify MathSolverAgent output preserves provider attribution and fallback metadata."""
        mock_router = MagicMock()
        mock_router.generate.return_value = ProviderResponse(
            success=True,
            answer="10",
            raw_text="Step 1: x = 10. FINAL_ANSWER: 10",
            reasoning="Step 1: x = 10.",
            provider="GEMINI",
            model="gemini-2.5-flash",
            intended_provider="GROQ",
            actual_provider="GEMINI",
            actual_model="gemini-2.5-flash",
            fallback_occurred=True,
            fallback_reason="GROQ failed",
            attempts=2,
            latency_ms=400.0,
        )

        solver = MathSolverAgent("solver_2", "Fast Problem Solver", target_provider="GROQ", router=mock_router)
        out = solver.solve_problem("Solve 2x = 20")

        self.assertTrue(out["success"])
        self.assertEqual(out["intended_provider"], "GROQ")
        self.assertEqual(out["actual_provider"], "GEMINI")
        self.assertEqual(out["actual_model"], "gemini-2.5-flash")
        self.assertTrue(out["fallback_occurred"])
        self.assertEqual(out["fallback_reason"], "GROQ failed")
        self.assertEqual(out["attempts"], 2)

    def test_retrieved_context_schema_and_empty_observability(self):
        """Verify RetrievedContext includes error and rerank_status fields and explains empty results."""
        ctx = RetrievedContext(
            query="test query",
            formatted_context="No relevant document context found.",
            error="Simulated DB Error",
            rerank_status="skipped_disabled",
        )
        ctx_dict = ctx.to_dict()
        self.assertEqual(ctx_dict["error"], "Simulated DB Error")
        self.assertEqual(ctx_dict["rerank_status"], "skipped_disabled")
        self.assertIn("error", ctx_dict)
        self.assertIn("rerank_status", ctx_dict)

    def test_reranker_status_tracking(self):
        """Verify CohereRerankerAdapter tracks its execution status accurately."""
        adapter = CohereRerankerAdapter(api_key="")
        dummy_chunk = RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            filename="math.txt",
            file_type="txt",
            page_number=1,
            section_heading="Test",
            char_start=0,
            char_end=50,
            vector_index=0,
            content="Sample math content",
            score=0.9,
        )

        # With empty API key, status should be skipped_missing_credentials
        res = adapter.rerank("query", [dummy_chunk])
        self.assertEqual(adapter.last_status, "skipped_missing_credentials")

        # With disabled config, status should be skipped_disabled
        adapter_with_key = CohereRerankerAdapter(api_key="mock_cohere_key")
        res2 = adapter_with_key.rerank("query", [dummy_chunk])
        self.assertEqual(adapter_with_key.last_status, "skipped_disabled")

        # With empty chunks, status should be skipped_empty
        res_empty = adapter.rerank("query", [])
        self.assertEqual(adapter.last_status, "skipped_empty")

    def test_graph_state_initialization_and_execution_mode(self):
        """Verify DebateGraphState initializes execution_mode and partial_execution fields."""
        state = create_initial_state("Solve x + 1 = 2")
        self.assertEqual(state["execution_mode"], "uninitialized")
        self.assertFalse(state["partial_execution"])
        self.assertIsNone(state["failed_node"])

    def test_ragas_evaluator_mode_reporting(self):
        """Verify RAGASEvaluator reports evaluation_mode and does not masquerade as genuine RAGAS."""
        evaluator = RAGASEvaluator(use_ragas_lib=False)
        meta = evaluator.get_evaluation_metadata()

        self.assertIn("evaluation_mode", meta)
        self.assertIn("ragas_installed", meta)
        self.assertEqual(meta["evaluation_mode"], "heuristic")
        self.assertFalse(meta["ragas_installed"])
        self.assertIn("heuristic", meta["description"].lower())

    def test_single_evaluation_result_mode_serialization(self):
        """Verify SingleEvaluationResult and BenchmarkReport serialize evaluation_mode."""
        eval_res = SingleEvaluationResult(
            question_id="test_01",
            question="What is 2+2?",
            reference_answer="4",
            final_answer="4",
            evaluation_mode="heuristic",
            ragas_installed=False,
        )
        res_dict = eval_res.to_dict()
        self.assertEqual(res_dict["evaluation_mode"], "heuristic")
        self.assertFalse(res_dict["ragas_installed"])

        report = BenchmarkReport(
            total_questions=1,
            successful_evaluations=1,
            failed_evaluations=0,
            results=[eval_res],
            evaluation_mode="heuristic",
            ragas_installed=False,
        )
        report_dict = report.to_dict()
        self.assertEqual(report_dict["evaluation_mode"], "heuristic")
        self.assertFalse(report_dict["ragas_installed"])

    def test_citation_grounding_filter(self):
        """Verify that citations are only preserved when genuinely grounded in final answer."""
        from graph.nodes import _is_citation_grounded

        math_citation = {
            "citation_id": "[mathematics_reference_guide.txt]",
            "filename": "mathematics_reference_guide.txt",
            "snippet": "Euler's formula states that e^(i*pi) + 1 = 0 linking five fundamental constants.",
        }

        # Case 1: Answer discusses Euler's formula and cites guide -> Grounded
        ans_grounded = "According to mathematics_reference_guide.txt, Euler's formula links fundamental constants."
        self.assertTrue(_is_citation_grounded(math_citation, ans_grounded))

        # Case 2: Answer discusses completely unrelated topic (Australia capital) -> NOT grounded
        ans_unrelated = "The capital city of Australia is Canberra with an estimated population of 450,000."
        self.assertFalse(_is_citation_grounded(math_citation, ans_unrelated))


if __name__ == "__main__":
    unittest.main()
