"""
Math Solver Agent - Multi-agent single-call debate with inline RAG
ENHANCED (2025-11-05):
- 3 virtual solvers (Analytical, Creative, Verifier) + Mini-Judge in ONE LLM call
- Inline RAG usage (Option 1) — RAG examples are woven into each solver's reasoning
- Works with updated APIClient (Groq → OpenAI → Cohere → HF fallback)
- GSM8K-friendly output parsing (SOLUTION + FINAL ANSWER)
"""

# TODO(Draft 2): Retain this prototype solver until dedicated solver agents are added.
import re
import logging
from typing import Dict, List, Any, Optional
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure the project root is in the Python path for robust imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import AGENT_ROLES, SYSTEM_CONFIG

from prompts.prompts import get_prompt_template
from providers.router import ProviderRouter
from providers.types import ProviderResponse

logger = logging.getLogger(__name__)



class MathSolverAgent:
    """Individual math solver agent using a multi-agent prompt in a single LLM call."""
    
    def __init__(
        self,
        agent_id: str,
        role: Optional[str] = None,
        solving_style: Optional[str] = None,
        target_provider: str = "GEMINI",
        router: Optional[ProviderRouter] = None,
    ):
        """
        Initialize a Math Solver Agent.

        Args:
            agent_id: Unique identifier for the agent (e.g., 'solver_1', 'solver_2')
            role: Description of the agent's role (auto-loaded from config if None)
            solving_style: Descriptive style name
            target_provider: Target cloud provider ('GEMINI', 'GROQ', 'OPENROUTER')
            router: ProviderRouter instance
        """
        self.agent_id = agent_id
        self.role = role or AGENT_ROLES.get(agent_id, "General Math Solver")
        self.solving_style = solving_style or self.role
        self.target_provider = target_provider.upper()
        self.router = router or ProviderRouter()
        self.system_instruction = get_prompt_template(self.agent_id, self.target_provider)

        # Solving configuration
        self.max_tokens = SYSTEM_CONFIG.get("max_tokens_completion", 1500)
        self.temperature = SYSTEM_CONFIG.get("temperature", 0.2)


    def initialize(self) -> bool:
        """Initialize the solver agent by validating provider availability."""
        status = self.router.validate_providers()
        logger.info(f"✅ Solver '{self.agent_id}' ({self.target_provider}) initialized.")
        return True

    def solve_problem(self, problem: str, context: Any = None) -> Dict[str, Any]:
        """
        Solves a math problem using specialized system instructions and ProviderRouter target provider.
        """
        if not problem or not problem.strip():
            return self._fail("Empty problem provided")

        context_snippets = self._make_inline_rag_snippets(context)
        user_prompt = f"Problem to solve:\n{problem}\n\n"
        if context_snippets:
            user_prompt += f"Context & Reference Hints:\n{context_snippets}\n\n"
        user_prompt += "Formulate step-by-step reasoning and end with:\nFINAL_ANSWER: <value>"

        try:
            logger.info(f"🧮 Agent '{self.agent_id}' solving via provider '{self.target_provider}'...")
            res: ProviderResponse = self.router.generate(
                prompt=user_prompt,
                system_instruction=self.system_instruction,
                target_provider=self.target_provider,
                max_tokens=1024,
                temperature=0.2,
            )

            if res.success and res.raw_text:
                return {
                    "success": True,
                    "agent_id": self.agent_id,
                    "solving_style": self.solving_style,
                    "solution": res.reasoning or res.raw_text,
                    "answer": res.answer,
                    "confidence": res.confidence or 0.85,
                    "api_used": f"{res.provider}/{res.model}",
                    "latency_ms": res.latency_ms,
                    "token_usage": res.token_usage,
                    "cost": res.estimated_cost,
                }

            logger.warning(f"⚠️ Solver '{self.agent_id}' generation failed ({res.error}). Returning fallback.")
            return self._fail(res.error or "Provider generation failed")

        except Exception as e:
            logger.error(f"💥 Exception in MathSolverAgent '{self.agent_id}': {e}", exc_info=True)
            return self._fail(str(e))

    def _fail(self, reason: str) -> Dict[str, Any]:
        return {
            "success": False,
            "agent_id": self.agent_id,
            "error": reason,
            "solution": None,
            "answer": None,
            "confidence": 0.0
        }

    # ---------- Prompt Construction ----------
    def _make_inline_rag_snippets(self, context: Any) -> str:

        """
        Turn RAG context into compact, generalizable hints for solvers.
        Supports str, dict, and list types without failing.
        """
        if not context:
            return ""

        if isinstance(context, str):
            return context.strip()

        if isinstance(context, dict):
            return str(context.get("formatted_context", context))

        hints = []
        if isinstance(context, list):
            for item in context[:5]:
                if isinstance(item, str):
                    hints.append(f"- Reference Context: {item.strip()}")
                elif isinstance(item, dict):
                    meta = item.get("metadata", item)
                    prob = (meta.get("problem") or meta.get("filename") or "").strip()
                    sol = (meta.get("solution") or meta.get("content") or "").strip()
                    ans = (meta.get("answer") or "").strip()

                    if len(sol) > 280:
                        sol = sol[:280].rstrip() + " ..."

                    heuristic = self._extract_quick_heuristic(sol) or sol or "Follow step-by-step reasoning."
                    hint = f"- Reference ({prob[:60]}): {heuristic}" + (f" (ans: {ans})" if ans else "")
                    hints.append(hint)

        return "\n".join(hints) if hints else ""


    # ---------- Parsing ----------
    def _parse_multi_agent_response(self, text: str) -> Dict[str, Any]:
        """
        Parse the multi-agent formatted response and consolidate to a final result.
        Expected sections:
            === ANALYTICAL === ... FINAL ANSWER:
            === CREATIVE === ... FINAL ANSWER:
            === VERIFIER === ...
            === JUDGE === BEST_AGENT: ... FINAL_ANSWER: ... CONFIDENCE:
        """
        try:
            analytical = self._extract_section(text, r"===\s*ANALYTICAL\s*===(.*?)(?===\s*CREATIVE\s*===|===\s*VERIFIER\s*===|===\s*JUDGE\s*===|$)")
            creative   = self._extract_section(text, r"===\s*CREATIVE\s*===(.*?)(?===\s*VERIFIER\s*===|===\s*JUDGE\s*===|$)")
            verifier   = self._extract_section(text, r"===\s*VERIFIER\s*===(.*?)(?===\s*JUDGE\s*===|$)")
            judge      = self._extract_section(text, r"===\s*JUDGE\s*===(.*)$")

            analytical_ans = self._extract_final_answer(analytical)
            creative_ans   = self._extract_final_answer(creative)
            judge_final    = self._extract_tag(judge, r"FINAL_ANSWER:\s*(.+)")
            judge_conf     = self._extract_confidence(judge)
            best_agent     = self._extract_tag(judge, r"BEST_AGENT:\s*([A-Za-z]+)")

            # Choose the judge's answer if looks valid, else fallback to consistent solver answer
            final_answer = self._pick_final_answer(judge_final, analytical_ans, creative_ans)

            # Build a readable combined solution (for UI/logs)
            solution_parts = []
            if analytical:
                solution_parts.append("**Analytical**\n" + self._extract_solution_body(analytical))
            if creative:
                solution_parts.append("**Creative**\n" + self._extract_solution_body(creative))
            if verifier:
                solution_parts.append("**Verifier**\n" + verifier.strip())
            if judge:
                solution_parts.append("**Judge**\n" + judge.strip())

            combined_solution = "\n\n".join(part for part in solution_parts if part.strip())

            # Confidence
            confidence = judge_conf if judge_conf is not None else self._fallback_confidence(analytical, creative, verifier)

            return {
                "solution": combined_solution.strip(),
                "answer": self._cleanup_number_str(final_answer),
                "confidence": float(confidence)
            }

        except Exception as e:
            logger.warning(f"⚠️ Parser fallback: {str(e)}")
            # Fallback: try to grab any final answer token
            any_final = self._extract_tag(text, r"FINAL_ANSWER:\s*(.+)") or self._extract_first_number(text) or "Parsing Error"
            return {"solution": text.strip(), "answer": self._cleanup_number_str(any_final), "confidence": 0.4}

    # ---------- Helpers: parsing primitives ----------
    def _extract_section(self, text: str, pattern: str) -> str:
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else ""

    def _extract_solution_body(self, section: str) -> str:
        m = re.search(r"SOLUTION:\s*(.*?)(FINAL ANSWER:|$)", section, re.DOTALL | re.IGNORECASE)
        body = m.group(1).strip() if m else section.strip()
        return body[:1200] if len(body) > 1200 else body

    def _extract_final_answer(self, section: str) -> Optional[str]:
        m = re.search(r"FINAL ANSWER:\s*(.+)", section, re.IGNORECASE)
        if not m:
            return None
        return m.group(1).strip()

    def _extract_tag(self, text: str, pattern: str) -> Optional[str]:
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    def _extract_confidence(self, judge_section: str) -> Optional[float]:
        if not judge_section:
            return None
        m = re.search(r"CONFIDENCE:\s*([01](?:\.\d+)?)", judge_section, re.IGNORECASE)
        try:
            return float(m.group(1)) if m else None
        except Exception:
            return None

    def _first_number_like(self, text: str) -> Optional[str]:
        if not text:
            return None
        for pat in [r"-?\$?\d+(?:[.,]\d+)?", r"-?\d+/\d+", r"-?\d+\.?\d*"]:
            m = re.search(pat, text)
            if m:
                return m.group(0)
        return None

    def _extract_first_number(self, text: str) -> Optional[str]:
        return self._first_number_like(text)

    def _pick_final_answer(self, judge_final: Optional[str], analytical_ans: Optional[str], creative_ans: Optional[str]) -> str:
        # Prefer judge's final if numeric-ish
        if judge_final:
            jf = self._first_number_like(judge_final)
            if jf:
                return jf

        # If both solvers agree on a number, use that
        a_num = self._first_number_like(analytical_ans or "")
        c_num = self._first_number_like(creative_ans or "")
        if a_num and c_num and self._normalize_num(a_num) == self._normalize_num(c_num):
            return a_num

        # Otherwise prefer analytical, then creative
        if a_num:
            return a_num
        if c_num:
            return c_num

        # Last resort: judge text as-is
        return judge_final or analytical_ans or creative_ans or "No final answer found"

    def _normalize_num(self, s: str) -> str:
        return s.replace(",", "").replace("$", "").strip()

    def _cleanup_number_str(self, s: str) -> str:
        if not s:
            return s
        s = s.strip()
        s = s.replace("$", "")
        # Normalize commas in numbers like 1,234.56 -> 1234.56
        if re.match(r"^-?\d{1,3}(,\d{3})*(\.\d+)?$", s):
            s = s.replace(",", "")
        return s

    def _fallback_confidence(self, analytical: str, creative: str, verifier: str) -> float:
        conf = 0.5
        if analytical and len(analytical) > 100:
            conf += 0.1
        if creative and len(creative) > 80:
            conf += 0.05
        if "check" in verifier.lower() or "mistake" in verifier.lower():
            conf += 0.05
        return min(conf, 0.95)

    # ---------- Helpers: RAG heuristics ----------
    def _extract_quick_heuristic(self, solution_text: str) -> Optional[str]:
        """
        Very light heuristic extraction from a solution paragraph to make guidance hints.
        """
        t = solution_text.lower()
        # Common math patterns
        if any(w in t for w in ["percentage", "%", "discount"]):
            return "Convert percentage to decimal, multiply base, then subtract/add accordingly."
        if any(w in t for w in ["fraction", "1/2", "1/3", "1/4", "denominator"]):
            return "Use fraction arithmetic (common denominator or sequential operations)."
        if any(w in t for w in ["area", "perimeter", "triangle", "rectangle", "circle"]):
            return "Identify the right geometry formula and plug in values carefully."
        if any(w in t for w in ["speed", "rate", "mph", "kmh", "time", "distance"]):
            return "Use D = R × T with consistent units."
        if any(w in t for w in ["probability", "outcomes", "favorable"]):
            return "Count total outcomes and favorable outcomes; probability = favorable/total."
        if any(w in t for w in ["equation", "solve for", "variable"]):
            return "Translate to equations, isolate the variable step by step."
        # Default
        if any(w in t for w in ["sum", "difference", "product", "divide", "multiply", "add", "subtract"]):
            return "Perform the indicated operations in order; verify with a quick back-check."
        return None

    # ---------- Common failure wrapper ----------
    def _fail(self, msg: str) -> Dict[str, Any]:
        return {
            "success": False,
            "error": msg,
            "solution": "",
            "answer": "",
            "confidence": 0.0,
            "agent_id": self.agent_id
        }

    # ---------- Diagnostics ----------
    def get_agent_info(self) -> Dict[str, Any]:
        """Returns information about the agent's configuration."""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "solving_style": "multi_agent_one_call",
            "api_client_configured": self.api_client.is_configured() if self.api_client else False,
            "available_providers": list(self.api_client.configured_providers) if self.api_client else [],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "capabilities": [
                "multi_agent_debate_single_call",
                "inline_rag_usage",
                "gsm8k_format_support",
                "structured_output",
                "confidence_scoring"
            ]
        }

    def get_stats(self) -> Dict[str, Any]:
        """Returns runtime statistics about the agent."""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "solving_style": "multi_agent_one_call",
            "initialized": self.api_client is not None,
            "api_configured": self.api_client.is_configured() if self.api_client else False
        }
