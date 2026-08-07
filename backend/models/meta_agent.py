# TODO(Draft 2): Retain this prototype orchestrator until the graph workflow is introduced.
# backend/models/meta_agent.py
"""
Meta Agent - Orchestrates the multi-agent math problem solving system
UPDATED (2025-11-05):
- Aligned with new APIClient (GROQ → Local LLM → OpenAI → Cohere → HF)
- Graceful RAG fallback (continue app even if vector store/retriever fail)
- Lean logging (INFO = milestones, DEBUG = detail)
"""
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import traceback
import sys
import os
from dotenv import load_dotenv

# NEW: evaluator
from .evaluator import Evaluator  # <- add this

# Load environment variables
load_dotenv()

# Ensure the project root is in the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.math_solver import MathSolverAgent
from agents.judge_agent import JudgeAgent
from agents.retriever_agent import RetrieverAgent
from rag.vector_store import MathProblemVectorStore
from utils.data_processor import DataProcessor
from utils.api_client import APIClient
from config import SYSTEM_CONFIG

logger = logging.getLogger(__name__)
VERBOSE_DEBUG = SYSTEM_CONFIG.get("DEBUG_MODE", True)  # Use DEBUG logs only if DEBUG_MODE=True


class MetaAgent:
    """Meta-agent that coordinates multiple specialized agents"""

    def __init__(self):
        """Initialize the Meta Agent orchestrator."""
        logger.info("MetaAgent: init")
        self.agent_id = "meta_agent"
        self.role = "System Orchestrator"

        # Core services
        self.vector_store: Optional[MathProblemVectorStore] = None
        self.data_processor: Optional[DataProcessor] = None
        self.api_client: Optional[APIClient] = None

        # Agents
        self.math_solvers: List[MathSolverAgent] = []
        self.judge_agent: Optional[JudgeAgent] = None
        self.retriever_agent: Optional[RetrieverAgent] = None

        # Stats
        self.total_problems_solved = 0
        self.successful_solutions = 0
        self.debate_sessions = 0

        # Config
        self.debate_rounds = SYSTEM_CONFIG.get("debate_rounds", 3)
        self.top_k_retrieval = SYSTEM_CONFIG.get("top_k_retrieval", 5)

        if VERBOSE_DEBUG:
            logger.debug(f"MetaAgent config: rounds={self.debate_rounds}, top_k={self.top_k_retrieval}")

    def initialize(self) -> bool:
        """Initialize all agents and components required by the MetaAgent."""
        try:
            logger.info("MetaAgent: initialize → start")

            # 1) Data Processor (non-critical)
            try:
                self.data_processor = DataProcessor()
                self.data_processor.load_sample_data()
                logger.info("DataProcessor: ready")
            except Exception as e:
                logger.warning(f"DataProcessor init failed: {e}", exc_info=VERBOSE_DEBUG)

            # 2) API Client (critical)
            try:
                self.api_client = APIClient()
                if not self.api_client or not self.api_client.is_configured():
                    logger.error("APIClient not configured (no usable providers).")
                logger.info("APIClient: ready")
            except Exception as e:
                logger.error(f"APIClient init failed: {e}", exc_info=VERBOSE_DEBUG)
                return False

            # 3) Vector Store (RAG)
            try:
                self.vector_store = MathProblemVectorStore()
                vector_db_path = SYSTEM_CONFIG.get("vector_db_path", "./database/vector_store.db")
                if self.vector_store.load(vector_db_path):
                    if VERBOSE_DEBUG:
                        stats = self.vector_store.get_stats()
                        logger.debug(f"VectorStore loaded: {stats}")
                    logger.info("VectorStore: loaded")
                else:
                    logger.info("VectorStore: not found (continuing without RAG)")
            except Exception as e:
                logger.info(f"VectorStore init failed (continuing without RAG): {e}", exc_info=VERBOSE_DEBUG)
                self.vector_store = None

            # 4) Retriever Agent (non-critical)
            try:
                self.retriever_agent = RetrieverAgent(vector_store=self.vector_store)
                if self.retriever_agent.initialize():
                    logger.info("RetrieverAgent: ready (RAG enabled)")
                else:
                    logger.info("RetrieverAgent: returned False (RAG disabled)")
                    self.retriever_agent = None
            except Exception as e:
                logger.info(f"RetrieverAgent init failed (RAG disabled): {e}", exc_info=VERBOSE_DEBUG)
                self.retriever_agent = None

            # 5) Math Solver Agents
            solver_ids = ["solver_1", "solver_2", "solver_3"]
            for sid in solver_ids:
                try:
                    solver = MathSolverAgent(agent_id=sid, role=None)
                    if solver.initialize():
                        self.math_solvers.append(solver)
                        if VERBOSE_DEBUG:
                            logger.debug(f"{sid}: initialized as '{solver.role}'")
                    else:
                        logger.warning(f"{sid}: initialize() returned False")
                except Exception as e:
                    logger.warning(f"{sid}: creation/init failed: {e}", exc_info=VERBOSE_DEBUG)

            if not self.math_solvers:
                logger.error("No math solver agents initialized. Cannot proceed.")
                return False

            # 6) Judge Agent
            try:
                self.judge_agent = JudgeAgent(agent_id="judge", role=None)
                if self.judge_agent.initialize():
                    logger.info("JudgeAgent: ready")
                else:
                    logger.info("JudgeAgent: initialize() returned False")
                    self.judge_agent = None
            except Exception as e:
                logger.info(f"JudgeAgent init failed: {e}", exc_info=VERBOSE_DEBUG)
                self.judge_agent = None

            rag_enabled = (
                self.vector_store is not None
                and self.retriever_agent is not None
                and hasattr(self.vector_store, "vectors")
                and len(self.vector_store.vectors) > 0
            )
            logger.info(
                f"MetaAgent: initialized ✓ | solvers={len(self.math_solvers)} | judge={'yes' if self.judge_agent else 'no'} | RAG={'on' if rag_enabled else 'off'}"
            )
            return True

        except Exception as e:
            logger.error(f"MetaAgent.initialize: fatal: {e}", exc_info=True)
            return False

    def _populate_vector_store(self):
        # ... (unchanged)
        try:
            if not self.data_processor:
                logger.info("populate_vector_store: DataProcessor missing; skip")
                return
            if not self.vector_store:
                logger.info("populate_vector_store: VectorStore missing; skip")
                return

            sample_problems = self.data_processor.get_sample_problems()
            if not sample_problems:
                logger.info("populate_vector_store: no sample problems; skip")
                return

            texts = [p.get("problem", "") for p in sample_problems if p.get("problem")]
            logger.info(f"populate_vector_store: embedding {len(texts)} problems")

            if hasattr(self.api_client, "get_embeddings_batch"):
                embeddings = self.api_client.get_embeddings_batch(texts)  # type: ignore[attr-defined]
            else:
                embeddings = []
                for i, t in enumerate(texts):
                    if VERBOSE_DEBUG and i % 10 == 0:
                        logger.debug(f"populate_vector_store: progress {i}/{len(texts)}")
                    emb = self.api_client.get_embeddings(t)
                    embeddings.append(emb if emb else [])

            if embeddings and len(embeddings) == len(sample_problems):
                self.vector_store.add_math_problems(sample_problems, embeddings)
                self.vector_store.save()
                logger.info(f"populate_vector_store: done ({len(sample_problems)} items)")
            else:
                logger.warning(
                    f"populate_vector_store: embeddings mismatch {len(embeddings)}/{len(sample_problems)}"
                )
        except Exception as e:
            logger.warning(f"populate_vector_store: failed: {e}", exc_info=VERBOSE_DEBUG)

    def solve_problem(self, problem: str, use_rag: bool = True) -> Dict[str, Any]:
        # ... (unchanged)
        self.total_problems_solved += 1
        start_time = datetime.now()
        pid = self.total_problems_solved

        if not problem or not problem.strip():
            return {
                "success": False,
                "error": "Empty problem provided",
                "answer": "No problem to solve",
                "confidence": 0.0,
                "problem": problem,
            }

        logger.info(f"solve[{pid}]: received | use_rag={use_rag}")

        try:
            if not self.api_client:
                return {
                    "success": False,
                    "error": "API Client not initialized",
                    "answer": "System initialization error",
                    "confidence": 0.0,
                }

            if not self.math_solvers:
                return {
                    "success": False,
                    "error": "No solver agents available",
                    "answer": "No solvers available",
                    "confidence": 0.0,
                }

            rag_context: List[Dict[str, Any]] = []
            rag_used_flag = False
            if use_rag and self.retriever_agent:
                try:
                    rag_context = self.retriever_agent.retrieve_similar_problems(
                        problem, top_k=self.top_k_retrieval
                    )
                    rag_used_flag = len(rag_context) > 0
                    if VERBOSE_DEBUG:
                        logger.debug(f"solve[{pid}]: RAG items={len(rag_context)}")
                except Exception as e:
                    if VERBOSE_DEBUG:
                        logger.debug(f"solve[{pid}]: RAG retrieval failed: {e}")
                    rag_context = []
                    rag_used_flag = False

            solver = self.math_solvers[0]
            if VERBOSE_DEBUG:
                logger.debug(f"solve[{pid}]: using {solver.agent_id}")

            result = solver.solve_problem(problem, context=rag_context)

            if not isinstance(result, dict):
                return {
                    "success": False,
                    "error": "Solver returned invalid response type",
                    "answer": "Solver error",
                    "confidence": 0.0,
                }

            if not result.get("success", False):
                return {
                    "success": False,
                    "error": f"Math solver failed: {result.get('error', 'Unknown')}",
                    "answer": "Solver failed to generate solution",
                    "confidence": 0.0,
                }

            total_time = (datetime.now() - start_time).total_seconds()
            out = {
                "success": True,
                "problem": problem,
                "answer": result.get("answer", "No answer provided"),
                "solution": result.get("solution", result.get("answer", "No solution provided")),
                "confidence": result.get("confidence", 0.0),
                "solver_used": result.get("agent_id", solver.agent_id),
                "solving_style": result.get("solving_style", getattr(solver, "solving_style", "unknown")),
                "api_used": result.get("api_used", "unknown"),
                "rag_enabled": use_rag and rag_used_flag,
                "rag_context_used": result.get("rag_context_used", len(rag_context)),
                "has_rag_context": result.get("has_rag_context", len(rag_context) > 0),
                "total_time": round(total_time, 2),
            }

            self.successful_solutions += 1
            logger.info(
                f"solve[{pid}]: ok | api={out['api_used']} | rag={'on' if out['rag_enabled'] else 'off'} | t={out['total_time']}s"
            )
            return out

        except Exception as e:
            logger.error(f"solve[{pid}]: exception: {e}", exc_info=VERBOSE_DEBUG)
            return {
                "success": False,
                "error": str(e),
                "answer": f"Exception: {str(e)}",
                "confidence": 0.0,
                "problem": problem,
                "traceback": traceback.format_exc() if VERBOSE_DEBUG else "",
            }

    def run_debate(self, problem: str, rounds: Optional[int] = None, ground_truth: Optional[str] = None) -> Dict[str, Any]:
        """
        Orchestrates multi-agent math debate via the LangGraph workflow engine.
        """
        self.debate_sessions += 1
        session_id = self.debate_sessions
        start_time = datetime.now()

        if not problem or not problem.strip():
            return {
                "success": False,
                "error": "Empty problem provided",
                "debate_winner": "Error",
                "final_solution": "No problem provided",
            }

        try:
            from graph.workflow import MathDebateGraph
            graph = MathDebateGraph()
            graph_state = graph.execute(problem)

            judge_out = graph_state.get("judge_output", {})
            winner = judge_out.get("best_agent", "Solver_1")
            final_solution = graph_state.get("final_answer") or judge_out.get("best_solution", "")
            elapsed = (datetime.now() - start_time).total_seconds()

            return {
                "success": True,
                "problem": problem,
                "debate_winner": winner,
                "final_solution": final_solution,
                "confidence": judge_out.get("confidence", 0.85),
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
        # ... (unchanged)
        try:
            success_rate = (
                (self.successful_solutions / self.total_problems_solved * 100)
                if self.total_problems_solved > 0
                else 0
            )
            agent_stats: Dict[str, Any] = {}
            for agent in (self.math_solvers or []):
                if hasattr(agent, "get_stats"):
                    agent_stats[agent.agent_id] = agent.get_stats()
            if self.judge_agent and hasattr(self.judge_agent, "get_stats"):
                agent_stats["judge"] = self.judge_agent.get_stats()
            if self.retriever_agent and hasattr(self.retriever_agent, "get_stats"):
                agent_stats["retriever"] = self.retriever_agent.get_stats()

            rag_enabled = (
                self.vector_store is not None
                and hasattr(self.vector_store, "vectors")
                and len(self.vector_store.vectors) > 0
            )

            return {
                "meta_agent_id": self.agent_id,
                "role": self.role,
                "total_problems_solved": self.total_problems_solved,
                "successful_solutions": self.successful_solutions,
                "failed_solutions": self.total_problems_solved - self.successful_solutions,
                "success_rate": round(success_rate, 2),
                "debate_sessions": self.debate_sessions,
                "solver_count": len(self.math_solvers),
                "api_configured": self.api_client.is_configured() if self.api_client else False,
                "rag_enabled": rag_enabled,
                "vector_store_stats": self.vector_store.get_stats() if self.vector_store else {},
                "agent_stats": agent_stats,
                "config": {
                    "debate_rounds": self.debate_rounds,
                    "top_k_retrieval": self.top_k_retrieval,
                },
            }
        except Exception as e:
            logger.error(f"get_stats failed: {e}", exc_info=VERBOSE_DEBUG)
            return {"error": "Failed to retrieve stats", "details": str(e)}

    def get_agent_info(self) -> Dict[str, Any]:
        # ... (unchanged)
        info: Dict[str, Any] = {}
        for solver in self.math_solvers:
            if hasattr(solver, "get_agent_info"):
                info[solver.agent_id] = solver.get_agent_info()
        if self.judge_agent and hasattr(self.judge_agent, "get_agent_info"):
            info["judge"] = self.judge_agent.get_agent_info()
        if self.retriever_agent and hasattr(self.retriever_agent, "get_agent_info"):
            info["retriever"] = self.retriever_agent.get_agent_info()

        return {
            "meta_agent": {
                "agent_id": self.agent_id,
                "role": self.role,
                "total_agents": len(self.math_solvers) + (1 if self.judge_agent else 0) + (1 if self.retriever_agent else 0),
            },
            "agents": info,
        }
