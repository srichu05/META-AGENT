"""Phase 3.2 — LLM-as-a-Judge Evaluation Types and Schemas.

Defines structured types for multi-dimensional evaluation results.
These types are separate from the existing debate evaluation types
and serve the independent LLM-as-a-Judge evaluation framework.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# Valid evaluation statuses
VALID_STATUSES = {"completed", "inconclusive", "failed", "not_applicable"}

# Valid evaluation modes
VALID_MODES = {"llm_judge", "reference_based", "heuristic", "hybrid"}


def _generate_evaluation_id() -> str:
    return f"eval_{uuid.uuid4().hex[:16]}"


@dataclass
class DimensionScore:
    """Score for a single evaluation dimension with bounded range [0.0, 1.0]."""

    score: Optional[float] = None
    status: str = "completed"
    reasoning: str = ""
    evidence: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.score is not None:
            if not isinstance(self.score, (int, float)):
                raise ValueError(f"Score must be numeric, got {type(self.score)}")
            if self.score < 0.0 or self.score > 1.0:
                raise ValueError(f"Score must be in [0.0, 1.0], got {self.score}")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{self.status}'. Must be one of {VALID_STATUSES}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 4) if self.score is not None else None,
            "status": self.status,
            "reasoning": self.reasoning,
            "evidence": self.evidence,
        }


@dataclass
class SolverAgreementAnalysis:
    """Analysis of agreement and divergence among solver agents."""

    solver_answers: Dict[str, str] = field(default_factory=dict)
    agreement_count: int = 0
    total_solvers: int = 0
    agreement_ratio: float = 0.0
    majority_answer: Optional[str] = None
    divergent_solvers: List[str] = field(default_factory=list)
    analysis_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "solver_answers": self.solver_answers,
            "agreement_count": self.agreement_count,
            "total_solvers": self.total_solvers,
            "agreement_ratio": round(self.agreement_ratio, 4),
            "majority_answer": self.majority_answer,
            "divergent_solvers": self.divergent_solvers,
            "analysis_notes": self.analysis_notes,
        }


@dataclass
class JudgeReliabilityAnalysis:
    """Assessment of whether the debate Judge selected the best available answer."""

    judge_selected_agent: Optional[str] = None
    judge_selected_answer: Optional[str] = None
    judge_selected_correct: Optional[bool] = None
    correct_solvers: List[str] = field(default_factory=list)
    any_solver_correct: Optional[bool] = None
    judge_missed_correct: bool = False
    judge_reasoning_quality: Optional[float] = None
    analysis_notes: str = ""
    status: str = "completed"

    def __post_init__(self):
        if self.judge_reasoning_quality is not None:
            if self.judge_reasoning_quality < 0.0 or self.judge_reasoning_quality > 1.0:
                raise ValueError("judge_reasoning_quality must be in [0.0, 1.0]")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{self.status}'")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "judge_selected_agent": self.judge_selected_agent,
            "judge_selected_answer": self.judge_selected_answer,
            "judge_selected_correct": self.judge_selected_correct,
            "correct_solvers": self.correct_solvers,
            "any_solver_correct": self.any_solver_correct,
            "judge_missed_correct": self.judge_missed_correct,
            "judge_reasoning_quality": (
                round(self.judge_reasoning_quality, 4)
                if self.judge_reasoning_quality is not None
                else None
            ),
            "analysis_notes": self.analysis_notes,
            "status": self.status,
        }


@dataclass
class LLMJudgeEvaluationResult:
    """Complete structured evaluation result for a single workflow execution.

    Contains six evaluation dimensions, solver/judge analysis, cache metadata,
    and provenance tracking for the evaluation model used.
    """

    # Identity
    evaluation_id: str = field(default_factory=_generate_evaluation_id)
    question_id: str = ""
    question: str = ""
    reference_answer: Optional[str] = None

    # System outputs being evaluated
    final_answer: str = ""
    solver_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    retrieved_context: List[Dict[str, Any]] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    judge_output: Dict[str, Any] = field(default_factory=dict)

    # Evaluation dimensions
    math_correctness: DimensionScore = field(default_factory=lambda: DimensionScore(status="not_applicable"))
    reasoning_validity: DimensionScore = field(default_factory=lambda: DimensionScore(status="not_applicable"))
    groundedness: DimensionScore = field(default_factory=lambda: DimensionScore(status="not_applicable"))
    citation_quality: DimensionScore = field(default_factory=lambda: DimensionScore(status="not_applicable"))
    completeness: DimensionScore = field(default_factory=lambda: DimensionScore(status="not_applicable"))

    # Solver and judge analysis
    solver_agreement: SolverAgreementAnalysis = field(default_factory=SolverAgreementAnalysis)
    judge_reliability: JudgeReliabilityAnalysis = field(default_factory=JudgeReliabilityAnalysis)

    # Overall assessment
    overall_assessment: Optional[str] = None
    overall_score: Optional[float] = None

    # Evaluation metadata
    evaluation_status: str = "completed"
    evaluation_mode: str = "llm_judge"
    evaluation_model: str = ""
    evaluation_provider: str = ""
    failure_reason: Optional[str] = None

    # Cache metadata
    is_cached_result: bool = False
    cache_hit_type: Optional[str] = None

    # Timestamp
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def __post_init__(self):
        if self.evaluation_status not in VALID_STATUSES:
            raise ValueError(f"Invalid evaluation_status '{self.evaluation_status}'")
        if self.evaluation_mode not in VALID_MODES:
            raise ValueError(f"Invalid evaluation_mode '{self.evaluation_mode}'")
        if self.overall_score is not None:
            if self.overall_score < 0.0 or self.overall_score > 1.0:
                raise ValueError(f"overall_score must be in [0.0, 1.0], got {self.overall_score}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "question_id": self.question_id,
            "question": self.question,
            "reference_answer": self.reference_answer,
            "final_answer": self.final_answer,
            "math_correctness": self.math_correctness.to_dict(),
            "reasoning_validity": self.reasoning_validity.to_dict(),
            "groundedness": self.groundedness.to_dict(),
            "citation_quality": self.citation_quality.to_dict(),
            "completeness": self.completeness.to_dict(),
            "solver_agreement": self.solver_agreement.to_dict(),
            "judge_reliability": self.judge_reliability.to_dict(),
            "overall_assessment": self.overall_assessment,
            "overall_score": round(self.overall_score, 4) if self.overall_score is not None else None,
            "evaluation_status": self.evaluation_status,
            "evaluation_mode": self.evaluation_mode,
            "evaluation_model": self.evaluation_model,
            "evaluation_provider": self.evaluation_provider,
            "failure_reason": self.failure_reason,
            "is_cached_result": self.is_cached_result,
            "cache_hit_type": self.cache_hit_type,
            "created_at": self.created_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class JudgeEvaluationReport:
    """Aggregated report across multiple LLM-as-a-Judge evaluation results."""

    total_evaluated: int = 0
    completed_count: int = 0
    inconclusive_count: int = 0
    failed_count: int = 0

    # Aggregate dimension scores (averages over completed evaluations)
    average_scores: Dict[str, Optional[float]] = field(default_factory=dict)

    # Judge reliability summary
    judge_correct_count: int = 0
    judge_missed_correct_count: int = 0
    solver_agreement_avg: float = 0.0

    # Cache tracking
    cached_results_count: int = 0
    fresh_results_count: int = 0

    # Evaluation metadata
    evaluation_mode: str = "llm_judge"
    evaluation_model: str = ""
    evaluation_provider: str = ""

    results: List[LLMJudgeEvaluationResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_evaluated": self.total_evaluated,
            "completed_count": self.completed_count,
            "inconclusive_count": self.inconclusive_count,
            "failed_count": self.failed_count,
            "average_scores": {
                k: round(v, 4) if v is not None else None
                for k, v in self.average_scores.items()
            },
            "judge_correct_count": self.judge_correct_count,
            "judge_missed_correct_count": self.judge_missed_correct_count,
            "solver_agreement_avg": round(self.solver_agreement_avg, 4),
            "cached_results_count": self.cached_results_count,
            "fresh_results_count": self.fresh_results_count,
            "evaluation_mode": self.evaluation_mode,
            "evaluation_model": self.evaluation_model,
            "evaluation_provider": self.evaluation_provider,
            "results": [r.to_dict() for r in self.results],
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_csv(self) -> str:
        """Serializes LLM Judge evaluation results to CSV format."""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "evaluation_id",
            "question_id",
            "question",
            "reference_answer",
            "final_answer",
            "math_correctness_score",
            "math_correctness_status",
            "reasoning_validity_score",
            "groundedness_score",
            "citation_quality_score",
            "completeness_score",
            "overall_score",
            "evaluation_status",
            "solver_agreement_ratio",
            "judge_selected_correct",
            "is_cached_result",
            "evaluation_provider",
            "evaluation_model",
        ])
        for r in self.results:
            writer.writerow([
                r.evaluation_id,
                r.question_id,
                (r.question or "").replace("\n", " "),
                (r.reference_answer or "").replace("\n", " "),
                (r.final_answer or "").replace("\n", " "),
                r.math_correctness.score if r.math_correctness.score is not None else "",
                r.math_correctness.status,
                r.reasoning_validity.score if r.reasoning_validity.score is not None else "",
                r.groundedness.score if r.groundedness.score is not None else "",
                r.citation_quality.score if r.citation_quality.score is not None else "",
                r.completeness.score if r.completeness.score is not None else "",
                r.overall_score if r.overall_score is not None else "",
                r.evaluation_status,
                r.solver_agreement.agreement_ratio,
                r.judge_reliability.judge_selected_correct if r.judge_reliability.judge_selected_correct is not None else "",
                r.is_cached_result,
                r.evaluation_provider,
                r.evaluation_model,
            ])
        return output.getvalue()

