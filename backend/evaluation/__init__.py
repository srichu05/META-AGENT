"""Evaluation & Benchmarking Package for Meta-Agent Math Debate System.

Supports:
- Phase 3.2: LLM-as-a-Judge Evaluation Framework, MathVerifier, JudgeBenchmarkRunner
- Phase 3.0: RAGAS & Heuristic Benchmarking Layer
"""

from .benchmark_runner import BenchmarkRunner
from .dataset import GSM8KBenchmarkDataset, GSM8K_SUBSET
from .judge_runner import JudgeBenchmarkRunner
from .judge_types import (
    DimensionScore,
    JudgeEvaluationReport,
    JudgeReliabilityAnalysis,
    LLMJudgeEvaluationResult,
    SolverAgreementAnalysis,
)
from .llm_judge import LLMJudgeEvaluator
from .math_verifier import MathVerifier, VerificationResult
from .ragas_evaluator import RAGASEvaluator
from .types import (
    BenchmarkItem,
    BenchmarkReport,
    MetricScore,
    SingleEvaluationResult,
)

__all__ = [
    # Core dataset & legacy types
    "BenchmarkItem",
    "MetricScore",
    "SingleEvaluationResult",
    "BenchmarkReport",
    "GSM8KBenchmarkDataset",
    "GSM8K_SUBSET",
    "RAGASEvaluator",
    "BenchmarkRunner",
    # Phase 3.2: LLM-as-a-Judge Framework
    "DimensionScore",
    "SolverAgreementAnalysis",
    "JudgeReliabilityAnalysis",
    "LLMJudgeEvaluationResult",
    "JudgeEvaluationReport",
    "MathVerifier",
    "VerificationResult",
    "LLMJudgeEvaluator",
    "JudgeBenchmarkRunner",
]
