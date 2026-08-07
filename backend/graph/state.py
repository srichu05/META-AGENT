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


def create_initial_state(query: str) -> DebateGraphState:
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
    }
