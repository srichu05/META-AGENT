"""LangGraph workflow orchestrator for Meta-Agent Math Debate System."""

import logging
import time
from typing import Any, Dict, List, Optional

from utils.observability import get_correlation_id

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

    def __init__(self, cache_service=None):
        self._compiled_graph = None
        self.cache_service = cache_service
        if self.cache_service is None:
            try:
                from cache.service import SemanticCacheService
                self.cache_service = SemanticCacheService()
            except Exception as error:
                logger.warning(f"SemanticCacheService initialization skipped ({error}).")
                self.cache_service = None

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

    def execute(
        self,
        query: str,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> DebateGraphState:
        """
        Executes the math debate graph workflow over a user query.
        Returns the final populated DebateGraphState with execution telemetry.
        """
        start_time = time.time()
        cid = correlation_id or get_correlation_id()

        # 1. Tier 1 & 2: Check Semantic Cache before executing DAG (user-scoped)
        if self.cache_service and self.cache_service.is_enabled():
            try:
                cached_result = self.cache_service.get(query, user_id=user_id)
                if cached_result is not None and cached_result.hit:
                    cached_state = cached_result.to_graph_state(current_query=query)
                    total_time = time.time() - start_time
                    cached_state["correlation_id"] = cid
                    cached_state["user_id"] = user_id
                    cached_state["status"] = "completed"
                    cached_state["workflow_duration_ms"] = round(total_time * 1000.0, 2)
                    logger.info(
                        f"[{cid}] ⚡ [Cache Hit: {cached_result.hit_type.upper()}] Returning cached debate for query: "
                        f"'{query[:50]}...' in {total_time * 1000.0:.2f}ms"
                    )
                    return cached_state
            except Exception as cache_err:
                logger.warning(f"[{cid}] Semantic cache lookup bypassed due to error: {cache_err}")

        state = create_initial_state(query, correlation_id=cid, user_id=user_id)

        logger.info(f"[{cid}] 🚀 Starting MathDebateGraph execution for query: '{query[:80]}...'")

        if HAS_LANGGRAPH and self._compiled_graph is not None:
            try:
                final_state = self._compiled_graph.invoke(state)
                final_state["execution_mode"] = "langgraph"
                final_state.setdefault("partial_execution", False)
                final_state.setdefault("failed_node", None)
                final_state.setdefault("error_category", None)
                final_state["status"] = "completed" if not final_state.get("partial_execution") else "partial"
                total_time = time.time() - start_time
                final_state["workflow_duration_ms"] = round(total_time * 1000.0, 2)
                logger.info(f"[{cid}] ✅ LangGraph StateGraph completed in {total_time:.2f}s.")

                # Store in semantic cache if eligible
                if self.cache_service and self.cache_service.is_enabled() and final_state["status"] == "completed":
                    try:
                        self.cache_service.set(
                            query=query,
                            state=final_state,
                            execution_time_ms=total_time * 1000.0,
                            user_id=user_id,
                        )
                    except Exception as cache_err:
                        logger.warning(f"[{cid}] Semantic cache store bypassed due to error: {cache_err}")

                return final_state
            except Exception as error:
                logger.warning(f"[{cid}] LangGraph execution exception ({error}). Falling back to state DAG executor.")
                state["error"] = f"LangGraph failure: {error}"

        # Stateful DAG fallback execution
        state["execution_mode"] = "builtin_dag"
        state["partial_execution"] = False
        state["failed_node"] = None
        state["error_category"] = None

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

        retrieval_duration_ms = 0.0
        for node_name, node_fn in nodes:
            node_start = time.time()
            try:
                state = node_fn(state)
                node_dur = (time.time() - node_start) * 1000.0
                if node_name.lower() == "retrieval":
                    retrieval_duration_ms = node_dur
                    state["retrieval_duration_ms"] = round(node_dur, 2)
            except Exception as node_err:
                logger.error(f"[{cid}] ❌ Error in graph node {node_name}: {node_err}", exc_info=True)
                state["partial_execution"] = True
                state["failed_node"] = node_name
                state["error"] = f"Error in node {node_name}: {str(node_err)}"

                # Standardize error category
                err_msg = str(node_err).lower()
                if "timeout" in err_msg or "timed out" in err_msg or isinstance(node_err, TimeoutError):
                    state["error_category"] = "timeout"
                elif any(k in err_msg for k in ["429", "rate limit", "quota", "provider", "api_key"]):
                    state["error_category"] = "provider_error"
                elif "validation" in err_msg:
                    state["error_category"] = "validation_error"
                else:
                    state["error_category"] = "internal_error"

                if node_name in ["Planner", "Retrieval", "ContextManager"] or "timeout" in err_msg:
                    logger.warning(f"[{cid}] Halting downstream graph execution due to failure in {node_name}.")
                    break

        total_time = time.time() - start_time
        state["workflow_duration_ms"] = round(total_time * 1000.0, 2)

        # Determine overall execution status
        if state.get("partial_execution") or state.get("failed_node"):
            solvers = state.get("solver_outputs") or {}
            has_solutions = any(s.get("answer") for s in solvers.values() if isinstance(s, dict))
            state["status"] = "partial" if has_solutions else "failed"
        else:
            state["status"] = "completed"

        logger.info(
            f"[{cid}] ✅ Graph DAG execution finished in {total_time:.2f}s with status '{state['status']}'."
        )

        # Store in semantic cache if fully eligible and completed
        if (
            self.cache_service
            and self.cache_service.is_enabled()
            and state.get("status") == "completed"
            and not state.get("partial_execution")
        ):
            try:
                self.cache_service.set(
                    query=query,
                    state=state,
                    execution_time_ms=total_time * 1000.0,
                    user_id=user_id,
                )
            except Exception as cache_err:
                logger.warning(f"[{cid}] Semantic cache store bypassed due to error: {cache_err}")

        return state
