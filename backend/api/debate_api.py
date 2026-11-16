"""REST API blueprint for LangGraph multi-agent math debate execution."""

import os
import time
from flask import Blueprint, current_app, jsonify, request

from graph.workflow import MathDebateGraph
from security import get_current_user, rate_limit, require_auth
from utils.observability import get_correlation_id

graph_debate_blueprint = Blueprint("graph_debate", __name__, url_prefix="/api/debate")


def _graph() -> MathDebateGraph:
    graph = current_app.extensions.get("math_debate_graph")
    if graph is None:
        graph = MathDebateGraph()
        current_app.extensions["math_debate_graph"] = graph
    return graph


@graph_debate_blueprint.route("/graph", methods=["POST"])
@require_auth()
@rate_limit(scope="debate")
def run_graph_debate():
    """Execute full LangGraph multi-agent debate workflow over a problem query."""
    start_time = time.time()
    data = request.get_json(force=True) or {}
    problem = (data.get("problem") or data.get("query") or "").strip()

    if not problem:
        return jsonify({"success": False, "error": "Problem text is required."}), 400

    max_len = int(os.getenv("MAX_QUERY_LENGTH", "5000"))
    if len(problem) > max_len:
        return jsonify({
            "success": False,
            "error": f"Problem text ({len(problem)} chars) exceeds maximum allowed ({max_len} chars).",
        }), 400

    try:
        cid = get_correlation_id()
        current_user = get_current_user() or {}
        user_id = current_user.get("user_id")

        current_app.logger.info(f"[{cid}] 🎪 /api/debate/graph request: '{problem[:80]}...' (user={user_id})")
        graph_state = _graph().execute(problem, correlation_id=cid, user_id=user_id)
        elapsed_s = time.time() - start_time

        judge_out = graph_state.get("judge_output", {})
        best_solution = graph_state.get("final_answer") or judge_out.get("best_solution", "")
        best_agent = judge_out.get("best_agent", "Solver_1")

        from providers.router import ProviderRouter
        router = ProviderRouter()

        retrieved = graph_state.get("retrieved_context") or {}
        chunks_retrieved = len(retrieved.get("chunks", [])) if isinstance(retrieved, dict) else 0

        telemetry = {
            "correlation_id": cid,
            "status": graph_state.get("status", "completed"),
            "partial_execution": bool(graph_state.get("partial_execution", False)),
            "failed_node": graph_state.get("failed_node"),
            "error_category": graph_state.get("error_category"),
            "workflow_duration_ms": round(elapsed_s * 1000.0, 2),
            "retrieval_duration_ms": graph_state.get("retrieval_duration_ms", 0.0),
            "chunks_retrieved_count": chunks_retrieved,
            "is_cached": bool(graph_state.get("is_cached", False)),
            "cache_hit_type": graph_state.get("cache_hit_type"),
        }

        response_payload = {
            "success": graph_state.get("status") != "failed",
            "status": graph_state.get("status", "completed"),
            "correlation_id": cid,
            "problem": problem,
            "debate_winner": best_agent,
            "final_solution": best_solution,
            "confidence": judge_out.get("confidence", 0.85),
            "score": judge_out.get("score", 0.95),
            "evaluation_metrics": judge_out.get("metrics", {}),
            "total_time": round(elapsed_s, 2),
            "is_cached": bool(graph_state.get("is_cached", False)),
            "cache_hit_type": graph_state.get("cache_hit_type"),
            "latency_saved_ms": graph_state.get("latency_saved_ms"),
            "planner": graph_state.get("planner_output", {}),
            "managed_context": graph_state.get("managed_context", {}),
            "solver_outputs": graph_state.get("solver_outputs", {}),
            "reflection": graph_state.get("reflection_output", {}),
            "judge": judge_out,
            "citations": graph_state.get("citations", []),
            "debate_history": graph_state.get("debate_history", []),
            "provider_metrics": router.get_metrics_summary(),
            "telemetry": telemetry,
        }

        return jsonify(response_payload), 200

    except Exception as error:
        current_app.logger.exception("LangGraph debate workflow failed unexpectedly")
        return jsonify({"success": False, "error": str(error)}), 500


@graph_debate_blueprint.route("/cache/stats", methods=["GET"])
@require_auth()
def get_cache_stats():
    """Returns semantic cache operational stats, hit rates, and latency savings."""
    graph = _graph()
    if graph.cache_service is not None:
        stats = graph.cache_service.get_stats()
        return jsonify({"success": True, "stats": stats}), 200
    return jsonify({"success": False, "error": "Semantic cache service is not active."}), 200


@graph_debate_blueprint.route("/cache/clear", methods=["POST"])
@require_auth(roles=["admin"])
def clear_cache():
    """Clears all records from the persistent semantic cache."""
    graph = _graph()
    if graph.cache_service is not None:
        cleared_count = graph.cache_service.clear()
        return jsonify({"success": True, "cleared_count": cleared_count}), 200
    return jsonify({"success": False, "error": "Semantic cache service is not active."}), 200
