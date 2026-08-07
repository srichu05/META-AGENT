"""LangGraph workflow orchestrator for Meta-Agent Math Debate System."""

import logging
import time
from typing import Any, Dict, List, Optional

from graph.nodes import (
    citation_generator_node,
    context_manager_node,
    judge_node,
    planner_node,
    reflection_node,
    retrieval_node,
    solver_1_node,
    solver_2_node,
    solver_3_node,
)
from graph.state import DebateGraphState, create_initial_state

logger = logging.getLogger(__name__)

# Attempt importing LangGraph StateGraph
try:
    from langgraph.graph import END, StateGraph
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
    logger.info("LangGraph package not installed. Using built-in state graph executor.")


class MathDebateGraph:
    """Orchestrates the 9-node LangGraph debate workflow."""

    def __init__(self):
        self._compiled_graph = None
        if HAS_LANGGRAPH:
            try:
                self._build_langgraph()
            except Exception as error:
                logger.warning(f"Failed to compile LangGraph StateGraph ({error}). Falling back to DAG executor.")

    def _build_langgraph(self):
        builder = StateGraph(DebateGraphState)
        builder.add_node("planner", planner_node)
        builder.add_node("retrieval", retrieval_node)
        builder.add_node("context_manager", context_manager_node)
        builder.add_node("solver_1", solver_1_node)
        builder.add_node("solver_2", solver_2_node)
        builder.add_node("solver_3", solver_3_node)
        builder.add_node("reflection", reflection_node)
        builder.add_node("judge", judge_node)
        builder.add_node("citation_generator", citation_generator_node)

        # Sequential flow
        builder.set_entry_point("planner")
        builder.add_edge("planner", "retrieval")
        builder.add_edge("retrieval", "context_manager")
        builder.add_edge("context_manager", "solver_1")
        builder.add_edge("solver_1", "solver_2")
        builder.add_edge("solver_2", "solver_3")
        builder.add_edge("solver_3", "reflection")
        builder.add_edge("reflection", "judge")
        builder.add_edge("judge", "citation_generator")
        builder.add_edge("citation_generator", END)

        self._compiled_graph = builder.compile()
        logger.info("✅ LangGraph StateGraph compiled successfully.")

    def execute(self, query: str) -> DebateGraphState:
        """
        Executes the math debate graph workflow over a user query.
        Returns the final populated DebateGraphState.
        """
        start_time = time.time()
        state = create_initial_state(query)

        logger.info(f"🚀 Starting MathDebateGraph execution for query: '{query[:80]}...'")

        if HAS_LANGGRAPH and self._compiled_graph is not None:
            try:
                final_state = self._compiled_graph.invoke(state)
                total_time = time.time() - start_time
                logger.info(f"✅ LangGraph StateGraph completed in {total_time:.2f}s.")
                return final_state
            except Exception as error:
                logger.warning(f"LangGraph execution exception ({error}). Falling back to state DAG executor.")

        # Stateful DAG fallback execution
        nodes = [
            ("Planner", planner_node),
            ("Retrieval", retrieval_node),
            ("ContextManager", context_manager_node),
            ("Solver_1", solver_1_node),
            ("Solver_2", solver_2_node),
            ("Solver_3", solver_3_node),
            ("Reflection", reflection_node),
            ("Judge", judge_node),
            ("CitationGenerator", citation_generator_node),
        ]

        for node_name, node_fn in nodes:
            try:
                state = node_fn(state)
            except Exception as node_err:
                logger.error(f"❌ Error in graph node {node_name}: {node_err}", exc_info=True)
                state["error"] = f"Error in node {node_name}: {str(node_err)}"

        total_time = time.time() - start_time
        logger.info(f"✅ Graph DAG execution completed in {total_time:.2f}s.")
        return state
