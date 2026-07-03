"""
Judge Agent - Evaluates solutions from multiple agents and selects the best one
(Optimized Light Upgrade for Meta-Agent + Math Solver Compatibility)
"""

import re
import logging
from typing import Dict, List, Any, Optional
import sys
import os
from dotenv import load_dotenv  # ✅ NEW

# ✅ Load environment variables
load_dotenv()

# Ensure the project root is in the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from utils.api_client import APIClient
from config import AGENT_ROLES  # ✅ Import agent roles from config

logger = logging.getLogger(__name__)


class JudgeAgent:
    """Judge agent that evaluates and ranks solutions from multiple solver agents."""
    
    def __init__(self, agent_id: str = 'judge', role: Optional[str] = None):
        """
        Initialize the Judge Agent.
        
        Args:
            agent_id: Identifier for this agent (default: 'judge')
            role: Description of the agent's role (auto-loaded from config if None)
        """
        self.agent_id = agent_id
        self.role = role or AGENT_ROLES.get(agent_id, 'Solution Evaluator')
        self.api_client: Optional[APIClient] = None

    def initialize(self) -> bool:
        """Initialize the judge agent by creating an API client."""
        try:
            self.api_client = APIClient()
            
            if not self.api_client.is_configured():
                logger.error(f"❌ Judge agent '{self.agent_id}' initialized but NO API providers are configured!")
                logger.error("💡 Check your .env file and ensure API keys are set correctly")
                return False
            
            provider_status = self.api_client.get_provider_status()
            configured = [p for p, status in provider_status.items() if status]
            logger.info(f"✅ Judge agent '{self.agent_id}' initialized with providers: {configured}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Judge agent: {str(e)}", exc_info=True)
            return False

    def evaluate_solutions(self, problem: str, solutions: Dict[str, Dict[str, Any]], mode: str = "best") -> Dict[str, Any]:
        """
        Evaluates multiple solutions to a problem and selects the best one.
        `mode` reserved for future expansion (best, rank, grade).
        """
        if not solutions:
            logger.warning("No solutions provided to evaluate")
            return {
                "best_agent": None, 
                "best_solution": "No solutions were provided to evaluate.", 
                "success": False,
                "confidence": 0.0,
                "score": 0.0  # ✅ Placeholder for scoring
            }

        if not self.api_client:
            logger.error("Judge agent not initialized. Call initialize() first.")
            return {
                "success": False,
                "error": "Agent not initialized",
                "best_agent": None,
                "best_solution": "Agent initialization failed",
                "score": 0.0  # ✅
            }

        if len(solutions) == 1:
            agent_id, solution_data = list(solutions.items())[0]
            logger.info(f"Only one solution from '{agent_id}' - returning by default")
            return {
                "success": True,
                "best_agent": agent_id,
                "best_solution": solution_data.get("solution", ""),
                "evaluation_reasoning": "Only one solution was provided.",
                "confidence": solution_data.get('confidence', 0.5),
                "score": 1.0  # ✅
            }

        prompt = self._create_evaluation_prompt(problem, solutions)
        
        try:
            logger.info(f"Evaluating {len(solutions)} solutions using AI judge...")
            response = self.api_client.call_best_available_api(
                prompt, 
                max_tokens=1024, 
                temperature=0.1
            )
            
            if response.get('success'):
                evaluation_text = response.get('response', '')
                parsed_eval = self._parse_evaluation(evaluation_text, solutions)
                best_agent_id = parsed_eval.get('best_agent')

                if best_agent_id and best_agent_id in solutions:
                    best_solution_data = solutions[best_agent_id]
                    logger.info(f"✅ Best solution selected: Agent '{best_agent_id}'")
                    return {
                        "success": True,
                        "best_agent": best_agent_id,
                        "best_solution": best_solution_data.get("solution", ""),
                        "evaluation_reasoning": parsed_eval.get("reasoning", "No specific reasoning provided."),
                        "confidence": self._calculate_evaluation_confidence(parsed_eval),
                        "api_used": response.get('api_used', 'unknown'),
                        "score": 1.0  # ✅ placeholder for future scoring
                    }

            logger.warning("⚠️ AI-based evaluation failed. Using fallback selection method.")
            return self._fallback_selection(solutions)

        except Exception as e:
            logger.error(f"💥 Exception during solution evaluation: {str(e)}", exc_info=True)
            return self._fallback_selection(solutions)

    def _create_evaluation_prompt(self, problem: str, solutions: Dict[str, Dict[str, Any]]) -> str:
        """Creates a detailed prompt for the LLM to evaluate the solutions."""
        prompt = f"You are an expert mathematics professor evaluating different approaches to a problem.\n\n**Problem:**\n{problem}\n\n"
        prompt += "**Here are the proposed solutions:**\n"

        for agent_id, solution_data in solutions.items():
            model_used = solution_data.get("model", "N/A")  # ✅ New safe metadata usage
            prompt += f"\n--- Solution from Agent '{agent_id}' ---\n"
            prompt += f"**Solution Steps:**\n{solution_data.get('solution', 'No steps provided.')}\n"
            prompt += f"**Final Answer:** {solution_data.get('answer', 'Not provided.')}\n"
            prompt += f"**Model/Approach Used:** {model_used}\n"
            prompt += f"**Stated Confidence:** {solution_data.get('confidence', 0.0):.2f}\n"

        prompt += """
---
Your Task:
1. Analyze each solution for correctness, clarity, and efficiency.
2. Identify the best solution. The best solution is the one that is both correct and easy to understand.
3. Check for mathematical correctness step-by-step and avoid hallucinated math.
4. Prefer traditionally accepted solving methods, while appreciating clean modern explanation.

Respond ONLY in the following strict format:

BEST_AGENT: [agent_id]
REASONING: [One short paragraph]
"""
        return prompt

    def _parse_evaluation(self, evaluation_text: str, solutions: Dict[str, Any]) -> Dict[str, Any]:
        """Parses the structured response from the evaluation prompt."""
        best_agent_match = re.search(r"BEST_AGENT:\s*(\w+)", evaluation_text, re.IGNORECASE)
        reasoning_match = re.search(r"REASONING:\s*(.*)", evaluation_text, re.IGNORECASE | re.DOTALL)
        
        best_agent = best_agent_match.group(1) if best_agent_match else None
        reasoning = reasoning_match.group(1).strip() if reasoning_match else "Evaluation was inconclusive."

        if best_agent not in solutions:
            logger.warning(f"LLM suggested '{best_agent}' but not in solutions. Using first available.")
            best_agent = next(iter(solutions.keys()))

        return {"best_agent": best_agent, "reasoning": reasoning}

    def _calculate_evaluation_confidence(self, evaluation_result: Dict) -> float:
        """Calculate confidence score based on evaluation quality."""
        reasoning = evaluation_result.get("reasoning", "").lower()
        if "step" in reasoning:  # ✅ Bonus if evaluator referenced reasoning steps
            return 0.95
        return 0.9 if reasoning else 0.6
        
    def _fallback_selection(self, solutions: Dict[str, Any]) -> Dict[str, Any]:
        """A fallback method to select a solution if the main evaluation fails."""
        logger.info("🔄 Executing fallback selection based on agent confidence...")
        
        best_agent_id = max(
            solutions, 
            key=lambda agent_id: solutions[agent_id].get('confidence', 0.0)
        )
        best_solution_data = solutions[best_agent_id]
        
        logger.info(f"Fallback selected: Agent '{best_agent_id}' with confidence {best_solution_data.get('confidence', 0.5):.2f}")
        
        return {
            "success": True,
            "best_agent": best_agent_id,
            "best_solution": best_solution_data.get("solution", ""),
            "evaluation_reasoning": "Fallback selection: Chose the solution with the highest self-reported confidence.",
            "confidence": best_solution_data.get('confidence', 0.5),
            "fallback_used": True,
            "score": 0.8  # ✅ Fallback has a slightly lower score
        }

    def get_agent_info(self) -> Dict[str, Any]:
        """Returns information about the agent's configuration and capabilities."""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "api_configured": self.api_client.is_configured() if self.api_client else False,
            "available_providers": list(self.api_client.configured_providers) if self.api_client else [],
            "capabilities": [
                "multi_solution_evaluation",
                "comparative_reasoning",
                "best_solution_selection",
                "confidence_scoring",
                "fallback_selection"
            ]
        }

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics about the judge agent."""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "initialized": self.api_client is not None,
            "api_configured": self.api_client.is_configured() if self.api_client else False
        }
