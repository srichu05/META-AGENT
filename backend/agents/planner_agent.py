"""Planner Agent - Analyzes math queries to produce execution strategies without solving them."""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from utils.api_client import APIClient
from config import PROBLEM_TYPES, SYSTEM_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class PlannerOutput:
    """Structured planning output produced by the Planner Agent."""

    query: str
    topic: str
    difficulty: str
    needs_retrieval: bool
    retrieval_depth: int
    execution_strategy: List[str] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "needs_retrieval": self.needs_retrieval,
            "retrieval_depth": self.retrieval_depth,
            "execution_strategy": self.execution_strategy,
            "reasoning": self.reasoning,
        }


class PlannerAgent:
    """Classifies math queries and produces structured planning strategy before retrieval/reasoning."""

    def __init__(self, agent_id: str = "planner", api_client: Optional[APIClient] = None):
        self.agent_id = agent_id
        self.api_client = api_client
        self.supported_topics = PROBLEM_TYPES

    def plan(self, query: str) -> PlannerOutput:
        """
        Analyze the math query and construct a PlannerOutput.
        Does NOT attempt to solve the math problem.
        """
        if not query or not query.strip():
            return PlannerOutput(
                query="",
                topic="unknown",
                difficulty="medium",
                needs_retrieval=False,
                retrieval_depth=3,
                execution_strategy=["Provide direct mathematical clarification."],
                reasoning="Empty query provided.",
            )

        logger.info(f"🧠 PlannerAgent analyzing query: '{query[:80]}...'")

        # Fallback heuristic analysis first
        topic = self._detect_topic(query)
        difficulty = self._detect_difficulty(query)
        needs_retrieval = self._decide_retrieval(query, topic, difficulty)
        retrieval_depth = self._decide_depth(difficulty, needs_retrieval)

        # Attempt LLM refinement if APIClient is available
        if self.api_client and self.api_client.is_configured():
            try:
                llm_plan = self._llm_plan(query)
                if llm_plan:
                    return llm_plan
            except Exception as error:
                logger.warning(f"LLM planning failed ({error}). Using heuristic planner output.")

        strategy = [
            f"Identify core {topic} definitions and equations.",
            f"Apply step-by-step reasoning suited for {difficulty} difficulty.",
            "Verify edge cases and dimensional consistency.",
        ]

        return PlannerOutput(
            query=query,
            topic=topic,
            difficulty=difficulty,
            needs_retrieval=needs_retrieval,
            retrieval_depth=retrieval_depth,
            execution_strategy=strategy,
            reasoning=f"Heuristic planning classified as {topic} ({difficulty} difficulty). Retrieval needed: {needs_retrieval}.",
        )

    def _detect_topic(self, query: str) -> str:
        q_lower = query.lower()
        if any(w in q_lower for w in ["integrate", "derivative", "dy/dx", "limit", "calculus", "integral"]):
            return "calculus"
        if any(w in q_lower for w in ["triangle", "angle", "circle", "area", "volume", "perimeter", "geometry", "hypotenuse"]):
            return "geometry"
        if any(w in q_lower for w in ["solve for x", "equation", "quadratic", "polynomial", "algebra", "x +", "x -"]):
            return "algebra"
        if any(w in q_lower for w in ["probability", "chance", "dice", "coins", "permutation", "combination"]):
            return "probability"
        if any(w in q_lower for w in ["percent", "%", "discount", "interest"]):
            return "percentage"
        if any(w in q_lower for w in ["fraction", "numerator", "denominator"]):
            return "fractions"
        if any(w in q_lower for w in ["speed", "distance", "time", "km/h", "mph", "train"]):
            return "time_distance"
        if any(w in q_lower for w in ["cost", "price", "$", "dollars", "cents", "money"]):
            return "money"
        if len(q_lower.split()) > 12 or any(w in q_lower for w in ["john", "mary", "apples", "has", "buys"]):
            return "word_problem"
        return "arithmetic"

    def _detect_difficulty(self, query: str) -> str:
        q_lower = query.lower()
        if len(query) > 200 or any(w in q_lower for w in ["prove", "system of equations", "calculus", "matrix"]):
            return "hard"
        if len(query) > 80 or any(w in q_lower for w in ["solve", "calculate", "find", "equation"]):
            return "medium"
        return "easy"

    def _decide_retrieval(self, query: str, topic: str, difficulty: str) -> bool:
        # Heuristic: Complex word problems, formulas, geometry, or hard problems benefit from document RAG
        if difficulty in ["medium", "hard"] or topic in ["word_problem", "geometry", "calculus", "algebra"]:
            return True
        return False

    def _decide_depth(self, difficulty: str, needs_retrieval: bool) -> int:
        if not needs_retrieval:
            return 0
        if difficulty == "hard":
            return 7
        if difficulty == "medium":
            return 5
        return 3

    def _llm_plan(self, query: str) -> Optional[PlannerOutput]:
        prompt = f"""You are an expert Math Planner Agent. Analyze the following math query.
Do NOT solve the math problem. Only plan the execution strategy.

Query: "{query}"

Respond EXACTLY in this format:
TOPIC: [arithmetic/algebra/geometry/word_problem/percentage/fractions/time_distance/money/probability/calculus]
DIFFICULTY: [easy/medium/hard]
NEEDS_RETRIEVAL: [True/False]
RETRIEVAL_DEPTH: [3/5/7]
STRATEGY: [Short sentence 1]; [Short sentence 2]
REASONING: [One short explanation sentence]
"""
        res = self.api_client.call_best_available_api(prompt, max_tokens=256, temperature=0.1)
        if not res.get("success"):
            return None

        text = res.get("response", "")
        topic_m = re.search(r"TOPIC:\s*(\w+)", text, re.I)
        diff_m = re.search(r"DIFFICULTY:\s*(\w+)", text, re.I)
        ret_m = re.search(r"NEEDS_RETRIEVAL:\s*(True|False)", text, re.I)
        depth_m = re.search(r"RETRIEVAL_DEPTH:\s*(\d+)", text, re.I)
        strat_m = re.search(r"STRATEGY:\s*(.*)", text, re.I)
        reas_m = re.search(r"REASONING:\s*(.*)", text, re.I)

        topic = topic_m.group(1).lower() if topic_m else self._detect_topic(query)
        difficulty = diff_m.group(1).lower() if diff_m else self._detect_difficulty(query)
        needs_retrieval = (ret_m.group(1).lower() == "true") if ret_m else True
        depth = int(depth_m.group(1)) if depth_m else 5
        strategy = [s.strip() for s in strat_m.group(1).split(";") if s.strip()] if strat_m else ["Analyze problem.", "Formulate steps."]
        reasoning = reas_m.group(1).strip() if reas_m else "LLM planner evaluation completed."

        return PlannerOutput(
            query=query,
            topic=topic,
            difficulty=difficulty,
            needs_retrieval=needs_retrieval,
            retrieval_depth=depth,
            execution_strategy=strategy,
            reasoning=reasoning,
        )
