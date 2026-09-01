"""Test suite for RAGAS Evaluation and Benchmarking Subsystem (Session 7)."""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure backend directory is in sys.path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app
from database import db
from evaluation.dataset import GSM8KBenchmarkDataset, BenchmarkItem
from evaluation.ragas_evaluator import RAGASEvaluator
from evaluation.benchmark_runner import BenchmarkRunner
from evaluation.types import BenchmarkReport, MetricScore, SingleEvaluationResult


class TestEvaluationSubsystem(unittest.TestCase):
    """Unit and integration tests for RAGAS metrics, dataset loading, runner, and API."""

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_benchmark_dataset_loading(self):
        """Verify GSM8K benchmark dataset loader returns structured BenchmarkItems."""
        dataset = GSM8KBenchmarkDataset()
        items = dataset.get_all()
        self.assertGreaterEqual(len(items), 10)

        first_item = items[0]
        self.assertIsInstance(first_item, BenchmarkItem)
        self.assertEqual(first_item.question_id, "gsm8k_001")
        self.assertTrue(first_item.question)
        self.assertEqual(first_item.reference_answer, "72")

        subset = dataset.get_subset(limit=3)
        self.assertEqual(len(subset), 3)

    def test_ragas_evaluator_metrics(self):
        """Verify Faithfulness, Answer Relevance, Context Precision, and Context Recall metric scoring."""
        evaluator = RAGASEvaluator(use_ragas_lib=False)

        question = "Solve 4x - 12 = 28."
        reference_answer = "10"
        final_answer = "To solve 4x - 12 = 28, add 12 to both sides: 4x = 40. Divide by 4: x = 10. FINAL_ANSWER: 10"
        context_texts = [
            "Linear equation isolation: Add 12 to both sides -> 4x = 40. Divide by 4 -> x = 10.",
            "Reference context for algebraic steps.",
        ]

        scores = evaluator.evaluate_all(
            question=question,
            reference_answer=reference_answer,
            final_answer=final_answer,
            retrieved_context_texts=context_texts,
            expected_context="Add 12 to both sides -> 4x = 40. Divide by 4 -> x = 10.",
        )

        self.assertIn("faithfulness", scores)
        self.assertIn("answer_relevance", scores)
        self.assertIn("context_precision", scores)
        self.assertIn("context_recall", scores)

        for metric_name, score in scores.items():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_evaluation_result_schema_and_serialization(self):
        """Verify SingleEvaluationResult and BenchmarkReport JSON/CSV serialization."""
        item = GSM8KBenchmarkDataset().get_by_id("gsm8k_001")
        self.assertIsNotNone(item)

        eval_res = SingleEvaluationResult(
            question_id=item.question_id,
            question=item.question,
            reference_answer=item.reference_answer,
            final_answer="72",
            ragas_scores={"faithfulness": 0.95, "answer_relevance": 0.98},
            judge_result={"best_agent": "solver_1"},
            latency_ms=1250.0,
        )

        res_dict = eval_res.to_dict()
        self.assertEqual(res_dict["question_id"], "gsm8k_001")
        self.assertEqual(res_dict["ragas_scores"]["faithfulness"], 0.95)

        report = BenchmarkReport(
            total_questions=1,
            successful_evaluations=1,
            failed_evaluations=0,
            average_scores={"faithfulness": 0.95, "answer_relevance": 0.98},
            average_latency_ms=1250.0,
            results=[eval_res],
        )

        json_str = report.to_json()
        self.assertIn("gsm8k_001", json_str)

        csv_str = report.to_csv()
        self.assertIn("gsm8k_001", csv_str)
        self.assertIn("faithfulness", csv_str)

    @patch("evaluation.benchmark_runner.MathDebateGraph")
    def test_benchmark_runner_execution(self, mock_graph_cls):
        """Verify BenchmarkRunner executes items through graph and compiles BenchmarkReport."""
        mock_graph_instance = MagicMock()
        mock_graph_cls.return_value = mock_graph_instance

        mock_graph_instance.execute.return_value = {
            "final_answer": "72",
            "judge_output": {"best_agent": "solver_1", "confidence": 0.95},
            "solver_outputs": {"solver_1": {"answer": "72"}},
            "reflection_output": {"contradictions_found": False},
            "retrieved_context": {"chunks": [{"content": "April 48, May 24 -> 72"}]},
        }

        runner = BenchmarkRunner(graph=mock_graph_instance)
        report = runner.run_benchmark(limit=2)

        self.assertEqual(report.total_questions, 2)
        self.assertEqual(report.successful_evaluations, 2)
        self.assertIn("faithfulness", report.average_scores)

    def test_evaluation_api_endpoints(self):
        """Verify POST and GET /api/evaluation/benchmark REST API endpoints."""
        # 1. POST benchmark run (mocked graph execution)
        with patch("evaluation.benchmark_runner.MathDebateGraph") as mock_graph_cls:
            mock_graph = MagicMock()
            mock_graph_cls.return_value = mock_graph
            mock_graph.execute.return_value = {
                "final_answer": "72",
                "judge_output": {"best_agent": "solver_1"},
                "solver_outputs": {},
                "reflection_output": {},
                "retrieved_context": {"chunks": []},
            }

            resp = self.client.post("/api/evaluation/benchmark", json={"limit": 1})
            self.assertEqual(resp.status_code, 200)
            data = json.loads(resp.data)
            self.assertTrue(data.get("success"))
            self.assertIn("report", data)

            # 2. GET cached benchmark report
            resp_get = self.client.get("/api/evaluation/benchmark")
            self.assertEqual(resp_get.status_code, 200)
            data_get = json.loads(resp_get.data)
            self.assertTrue(data_get.get("success"))
            self.assertIn("report", data_get)

    def test_failure_handling_when_apis_unavailable(self):
        """Verify BenchmarkRunner handles graph node execution exceptions gracefully."""
        mock_graph = MagicMock()
        mock_graph.execute.side_effect = Exception("LLM Provider Timeout")

        runner = BenchmarkRunner(graph=mock_graph)
        item = GSM8KBenchmarkDataset().get_by_id("gsm8k_001")
        result = runner.run_single(item)

        self.assertIsNotNone(result.error)
        self.assertIn("LLM Provider Timeout", result.error)
        self.assertEqual(result.final_answer, "EVALUATION_ERROR")


if __name__ == "__main__":
    unittest.main()
