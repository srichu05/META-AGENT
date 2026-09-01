"""Structured Evaluation & Benchmarking Dataclasses for Meta-Agent Math Debate System."""

import csv
import io
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class BenchmarkItem:
    """A single benchmark problem item in the dataset."""

    question_id: str
    question: str
    reference_answer: str
    expected_context: str = ""
    category: str = "math"
    difficulty: str = "medium"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "question": self.question,
            "reference_answer": self.reference_answer,
            "expected_context": self.expected_context,
            "category": self.category,
            "difficulty": self.difficulty,
            "metadata": self.metadata,
        }


@dataclass
class MetricScore:
    """Individual metric evaluation score."""

    metric_name: str
    score: float
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "score": round(self.score, 4),
            "reasoning": self.reasoning,
            "metadata": self.metadata,
        }


@dataclass
class SingleEvaluationResult:
    """Complete evaluation result for a single benchmark query."""

    question_id: str
    question: str
    reference_answer: str
    final_answer: str
    retrieved_context: List[Dict[str, Any]] = field(default_factory=list)
    ragas_scores: Dict[str, float] = field(default_factory=dict)
    solver_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    reflection_result: Dict[str, Any] = field(default_factory=dict)
    judge_result: Dict[str, Any] = field(default_factory=dict)
    provider_info: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "question": self.question,
            "reference_answer": self.reference_answer,
            "final_answer": self.final_answer,
            "retrieved_context": self.retrieved_context,
            "ragas_scores": {k: round(v, 4) for k, v in self.ragas_scores.items()},
            "solver_outputs": self.solver_outputs,
            "reflection_result": self.reflection_result,
            "judge_result": self.judge_result,
            "provider_info": self.provider_info,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class BenchmarkReport:
    """Aggregated report across multiple evaluated benchmark items."""

    total_questions: int
    successful_evaluations: int
    failed_evaluations: int
    average_scores: Dict[str, float] = field(default_factory=dict)
    average_latency_ms: float = 0.0
    results: List[SingleEvaluationResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_questions": self.total_questions,
            "successful_evaluations": self.successful_evaluations,
            "failed_evaluations": self.failed_evaluations,
            "average_scores": {k: round(v, 4) for k, v in self.average_scores.items()},
            "average_latency_ms": round(self.average_latency_ms, 2),
            "results": [r.to_dict() for r in self.results],
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_csv(self) -> str:
        """Serializes benchmark results to CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "question_id",
            "question",
            "reference_answer",
            "final_answer",
            "faithfulness",
            "answer_relevance",
            "context_precision",
            "context_recall",
            "best_solver",
            "latency_ms",
            "status",
        ])
        for r in self.results:
            scores = r.ragas_scores or {}
            writer.writerow([
                r.question_id,
                r.question.replace("\n", " "),
                r.reference_answer,
                r.final_answer.replace("\n", " ") if r.final_answer else "",
                scores.get("faithfulness", 0.0),
                scores.get("answer_relevance", 0.0),
                scores.get("context_precision", 0.0),
                scores.get("context_recall", 0.0),
                r.judge_result.get("best_agent", "N/A"),
                round(r.latency_ms, 2),
                "SUCCESS" if not r.error else f"ERROR: {r.error}",
            ])
        return output.getvalue()
