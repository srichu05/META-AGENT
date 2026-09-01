"""Reflection Agent - Analyzes solver outputs, detects contradictions, logic errors & hallucinations."""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from utils.api_client import APIClient

from prompts.prompts import REFLECTION_SYSTEM_PROMPT
from providers.router import ProviderRouter
from providers.types import ProviderResponse

logger = logging.getLogger(__name__)


@dataclass
class ReflectionOutput:
    """Structured reflection output produced by the Reflection Agent."""

    contradictions_found: bool
    hallucination_detected: bool
    discrepancies: List[str] = field(default_factory=list)
    math_inconsistencies: List[str] = field(default_factory=list)
    suggested_corrections: List[str] = field(default_factory=list)
    solver_agreements: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contradictions_found": self.contradictions_found,
            "hallucination_detected": self.hallucination_detected,
            "discrepancies": self.discrepancies,
            "math_inconsistencies": self.math_inconsistencies,
            "suggested_corrections": self.suggested_corrections,
            "solver_agreements": self.solver_agreements,
            "summary": self.summary,
        }


class ReflectionAgent:
    """Evaluates solver solutions for mathematical consistency, contradictions, and hallucinations."""

    def __init__(self, agent_id: str = "reflection", router: Optional[ProviderRouter] = None):
        self.agent_id = agent_id
        self.router = router or ProviderRouter()

    def reflect(self, problem: str, solver_outputs: Dict[str, Dict[str, Any]]) -> ReflectionOutput:
        """
        Reflect upon multiple solver solutions to identify discrepancies and math errors.
        Does NOT choose a winning solution.
        """
        if not solver_outputs:
            return ReflectionOutput(
                contradictions_found=False,
                hallucination_detected=False,
                summary="No solver solutions available for reflection.",
            )

        logger.info(f"🪞 ReflectionAgent analyzing {len(solver_outputs)} solver outputs...")

        # Rule-based static check first
        answers = {s_id: s_data.get("answer", "").strip().lower() for s_id, s_data in solver_outputs.items()}
        unique_answers = set(ans for ans in answers.values() if ans)
        contradictions = len(unique_answers) > 1

        discrepancies: List[str] = []
        if contradictions:
            discrepancies.append(f"Solvers produced conflicting final answers: {dict(answers)}")

        math_inconsistencies: List[str] = []
        suggested_corrections: List[str] = []

        # Check for obvious ungrounded or empty steps
        for s_id, s_data in solver_outputs.items():
            solution_text = s_data.get("solution", "")
            if not solution_text or len(solution_text) < 10:
                math_inconsistencies.append(f"Agent '{s_id}' provided insufficient reasoning steps.")

        # Attempt LLM reflection via ProviderRouter
        if len(solver_outputs) > 0:
            try:
                llm_reflection = self._llm_reflect(problem, solver_outputs)
                if llm_reflection:
                    return llm_reflection
            except Exception as error:
                logger.warning(f"LLM Reflection failed ({error}). Using heuristic reflection output.")

        summary = "Unanimous agreement across solvers." if not contradictions else f"Contradiction detected: Solvers disagree on final answer ({unique_answers})."

        return ReflectionOutput(
            contradictions_found=contradictions,
            hallucination_detected=False,
            discrepancies=discrepancies,
            math_inconsistencies=math_inconsistencies,
            suggested_corrections=suggested_corrections,
            solver_agreements={"unique_answers_count": len(unique_answers), "answers": answers},
            summary=summary,
        )

    def _llm_reflect(self, problem: str, solver_outputs: Dict[str, Dict[str, Any]]) -> Optional[ReflectionOutput]:
        prompt = f"Problem:\n{problem}\n\n"
        for s_id, s_data in solver_outputs.items():
            prompt += f"--- Solution from Agent '{s_id}' ---\n"
            prompt += f"Steps:\n{s_data.get('solution', 'N/A')}\n"
            prompt += f"Final Answer: {s_data.get('answer', 'N/A')}\n\n"

        prompt += """Tasks:
1. Identify any mathematical contradictions or discrepancies between solvers.
2. Check for calculation mistakes or ungrounded math hallucinations.
3. Suggest necessary corrections.

Respond EXACTLY in this format:
CONTRADICTIONS_FOUND: [True/False]
HALLUCINATION_DETECTED: [True/False]
DISCREPANCIES: [Short description or None]
INCONSISTENCIES: [Short description of math errors or None]
CORRECTIONS: [Short suggestion or None]
SUMMARY: [One line summary]
"""
        res: ProviderResponse = self.router.generate(
            prompt=prompt,
            system_instruction=REFLECTION_SYSTEM_PROMPT,
            target_provider="GEMINI",
            max_tokens=512,
            temperature=0.1,
        )

        if not res.success or not res.raw_text:
            return None

        text = res.raw_text
        contra_m = re.search(r"CONTRADICTIONS_FOUND:\s*(True|False)", text, re.I)
        hallu_m = re.search(r"HALLUCINATION_DETECTED:\s*(True|False)", text, re.I)
        disc_m = re.search(r"DISCREPANCIES:\s*(.*)", text, re.I)
        incon_m = re.search(r"INCONSISTENCIES:\s*(.*)", text, re.I)
        corr_m = re.search(r"CORRECTIONS:\s*(.*)", text, re.I)
        summ_m = re.search(r"SUMMARY:\s*(.*)", text, re.I)

        contradictions = (contra_m.group(1).lower() == "true") if contra_m else False
        hallucination = (hallu_m.group(1).lower() == "true") if hallu_m else False

        discrepancies = [disc_m.group(1).strip()] if disc_m and disc_m.group(1).strip().lower() != "none" else []
        math_inconsistencies = [incon_m.group(1).strip()] if incon_m and incon_m.group(1).strip().lower() != "none" else []
        suggested_corrections = [corr_m.group(1).strip()] if corr_m and corr_m.group(1).strip().lower() != "none" else []
        summary = summ_m.group(1).strip() if summ_m else f"Reflection completed via {res.provider}."

        answers = {s_id: s_data.get("answer", "").strip() for s_id, s_data in solver_outputs.items()}

        return ReflectionOutput(
            contradictions_found=contradictions,
            hallucination_detected=hallucination,
            discrepancies=discrepancies,
            math_inconsistencies=math_inconsistencies,
            suggested_corrections=suggested_corrections,
            solver_agreements={"answers": answers},
            summary=summary,
        )
