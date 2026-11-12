"""REST API endpoints for evaluation and benchmarking subsystem.

Supports:
- Phase 3.0: RAGAS / Heuristic evaluation endpoints (/api/evaluation/status, /api/evaluation/benchmark)
- Phase 3.2: LLM-as-a-Judge evaluation endpoints (/api/evaluation/judge/*)
"""

import logging
import time
from typing import Any, Dict, Optional
from flask import Blueprint, current_app, jsonify, request

from evaluation.benchmark_runner import BenchmarkRunner
from evaluation.judge_runner import JudgeBenchmarkRunner
from evaluation.llm_judge import LLMJudgeEvaluator
from graph.workflow import MathDebateGraph

evaluation_blueprint = Blueprint("evaluation", __name__, url_prefix="/api/evaluation")

logger = logging.getLogger(__name__)


def _runner() -> BenchmarkRunner:
    runner = current_app.extensions.get("benchmark_runner")
    if runner is None:
        runner = BenchmarkRunner()
        current_app.extensions["benchmark_runner"] = runner
    return runner


def _judge_evaluator() -> LLMJudgeEvaluator:
    evaluator = current_app.extensions.get("llm_judge_evaluator")
    if evaluator is None:
        evaluator = LLMJudgeEvaluator()
        current_app.extensions["llm_judge_evaluator"] = evaluator
    return evaluator


def _judge_runner() -> JudgeBenchmarkRunner:
    runner = current_app.extensions.get("judge_benchmark_runner")
    if runner is None:
        runner = JudgeBenchmarkRunner(evaluator=_judge_evaluator())
        current_app.extensions["judge_benchmark_runner"] = runner
    return runner


# ═══════════════════════════════════════════════════════════════════════
# Phase 3.0: RAGAS & Heuristic Benchmarking Endpoints
# ═══════════════════════════════════════════════════════════════════════


@evaluation_blueprint.route("/status", methods=["GET"])
def get_evaluation_status():
    """Returns evaluation subsystem readiness, installed libraries, and active evaluation mode."""
    meta = _runner().evaluator.get_evaluation_metadata()
    return jsonify({"success": True, **meta}), 200


@evaluation_blueprint.route("/benchmark", methods=["POST"])
def run_benchmark():
    """Triggers benchmark evaluation over GSM8K dataset items (RAGAS/heuristic mode)."""
    try:
        data = request.get_json(silent=True) or {}
        limit = int(data.get("limit", data.get("question_limit", 3)))
        limit = max(1, min(10, limit))

        logger.info(f"📊 REST /api/evaluation/benchmark POST request (limit={limit})...")
        report = _runner().run_benchmark(limit=limit)

        # Cache latest report in app extension
        current_app.extensions["latest_benchmark_report"] = report

        return jsonify({"success": True, "report": report.to_dict()}), 200
    except Exception as error:
        logger.exception("Benchmark evaluation execution failed unexpectedly")
        return jsonify({"success": False, "error": str(error)}), 500


@evaluation_blueprint.route("/benchmark", methods=["GET"])
def get_benchmark_report():
    """Returns the latest benchmark evaluation report summary (RAGAS/heuristic mode)."""
    try:
        cached_report = current_app.extensions.get("latest_benchmark_report")
        if cached_report is not None:
            return jsonify({"success": True, "cached": True, "report": cached_report.to_dict()}), 200

        # If no report cached, run lightweight 1-item benchmark
        report = _runner().run_benchmark(limit=1)
        current_app.extensions["latest_benchmark_report"] = report
        return jsonify({"success": True, "cached": False, "report": report.to_dict()}), 200
    except Exception as error:
        logger.exception("Fetching benchmark report failed")
        return jsonify({"success": False, "error": str(error)}), 500


# ═══════════════════════════════════════════════════════════════════════
# Phase 3.2: LLM-as-a-Judge Evaluation Endpoints
# ═══════════════════════════════════════════════════════════════════════


@evaluation_blueprint.route("/judge/config", methods=["GET"])
def get_judge_config():
    """Returns LLM Judge configuration, target provider, model, and independence status."""
    evaluator = _judge_evaluator()
    sample_state = {"solver_outputs": {"solver_1": {"actual_provider": "GEMINI"}}}
    independence = evaluator.check_evaluator_independence(sample_state)

    return jsonify({
        "success": True,
        "evaluator_provider": evaluator.target_provider,
        "evaluator_model": evaluator.model or "default",
        "fallback_order": evaluator.fallback_order,
        "temperature": evaluator.temperature,
        "deterministic_verification_enabled": evaluator.deterministic_verify_enabled,
        "sample_independence_check": independence,
    }), 200


@evaluation_blueprint.route("/judge/evaluate", methods=["POST"])
def evaluate_workflow_result():
    """Evaluates a completed workflow state or executes a problem and evaluates it.

    Payload options:
    1. { "state": { ... }, "reference_answer": "optional" }
    2. { "query": "...", "reference_answer": "optional" }
    """
    try:
        data = request.get_json(force=True) or {}
        reference_answer = data.get("reference_answer")
        question_id = data.get("question_id", "")

        state = data.get("state")
        if not state:
            query = (data.get("query") or data.get("problem") or "").strip()
            if not query:
                return jsonify({
                    "success": False,
                    "error": "Must provide either 'state' object or 'query' text.",
                }), 400

            graph = current_app.extensions.get("math_debate_graph") or MathDebateGraph()
            state = graph.execute(query)

        evaluator = _judge_evaluator()
        result = evaluator.evaluate_workflow(
            state=state,
            reference_answer=reference_answer,
            question_id=question_id,
        )

        return jsonify({"success": True, "evaluation": result.to_dict()}), 200

    except Exception as error:
        logger.exception("LLM Judge evaluation request failed")
        return jsonify({"success": False, "error": str(error)}), 500


@evaluation_blueprint.route("/judge/benchmark", methods=["POST"])
def run_judge_benchmark():
    """Runs LLM-as-a-Judge evaluation benchmark over dataset items."""
    try:
        data = request.get_json(silent=True) or {}
        limit = int(data.get("limit", data.get("question_limit", 3)))
        limit = max(1, min(10, limit))

        logger.info(f"⚖️ REST /api/evaluation/judge/benchmark POST request (limit={limit})...")
        runner = _judge_runner()
        report = runner.run_benchmark(limit=limit, save_results=True)

        current_app.extensions["latest_judge_benchmark_report"] = report

        return jsonify({"success": True, "report": report.to_dict()}), 200

    except Exception as error:
        logger.exception("LLM Judge benchmark execution failed")
        return jsonify({"success": False, "error": str(error)}), 500


@evaluation_blueprint.route("/judge/report", methods=["GET"])
def get_judge_report():
    """Returns the latest LLM Judge benchmark report."""
    try:
        cached_report = current_app.extensions.get("latest_judge_benchmark_report")
        if cached_report is not None:
            return jsonify({"success": True, "cached": True, "report": cached_report.to_dict()}), 200

        runner = _judge_runner()
        report = runner.run_benchmark(limit=1, save_results=False)
        current_app.extensions["latest_judge_benchmark_report"] = report
        return jsonify({"success": True, "cached": False, "report": report.to_dict()}), 200

    except Exception as error:
        logger.exception("Fetching LLM Judge report failed")
        return jsonify({"success": False, "error": str(error)}), 500
