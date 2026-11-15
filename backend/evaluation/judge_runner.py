"""Phase 3.2 — LLM-as-a-Judge Benchmark Runner.

Orchestrates evaluation of benchmark datasets (e.g., GSM8K, project math problems)
using LLMJudgeEvaluator and MathVerifier. Computes aggregated statistics across all dimensions,
records judge accuracy, solver agreement, and saves outputs to JSON and CSV.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from evaluation.dataset import GSM8KBenchmarkDataset
from evaluation.judge_types import (
    JudgeEvaluationReport,
    LLMJudgeEvaluationResult,
)
from evaluation.llm_judge import LLMJudgeEvaluator
from evaluation.types import BenchmarkItem
from graph.workflow import MathDebateGraph

logger = logging.getLogger(__name__)


class JudgeBenchmarkRunner:
    """Orchestrates LLM-as-a-Judge evaluation across benchmark datasets and workflows."""

    def __init__(
        self,
        dataset: Optional[GSM8KBenchmarkDataset] = None,
        evaluator: Optional[LLMJudgeEvaluator] = None,
        graph: Optional[MathDebateGraph] = None,
        output_dir: Optional[str] = None,
    ):
        self.dataset = dataset or GSM8KBenchmarkDataset()
        self.evaluator = evaluator or LLMJudgeEvaluator()
        self.graph = graph or MathDebateGraph()

        backend_dir = Path(__file__).resolve().parents[1]
        self.output_dir = Path(output_dir) if output_dir else backend_dir / "evaluation" / "results"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def evaluate_single_item(
        self,
        item: BenchmarkItem,
        precomputed_state: Optional[Dict[str, Any]] = None,
    ) -> LLMJudgeEvaluationResult:
        """Executes workflow for a single benchmark item and evaluates it."""
        logger.info(f"📋 JudgeBenchmarkRunner evaluating item '{item.question_id}': '{item.question[:60]}...'")

        # Use precomputed state or execute workflow
        if precomputed_state is not None:
            state = precomputed_state
        else:
            state = self.graph.execute(item.question)

        # Run evaluation
        result = self.evaluator.evaluate_workflow(
            state=state,
            reference_answer=item.reference_answer,
            question_id=item.question_id,
        )
        return result

    def run_benchmark(
        self,
        limit: int = 5,
        save_results: bool = True,
        save_prefix: str = "judge_benchmark",
    ) -> JudgeEvaluationReport:
        """Executes benchmark over a subset of items and compiles aggregate report."""
        items = self.dataset.get_subset(limit=limit)
        logger.info(f"🚀 Starting LLM-as-a-Judge benchmark run over {len(items)} items...")

        results: List[LLMJudgeEvaluationResult] = []
        completed_count = 0
        inconclusive_count = 0
        failed_count = 0

        # Score accumulators for completed evaluations
        dim_sums: Dict[str, float] = {
            "math_correctness": 0.0,
            "reasoning_validity": 0.0,
            "groundedness": 0.0,
            "citation_quality": 0.0,
            "completeness": 0.0,
            "overall_score": 0.0,
        }
        dim_counts: Dict[str, int] = {k: 0 for k in dim_sums}

        judge_correct = 0
        judge_missed = 0
        agreement_ratios: List[float] = []
        cached_count = 0
        fresh_count = 0

        for item in items:
            res = self.evaluate_single_item(item)
            results.append(res)

            if res.is_cached_result:
                cached_count += 1
            else:
                fresh_count += 1

            if res.evaluation_status == "completed":
                completed_count += 1
            elif res.evaluation_status == "inconclusive":
                inconclusive_count += 1
            else:
                failed_count += 1

            # Accumulate scores where available
            self._accumulate_dimension(res.math_correctness.score, "math_correctness", dim_sums, dim_counts)
            self._accumulate_dimension(res.reasoning_validity.score, "reasoning_validity", dim_sums, dim_counts)
            self._accumulate_dimension(res.groundedness.score, "groundedness", dim_sums, dim_counts)
            self._accumulate_dimension(res.citation_quality.score, "citation_quality", dim_sums, dim_counts)
            self._accumulate_dimension(res.completeness.score, "completeness", dim_sums, dim_counts)
            self._accumulate_dimension(res.overall_score, "overall_score", dim_sums, dim_counts)

            # Judge reliability
            if res.judge_reliability.judge_selected_correct is True:
                judge_correct += 1
            if res.judge_reliability.judge_missed_correct:
                judge_missed += 1

            # Solver agreement
            agreement_ratios.append(res.solver_agreement.agreement_ratio)

        # Compute averages
        average_scores: Dict[str, Optional[float]] = {}
        for dim, count in dim_counts.items():
            if count > 0:
                average_scores[dim] = round(dim_sums[dim] / count, 4)
            else:
                average_scores[dim] = None

        avg_agreement = sum(agreement_ratios) / len(agreement_ratios) if agreement_ratios else 0.0

        report = JudgeEvaluationReport(
            total_evaluated=len(items),
            completed_count=completed_count,
            inconclusive_count=inconclusive_count,
            failed_count=failed_count,
            average_scores=average_scores,
            judge_correct_count=judge_correct,
            judge_missed_correct_count=judge_missed,
            solver_agreement_avg=round(avg_agreement, 4),
            cached_results_count=cached_count,
            fresh_results_count=fresh_count,
            evaluation_mode="llm_judge",
            evaluation_model=self.evaluator.model or "default",
            evaluation_provider=self.evaluator.target_provider or "UNKNOWN",
            results=results,
        )

        if save_results:
            self._save_report(report, save_prefix)

        logger.info(
            f"✅ LLM-as-a-Judge benchmark finished: {completed_count}/{len(items)} completed, "
            f"{inconclusive_count} inconclusive, {failed_count} failed. "
            f"Averages: {report.average_scores}"
        )
        return report

    def _accumulate_dimension(
        self,
        score: Optional[float],
        dim_key: str,
        sums: Dict[str, float],
        counts: Dict[str, int],
    ) -> None:
        if score is not None:
            sums[dim_key] += score
            counts[dim_key] += 1

    def _save_report(self, report: JudgeEvaluationReport, prefix: str) -> None:
        """Saves evaluation report to JSON and CSV files."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        json_path = self.output_dir / f"{prefix}_{timestamp}.json"
        csv_path = self.output_dir / f"{prefix}_{timestamp}.csv"

        try:
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(report.to_json())
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write(report.to_csv())
            logger.info(f"💾 Evaluation reports saved to:\n  - {json_path}\n  - {csv_path}")
        except Exception as e:
            logger.error(f"Failed to save evaluation reports: {e}", exc_info=True)

