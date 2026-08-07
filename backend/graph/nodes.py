"""Graph node functions for LangGraph math debate orchestration."""

import datetime
import logging
from typing import Any, Dict, List, Optional

from agents.judge_agent import JudgeAgent
from agents.math_solver import MathSolverAgent
from agents.planner_agent import PlannerAgent
from agents.reflection_agent import ReflectionAgent
from graph.state import DebateGraphState
from retrieval.service import RetrievalService
from services.context_manager import ContextManager

logger = logging.getLogger(__name__)


def _log_node_execution(state: DebateGraphState, node_name: str, details: Dict[str, Any]) -> None:
    """Appends execution timestamp and details to graph debate history."""
    if "debate_history" not in state or state["debate_history"] is None:
        state["debate_history"] = []

    state["current_node"] = node_name
    record = {
        "node": node_name,
        "timestamp": datetime.datetime.now().isoformat(),
        "details": details,
    }
    state["debate_history"].append(record)
    logger.info(f"📍 [Graph Node: {node_name}] Executed successfully.")


# Singleton / cached component instances
_planner = PlannerAgent()
_retrieval_service = RetrievalService()
_context_manager = ContextManager()
_reflection_agent = ReflectionAgent()
_judge_agent = JudgeAgent()

_solvers = [
    MathSolverAgent("solver_1", "Analytical Math Solver"),
    MathSolverAgent("solver_2", "Creative Problem Solver"),
    MathSolverAgent("solver_3", "Verification Agent"),
]


def planner_node(state: DebateGraphState) -> DebateGraphState:
    """Node 1: Planner Agent - Analyzes query and produces execution strategy."""
    query = state.get("query", "")
    planner_output = _planner.plan(query)
    out_dict = planner_output.to_dict()

    state["planner_output"] = out_dict
    _log_node_execution(state, "Planner", {
        "topic": out_dict.get("topic"),
        "difficulty": out_dict.get("difficulty"),
        "needs_retrieval": out_dict.get("needs_retrieval"),
        "retrieval_depth": out_dict.get("retrieval_depth"),
        "strategy": out_dict.get("execution_strategy"),
    })
    return state


def retrieval_node(state: DebateGraphState) -> DebateGraphState:
    """Node 2: Retrieval Engine - Executes Session 3 RAG search if recommended by Planner."""
    query = state.get("query", "")
    planner_output = state.get("planner_output", {})

    needs_retrieval = planner_output.get("needs_retrieval", True)
    top_k = planner_output.get("retrieval_depth", 5)

    if not needs_retrieval or top_k <= 0:
        logger.info("Retrieval node skipped per planner decision.")
        state["retrieved_context"] = {
            "query": query,
            "formatted_context": "No retrieval requested by Planner.",
            "chunks": [],
            "citations": [],
            "total_chunks_retrieved": 0,
        }
        _log_node_execution(state, "Retrieval", {"retrieval_skipped": True})
        return state

    retrieved_obj = _retrieval_service.retrieve(query, top_k=top_k)
    ret_dict = retrieved_obj.to_dict()

    state["retrieved_context"] = ret_dict
    _log_node_execution(state, "Retrieval", {
        "total_retrieved": ret_dict.get("total_chunks_retrieved", 0),
        "hybrid_used": ret_dict.get("hybrid_used", False),
        "retrieval_time_ms": ret_dict.get("retrieval_time_ms", 0.0),
    })
    return state


def context_manager_node(state: DebateGraphState) -> DebateGraphState:
    """Node 3: Context Manager - Deduplicates, organizes, and formats prompt-ready context."""
    raw_retrieved = state.get("retrieved_context", {})
    query = state.get("query", "")

    # Re-wrap or extract chunks
    from retrieval.types import RetrievedChunk, RetrievedContext
    chunks_data = raw_retrieved.get("chunks", [])

    chunks = [
        RetrievedChunk(
            chunk_id=c.get("chunk_id", ""),
            document_id=c.get("document_id", ""),
            filename=c.get("filename", ""),
            file_type=c.get("file_type", ""),
            page_number=c.get("page_number"),
            section_heading=c.get("section_heading"),
            char_start=c.get("char_start", 0),
            char_end=c.get("char_end", 0),
            vector_index=c.get("vector_index", 0),
            content=c.get("content", ""),
            score=c.get("score", 0.0),
            retrieval_source=c.get("retrieval_source", "faiss"),
        )
        for c in chunks_data
    ]

    context_obj = RetrievedContext(
        query=query,
        formatted_context=raw_retrieved.get("formatted_context", ""),
        chunks=chunks,
    )

    managed_dict = _context_manager.process_context(context_obj, query=query)
    state["managed_context"] = managed_dict

    _log_node_execution(state, "ContextManager", {
        "accepted_chunks": managed_dict.get("total_chunks_processed", 0),
        "deduplicated": managed_dict.get("deduplicated_count", 0),
        "character_count": managed_dict.get("character_count", 0),
    })
    return state


def solver_1_node(state: DebateGraphState) -> DebateGraphState:
    """Node 4: Solver Agent 1 (Analytical Math Solver)."""
    return _run_solver_node(state, _solvers[0], "Solver_1")


def solver_2_node(state: DebateGraphState) -> DebateGraphState:
    """Node 5: Solver Agent 2 (Creative Problem Solver)."""
    return _run_solver_node(state, _solvers[1], "Solver_2")


def solver_3_node(state: DebateGraphState) -> DebateGraphState:
    """Node 6: Solver Agent 3 (Verification Agent)."""
    return _run_solver_node(state, _solvers[2], "Solver_3")


def _run_solver_node(state: DebateGraphState, solver: MathSolverAgent, solver_name: str) -> DebateGraphState:
    query = state.get("query", "")
    managed_context = state.get("managed_context", {})
    context_str = managed_context.get("formatted_context", "")

    if "solver_outputs" not in state or state["solver_outputs"] is None:
        state["solver_outputs"] = {}

    if not solver.api_client:
        solver.initialize()

    result = solver.solve_problem(query, context=context_str)
    state["solver_outputs"][solver.agent_id] = result

    _log_node_execution(state, solver_name, {
        "solver_id": solver.agent_id,
        "answer": result.get("answer", ""),
        "confidence": result.get("confidence", 0.0),
    })
    return state


def reflection_node(state: DebateGraphState) -> DebateGraphState:
    """Node 7: Reflection Agent - Audit solver outputs for contradictions and math errors."""
    query = state.get("query", "")
    solver_outputs = state.get("solver_outputs", {})

    if not _reflection_agent.api_client:
        from utils.api_client import APIClient
        _reflection_agent.api_client = APIClient()

    reflection_output = _reflection_agent.reflect(query, solver_outputs)
    ref_dict = reflection_output.to_dict()

    state["reflection_output"] = ref_dict
    _log_node_execution(state, "Reflection", {
        "contradictions_found": ref_dict.get("contradictions_found", False),
        "hallucination_detected": ref_dict.get("hallucination_detected", False),
        "summary": ref_dict.get("summary", ""),
    })
    return state


def judge_node(state: DebateGraphState) -> DebateGraphState:
    """Node 8: Judge Agent Upgrade - Evaluate correctness, reasoning logic & reflection notes."""
    query = state.get("query", "")
    solver_outputs = state.get("solver_outputs", {})
    reflection_output = state.get("reflection_output", {})

    if not _judge_agent.api_client:
        _judge_agent.initialize()

    judge_result = _judge_agent.evaluate_solutions(
        problem=query,
        solutions=solver_outputs,
        reflection_output=reflection_output,
    )

    state["judge_output"] = judge_result
    state["final_answer"] = judge_result.get("best_solution", "")

    _log_node_execution(state, "Judge", {
        "best_agent": judge_result.get("best_agent"),
        "confidence": judge_result.get("confidence", 0.0),
        "score": judge_result.get("score", 0.0),
        "evaluation_reasoning": judge_result.get("evaluation_reasoning"),
    })
    return state


def citation_generator_node(state: DebateGraphState) -> DebateGraphState:
    """Node 9: Citation Generator - Maps final response to retrieved document citations."""
    managed_context = state.get("managed_context", {})
    citations = managed_context.get("citations", [])

    state["citations"] = citations
    _log_node_execution(state, "CitationGenerator", {
        "total_citations": len(citations),
        "citation_labels": [c.get("citation_id") for c in citations[:5]],
    })
    return state
