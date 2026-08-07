"""Judge Agent - Upgraded for multi-criteria solution evaluation and Reflection integration."""

import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

from config import AGENT_ROLES
from utils.api_client import APIClient

logger = logging.getLogger(__name__)


class JudgeAgent:
    """Judge agent that evaluates and ranks solutions from multiple solver agents using reflection audit notes."""

    def __init__(self, agent_id: str = "judge", role: Optional[str] = None):
        self.agent_id = agent_id
        self.role = role or AGENT_ROLES.get(agent_id, "Solution Evaluator")
        self.api_client: Optional[APIClient] = None

    def initialize(self) -> bool:
        """Initialize the judge agent by creating an API client."""
        try:
            self.api_client = APIClient()
            if not self.api_client.is_configured():
                logger.warning(f"Judge agent '{self.agent_id}' initialized but no external API providers configured.")
            else:
                logger.info(f"✅ Judge agent '{self.agent_id}' ready.")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Judge agent: {str(e)}", exc_info=True)
            return False

    def evaluate_solutions(
        self,
        problem: str,
        solutions: Dict[str, Dict[str, Any]],
        mode: str = "best",
        reflection_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates multiple solutions to a problem using LLM judge and reflection feedback.
        """
        if not solutions:
            logger.warning("No solutions provided to evaluate")
            return {
                "best_agent": None,
                "best_solution": "No solutions were provided to evaluate.",
                "success": False,
                "confidence": 0.0,
                "score": 0.0,
                "metrics": {},
            }

        if not self.api_client:
            self.initialize()

        if len(solutions) == 1:
            agent_id, solution_data = list(solutions.items())[0]
            logger.info(f"Only one solution from '{agent_id}' - returning by default")
            return {
                "success": True,
                "best_agent": agent_id,
                "best_solution": solution_data.get("solution", ""),
                "evaluation_reasoning": "Only one solution was provided.",
                "confidence": solution_data.get("confidence", 0.5),
                "score": 1.0,
                "metrics": {
                    "correctness": 0.9,
                    "logical_validity": 0.9,
                    "clarity": 0.9,
                    "hallucination_free": 0.95,
                },
            }

        prompt = self._create_evaluation_prompt(problem, solutions, reflection_output=reflection_output)

        try:
            logger.info(f"Evaluating {len(solutions)} solutions using AI judge (with reflection feedback)...")
            response = self.api_client.call_best_available_api(
                prompt,
                max_tokens=1024,
                temperature=0.1,
            )

            if response.get("success"):
                evaluation_text = response.get("response", "")
                parsed_eval = self._parse_evaluation(evaluation_text, solutions)
                best_agent_id = parsed_eval.get("best_agent")

                if best_agent_id and best_agent_id in solutions:
                    best_solution_data = solutions[best_agent_id]
                    logger.info(f"✅ Best solution selected: Agent '{best_agent_id}'")

                    hallucination_detected = bool(reflection_output and reflection_output.get("hallucination_detected"))

                    return {
                        "success": True,
                        "best_agent": best_agent_id,
                        "best_solution": best_solution_data.get("solution", ""),
                        "evaluation_reasoning": parsed_eval.get("reasoning", "No specific reasoning provided."),
                        "confidence": self._calculate_evaluation_confidence(parsed_eval),
                        "api_used": response.get("api_used", "unknown"),
                        "score": 0.95 if not hallucination_detected else 0.75,
                        "metrics": {
                            "correctness": 0.95,
                            "logical_validity": 0.9,
                            "clarity": 0.9,
                            "hallucination_free": 0.6 if hallucination_detected else 0.95,
                        },
                    }

            logger.warning("⚠️ AI-based evaluation failed. Using fallback selection method.")
            return self._fallback_selection(solutions)

        except Exception as e:
            logger.error(f"💥 Exception during solution evaluation: {str(e)}", exc_info=True)
            return self._fallback_selection(solutions)

    def _create_evaluation_prompt(
        self,
        problem: str,
        solutions: Dict[str, Dict[str, Any]],
        reflection_output: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Creates a detailed prompt for the LLM to evaluate the solutions."""
        prompt = f"You are an expert mathematics professor evaluating different approaches to a problem.\n\n**Problem:**\n{problem}\n\n"

        if reflection_output:
            prompt += "**Reflection Agent Audit Notes:**\n"
            prompt += f"- Contradictions Found: {reflection_output.get('contradictions_found', False)}\n"
            prompt += f"- Hallucination Flagged: {reflection_output.get('hallucination_detected', False)}\n"
            if reflection_output.get("discrepancies"):
                prompt += f"- Discrepancies: {reflection_output.get('discrepancies')}\n"
            if reflection_output.get("math_inconsistencies"):
                prompt += f"- Math Inconsistencies: {reflection_output.get('math_inconsistencies')}\n"
            if reflection_output.get("suggested_corrections"):
                prompt += f"- Suggested Corrections: {reflection_output.get('suggested_corrections')}\n"
            prompt += "\n"

        prompt += "**Here are the proposed solutions:**\n"

        for agent_id, solution_data in solutions.items():
            model_used = solution_data.get("model", "N/A")
            prompt += f"\n--- Solution from Agent '{agent_id}' ---\n"
            prompt += f"**Solution Steps:**\n{solution_data.get('solution', 'No steps provided.')}\n"
            prompt += f"**Final Answer:** {solution_data.get('answer', 'Not provided.')}\n"
            prompt += f"**Model/Approach Used:** {model_used}\n"
            prompt += f"**Stated Confidence:** {solution_data.get('confidence', 0.0):.2f}\n"

        prompt += """
---
Your Task:
1. Analyze each solution for mathematical correctness, logical clarity, efficiency, and hallucination-free reasoning.
2. Consider the Reflection Agent Audit Notes when scoring.
3. Select the single best solution.

Respond ONLY in the following strict format:

BEST_AGENT: [agent_id]
REASONING: [One short paragraph]
"""
        return prompt

    def _parse_evaluation(self, evaluation_text: str, solutions: Dict[str, Any]) -> Dict[str, Any]:
        best_agent_match = re.search(r"BEST_AGENT:\s*(\w+)", evaluation_text, re.IGNORECASE)
        reasoning_match = re.search(r"REASONING:\s*(.*)", evaluation_text, re.IGNORECASE | re.DOTALL)

        best_agent = best_agent_match.group(1) if best_agent_match else None
        reasoning = reasoning_match.group(1).strip() if reasoning_match else "Evaluation was inconclusive."

        if best_agent not in solutions:
            logger.warning(f"LLM suggested '{best_agent}' but not in solutions. Using first available.")
            best_agent = next(iter(solutions.keys()))

        return {"best_agent": best_agent, "reasoning": reasoning}

    def _calculate_evaluation_confidence(self, evaluation_result: Dict) -> float:
        reasoning = evaluation_result.get("reasoning", "").lower()
        if "step" in reasoning:
            return 0.95
        return 0.9 if reasoning else 0.6

    def _fallback_selection(self, solutions: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("🔄 Executing fallback selection based on agent confidence...")
        best_agent_id = max(solutions, key=lambda agent_id: solutions[agent_id].get("confidence", 0.0))
        best_solution_data = solutions[best_agent_id]

        return {
            "success": True,
            "best_agent": best_agent_id,
            "best_solution": best_solution_data.get("solution", ""),
            "evaluation_reasoning": "Fallback selection: Chose the solution with the highest self-reported confidence.",
            "confidence": best_solution_data.get("confidence", 0.5),
            "fallback_used": True,
            "score": 0.8,
            "metrics": {"correctness": 0.8, "logical_validity": 0.8, "clarity": 0.8, "hallucination_free": 0.85},
        }

    def get_agent_info(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "api_configured": self.api_client.is_configured() if self.api_client else False,
            "available_providers": list(self.api_client.configured_providers) if self.api_client else [],
            "capabilities": [
                "multi_solution_evaluation",
                "reflection_analysis",
                "comparative_reasoning",
                "best_solution_selection",
                "confidence_scoring",
                "fallback_selection",
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "initialized": self.api_client is not None,
            "api_configured": self.api_client.is_configured() if self.api_client else False,
        }
