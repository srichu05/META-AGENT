"""REST API endpoints for evaluation and benchmarking subsystem."""

import time
import logging
from flask import Blueprint, current_app, jsonify, request

from evaluation.benchmark_runner import BenchmarkRunner

evaluation_blueprint = Blueprint("evaluation", __name__, url_prefix="/api/evaluation")

logger = logging.getLogger(__name__)


def _runner() -> BenchmarkRunner:
    runner = current_app.extensions.get("benchmark_runner")
    if runner is None:
        runner = BenchmarkRunner()
        current_app.extensions["benchmark_runner"] = runner
    return runner


@evaluation_blueprint.route("/benchmark", methods=["POST"])
def run_benchmark():
    """Triggers benchmark evaluation over GSM8K dataset items."""
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
    """Returns the latest benchmark evaluation report summary."""
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
