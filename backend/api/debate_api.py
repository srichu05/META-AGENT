"""REST API blueprint for LangGraph multi-agent math debate execution."""

import time
from flask import Blueprint, current_app, jsonify, request

from graph.workflow import MathDebateGraph

graph_debate_blueprint = Blueprint("graph_debate", __name__, url_prefix="/api/debate")


def _graph() -> MathDebateGraph:
    graph = current_app.extensions.get("math_debate_graph")
    if graph is None:
        graph = MathDebateGraph()
        current_app.extensions["math_debate_graph"] = graph
    return graph


@graph_debate_blueprint.route("/graph", methods=["POST"])
def run_graph_debate():
    """Execute full LangGraph multi-agent debate workflow over a problem query."""
    start_time = time.time()
    data = request.get_json(force=True) or {}
    problem = (data.get("problem") or data.get("query") or "").strip()

    if not problem:
        return jsonify({"success": False, "error": "Problem text is required."}), 400

    try:
        current_app.logger.info(f"🎪 /api/debate/graph request: '{problem[:80]}...'")
        graph_state = _graph().execute(problem)
        elapsed_s = time.time() - start_time

        judge_out = graph_state.get("judge_output", {})
        best_solution = graph_state.get("final_answer") or judge_out.get("best_solution", "")
        best_agent = judge_out.get("best_agent", "Solver_1")

        response_payload = {
            "success": True,
            "problem": problem,
            "debate_winner": best_agent,
            "final_solution": best_solution,
            "confidence": judge_out.get("confidence", 0.85),
            "score": judge_out.get("score", 0.95),
            "evaluation_metrics": judge_out.get("metrics", {}),
            "total_time": round(elapsed_s, 2),
            "planner": graph_state.get("planner_output", {}),
            "managed_context": graph_state.get("managed_context", {}),
            "solver_outputs": graph_state.get("solver_outputs", {}),
            "reflection": graph_state.get("reflection_output", {}),
            "judge": judge_out,
            "citations": graph_state.get("citations", []),
            "debate_history": graph_state.get("debate_history", []),
        }

        return jsonify(response_payload), 200
    except Exception as error:
        current_app.logger.exception("LangGraph debate workflow failed unexpectedly")
        return jsonify({"success": False, "error": str(error)}), 500
