"""
Meta Agent - Backward-Compatible Facade for Draft 2 MathDebateGraph Orchestrator.
Delegates all debate and problem-solving execution to the authoritative MathDebateGraph.
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import traceback
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure the project root is in the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from graph.workflow import MathDebateGraph
from providers.router import ProviderRouter
from config import SYSTEM_CONFIG

logger = logging.getLogger(__name__)
VERBOSE_DEBUG = SYSTEM_CONFIG.get("DEBUG_MODE", True)


class MetaAgent:
    """
    Backward-compatible facade that routes all problem-solving and debate workflows
    authoritatively through the 9-node MathDebateGraph DAG.
    """

    def __init__(self):
        """Initialize the MetaAgent facade."""
        logger.info("MetaAgent: initializing Draft 2 facade")
        self.agent_id = "meta_agent"
        self.role = "System Orchestrator Facade"

        # Active Draft 2 Orchestration & Provider Layer
        self.graph = MathDebateGraph()
        self.router = ProviderRouter()

        # Legacy compatibility attributes
        self.vector_store = None
        self.data_processor = None
        self.api_client = None
        self.math_solvers = []
        self.judge_agent = None
        self.retriever_agent = None

        # Statistics
        self.total_problems_solved = 0
        self.successful_solutions = 0
        self.debate_sessions = 0

        # Configuration
        self.debate_rounds = SYSTEM_CONFIG.get("debate_rounds", 3)
        self.top_k_retrieval = SYSTEM_CONFIG.get("top_k_retrieval", 5)

    def initialize(self) -> bool:
        """Validates provider routing readiness."""
        try:
            logger.info("MetaAgent: initialize → validating ProviderRouter...")
            validation_status = self.router.validate_providers()
            active_providers = [p for p, ok in validation_status.items() if ok]
            logger.info(f"MetaAgent: Draft 2 facade ready | Active providers: {active_providers}")
            return True
        except Exception as error:
            logger.error(f"MetaAgent.initialize: fatal: {error}", exc_info=True)
            return False

    def solve_problem(self, problem: str, use_rag: bool = True) -> Dict[str, Any]:
        """
        Solves a math problem by delegating directly to MathDebateGraph.
        """
        self.total_problems_solved += 1
        pid = self.total_problems_solved
        start_time = datetime.now()

        if not problem or not problem.strip():
            return {
                "success": False,
                "error": "Empty problem provided",
                "answer": "No problem to solve",
                "confidence": 0.0,
                "problem": problem,
            }

        logger.info(f"MetaAgent solve[{pid}]: delegating to MathDebateGraph")

        try:
            graph_state = self.graph.execute(problem)
            judge_out = graph_state.get("judge_output", {})
            final_ans = graph_state.get("final_answer") or judge_out.get("best_solution", "")
            winner = judge_out.get("best_agent", "Solver_1")
            total_time = (datetime.now() - start_time).total_seconds()

            self.successful_solutions += 1

            return {
                "success": True,
                "problem": problem,
                "answer": final_ans,
                "solution": final_ans,
                "confidence": judge_out.get("confidence", 0.9),
                "solver_used": winner,
                "solving_style": "Multi-Agent Debate",
                "api_used": judge_out.get("evaluated_by", "GEMINI"),
                "rag_enabled": use_rag,
                "rag_context_used": len(graph_state.get("retrieved_context", {}).get("chunks", [])),
                "has_rag_context": bool(graph_state.get("retrieved_context", {}).get("chunks")),
                "citations": graph_state.get("citations", []),
                "total_time": round(total_time, 2),
            }
        except Exception as error:
            logger.error(f"MetaAgent solve[{pid}] failed: {error}", exc_info=VERBOSE_DEBUG)
            return {
                "success": False,
                "error": str(error),
                "answer": f"Graph execution error: {str(error)}",
                "confidence": 0.0,
                "problem": problem,
                "traceback": traceback.format_exc() if VERBOSE_DEBUG else "",
            }

    def run_debate(self, problem: str, rounds: Optional[int] = None, ground_truth: Optional[str] = None) -> Dict[str, Any]:
        """
        Orchestrates multi-agent math debate via the authoritative MathDebateGraph engine.
        """
        self.debate_sessions += 1
        start_time = datetime.now()

        if not problem or not problem.strip():
            return {
                "success": False,
                "error": "Empty problem provided",
                "debate_winner": "Error",
                "final_solution": "No problem provided",
            }

        try:
            graph_state = self.graph.execute(problem)

            judge_out = graph_state.get("judge_output", {})
            winner = judge_out.get("best_agent", "Solver_1")
            final_solution = graph_state.get("final_answer") or judge_out.get("best_solution", "")
            elapsed = (datetime.now() - start_time).total_seconds()

            self.successful_solutions += 1

            return {
                "success": True,
                "problem": problem,
                "debate_winner": winner,
                "final_solution": final_solution,
                "confidence": judge_out.get("confidence", 0.9),
                "score": judge_out.get("score", 0.95),
                "evaluation_metrics": judge_out.get("metrics", {}),
                "evaluation_reasoning": judge_out.get("evaluation_reasoning", ""),
                "debate_rounds": rounds or self.debate_rounds,
                "total_time": round(elapsed, 2),
                "planner": graph_state.get("planner_output", {}),
                "managed_context": graph_state.get("managed_context", {}),
                "solver_outputs": graph_state.get("solver_outputs", {}),
                "reflection": graph_state.get("reflection_output", {}),
                "citations": graph_state.get("citations", []),
                "debate_history": graph_state.get("debate_history", []),
            }

        except Exception as error:
            logger.error(f"MetaAgent run_debate graph execution failed: {error}", exc_info=VERBOSE_DEBUG)
            return {
                "success": False,
                "error": str(error),
                "debate_winner": "Error",
                "final_solution": f"Graph execution error: {str(error)}",
                "traceback": traceback.format_exc() if VERBOSE_DEBUG else "",
            }

    def get_stats(self) -> Dict[str, Any]:
        """Returns runtime execution metrics."""
        try:
            success_rate = (
                (self.successful_solutions / self.total_problems_solved * 100)
                if self.total_problems_solved > 0
                else 0
            )
            return {
                "meta_agent_id": self.agent_id,
                "role": self.role,
                "total_problems_solved": self.total_problems_solved,
                "successful_solutions": self.successful_solutions,
                "failed_solutions": self.total_problems_solved - self.successful_solutions,
                "success_rate": round(success_rate, 2),
                "debate_sessions": self.debate_sessions,
                "orchestrator": "MathDebateGraph",
                "provider_metrics": self.router.get_metrics_summary(),
                "config": {
                    "debate_rounds": self.debate_rounds,
                    "top_k_retrieval": self.top_k_retrieval,
                },
            }
        except Exception as e:
            logger.error(f"get_stats failed: {e}", exc_info=VERBOSE_DEBUG)
            return {"error": "Failed to retrieve stats", "details": str(e)}

    def get_agent_info(self) -> Dict[str, Any]:
        """Returns metadata about active debate agents."""
        return {
            "meta_agent": {
                "agent_id": self.agent_id,
                "role": self.role,
                "orchestrator": "MathDebateGraph (9 Nodes)",
            },
            "agents": {
                "planner": {"role": "Query Decomposition & Retrieval Planning"},
                "retrieval": {"role": "FAISS + BM25 + RRF + Cohere Rerank"},
                "context_manager": {"role": "Deduplication & Citation Packaging"},
                "solver_1": {"role": "Analytical Solver", "provider": "GEMINI"},
                "solver_2": {"role": "Fast Solver", "provider": "GROQ"},
                "solver_3": {"role": "Alternative Solver", "provider": "OPENROUTER"},
                "reflection": {"role": "Contradiction & Hallucination Auditor"},
                "judge": {"role": "Multi-Criteria Decision Evaluator"},
                "citation_generator": {"role": "Document Citation Attribution"},
            },
        }
