"""Shared graph state representation for LangGraph orchestration."""

from typing import Any, Dict, List, Optional, TypedDict


class DebateGraphState(TypedDict, total=False):
    """Shared state object passed through all nodes in the math debate graph."""

    query: str
    planner_output: Dict[str, Any]
    retrieved_context: Dict[str, Any]
    managed_context: Dict[str, Any]
    solver_outputs: Dict[str, Dict[str, Any]]
    reflection_output: Dict[str, Any]
    judge_output: Dict[str, Any]
    citations: List[Dict[str, Any]]
    final_answer: str
    debate_history: List[Dict[str, Any]]
    current_node: str
    error: Optional[str]
    execution_mode: str
    partial_execution: bool
    failed_node: Optional[str]
    correlation_id: Optional[str]
    user_id: Optional[str]
    status: str
    error_category: Optional[str]
    retrieval_duration_ms: float
    workflow_duration_ms: float


def create_initial_state(query: str, correlation_id: Optional[str] = None, user_id: Optional[str] = None) -> DebateGraphState:
    """Helper function to create a clean initial state for a user query."""
    return {
        "query": (query or "").strip(),
        "planner_output": {},
        "retrieved_context": {},
        "managed_context": {},
        "solver_outputs": {},
        "reflection_output": {},
        "judge_output": {},
        "citations": [],
        "final_answer": "",
        "debate_history": [],
        "current_node": "START",
        "error": None,
        "execution_mode": "uninitialized",
        "partial_execution": False,
        "failed_node": None,
        "correlation_id": correlation_id,
        "user_id": user_id,
        "status": "in_progress",
        "error_category": None,
        "retrieval_duration_ms": 0.0,
        "workflow_duration_ms": 0.0,
    }
