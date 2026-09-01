"""Benchmark Runner orchestrating Meta-Agent workflow execution and RAGAS metric compilation."""

import logging
import time
from typing import Any, Dict, List, Optional

from graph.workflow import MathDebateGraph
from providers.router import ProviderRouter

from .dataset import GSM8KBenchmarkDataset
from .ragas_evaluator import RAGASEvaluator
from .types import BenchmarkItem, BenchmarkReport, SingleEvaluationResult

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Executes GSM8K benchmark questions through MathDebateGraph and evaluates RAGAS metrics."""

    def __init__(
        self,
        dataset: Optional[GSM8KBenchmarkDataset] = None,
        evaluator: Optional[RAGASEvaluator] = None,
        graph: Optional[MathDebateGraph] = None,
    ):
        self.dataset = dataset or GSM8KBenchmarkDataset()
        self.evaluator = evaluator or RAGASEvaluator()
        self.graph = graph or MathDebateGraph()
        self.router = ProviderRouter()

    def run_single(self, item: BenchmarkItem) -> SingleEvaluationResult:
        """
        Executes a single benchmark question through MathDebateGraph and RAGAS evaluator.
        """
        start_time = time.time()
        logger.info(f"📊 Running benchmark item '{item.question_id}': '{item.question[:60]}...'")

        try:
            state = self.graph.execute(item.question)
            latency_ms = (time.time() - start_time) * 1000.0

            judge_out = state.get("judge_output", {})
            final_ans = state.get("final_answer") or judge_out.get("best_solution", "")
            solver_outs = state.get("solver_outputs", {})
            reflection_out = state.get("reflection_output", {})
            raw_retrieved = state.get("retrieved_context", {})

            # Extract retrieved chunk texts
            chunks_data = raw_retrieved.get("chunks", [])
            retrieved_texts = [c.get("content", "") for c in chunks_data if isinstance(c, dict)]

            # Run RAGAS metric evaluation
            ragas_scores = self.evaluator.evaluate_all(
                question=item.question,
                reference_answer=item.reference_answer,
                final_answer=final_ans,
                retrieved_context_texts=retrieved_texts,
                expected_context=item.expected_context,
            )

            metrics_summary = self.router.get_metrics_summary()

            return SingleEvaluationResult(
                question_id=item.question_id,
                question=item.question,
                reference_answer=item.reference_answer,
                final_answer=final_ans,
                retrieved_context=chunks_data,
                ragas_scores=ragas_scores,
                solver_outputs=solver_outs,
                reflection_result=reflection_out,
                judge_result=judge_out,
                provider_info=metrics_summary,
                latency_ms=latency_ms,
            )
        except Exception as error:
            latency_ms = (time.time() - start_time) * 1000.0
            logger.error(f"❌ Error during benchmark evaluation for '{item.question_id}': {error}", exc_info=True)
            return SingleEvaluationResult(
                question_id=item.question_id,
                question=item.question,
                reference_answer=item.reference_answer,
                final_answer="EVALUATION_ERROR",
                latency_ms=latency_ms,
                error=str(error),
            )

    def run_benchmark(self, limit: int = 5) -> BenchmarkReport:
        """
        Executes a benchmark run over a subset of benchmark dataset items.
        Returns a compiled BenchmarkReport.
        """
        items = self.dataset.get_subset(limit=limit)
        logger.info(f"🚀 Starting benchmark evaluation over {len(items)} questions...")

        results: List[SingleEvaluationResult] = []
        successful_count = 0
        failed_count = 0

        metric_sums: Dict[str, float] = {
            "faithfulness": 0.0,
            "answer_relevance": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
        }
        total_latency = 0.0

        for item in items:
            res = self.run_single(item)
            results.append(res)
            total_latency += res.latency_ms

            if not res.error:
                successful_count += 1
                for k, v in res.ragas_scores.items():
                    metric_sums[k] = metric_sums.get(k, 0.0) + v
            else:
                failed_count += 1

        total = len(items)
        avg_scores = {}
        if successful_count > 0:
            avg_scores = {k: v / successful_count for k, v in metric_sums.items()}

        avg_latency = total_latency / total if total > 0 else 0.0

        report = BenchmarkReport(
            total_questions=total,
            successful_evaluations=successful_count,
            failed_evaluations=failed_count,
            average_scores=avg_scores,
            average_latency_ms=avg_latency,
            results=results,
        )

        logger.info(
            f"✅ Benchmark finished: {successful_count}/{total} successful. "
            f"Avg Scores: {report.average_scores} | Avg Latency: {report.average_latency_ms:.1f}ms"
        )
        return report
