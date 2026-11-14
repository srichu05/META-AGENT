"""Cache eligibility policy ensuring only complete, validated, error-free debates are cached."""

import re
from typing import Optional, Tuple

from graph.state import DebateGraphState

PROVIDER_ERROR_SIGNATURES = [
    r"all\s+cloud\s+providers\s+in\s+order.*failed",
    r"rate_limit",
    r"http\s+429",
    r"http\s+404",
    r"http\s+500",
    r"quota\s+exceeded",
    r"model_not_found",
    r"authentication_error",
    r"provider\s+timeout",
]

PROMPT_LEAK_SIGNATURES = [
    r"security\s+directive",
    r"unprivileged\s+input\s+data",
    r"you\s+are\s+the\s+(?:analytical|fast|alternative|reflection|judge)\s+(?:math\s+)?solver",
    r"system_instruction",
    r"<untrusted_",
    r"</solver_proposal>",
    r"api[_-]?key",
    r"sk-[a-zA-Z0-9]{20,}",
]


class CacheEligibilityPolicy:
    """
    Evaluates whether a completed DebateGraphState qualifies for persistent semantic caching.
    Strictly forbids caching provider errors, rate-limit messages, and partial executions.
    """

    @classmethod
    def is_eligible(
        cls,
        state: DebateGraphState,
        require_grounded_citations: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Determines if a debate state is eligible to be cached.
        Returns (True, None) if eligible, or (False, rejection_reason).
        """
        if not isinstance(state, dict):
            return False, "State is not a valid dictionary"

        # 1. Execution integrity: Must not be a partial or interrupted execution
        if state.get("partial_execution") is True:
            return False, "Debate execution was flagged as partial"

        if state.get("failed_node") is not None:
            return False, f"Debate had a failed node: {state.get('failed_node')}"

        if state.get("error"):
            return False, f"State contains an execution error: {state.get('error')}"

        # 2. Final Answer validation: Must be non-empty and devoid of error messages
        final_answer = (state.get("final_answer") or "").strip()
        if not final_answer:
            return False, "Final answer is empty"

        lower_answer = final_answer.lower()
        for err_sig in PROVIDER_ERROR_SIGNATURES:
            if re.search(err_sig, lower_answer):
                return False, f"Final answer contains provider error signature matching '{err_sig}'"

        for leak_sig in PROMPT_LEAK_SIGNATURES:
            if re.search(leak_sig, lower_answer):
                return False, f"Final answer contains prompt leak or security directive signature matching '{leak_sig}'"

        # 3. Judge output validation: Must have successfully determined a winner
        judge_output = state.get("judge_output")
        if not judge_output or not isinstance(judge_output, dict):
            return False, "Debate lacks valid judge output"

        if judge_output.get("success") is False:
            return False, "Judge marked evaluation as unsuccessful"

        if not judge_output.get("best_agent"):
            return False, "Judge did not designate a best agent"

        # 4. Solvers validation: At least one solver must have executed successfully
        solver_outputs = state.get("solver_outputs") or {}
        if not solver_outputs:
            return False, "No solver outputs are present"

        successful_solvers = [
            s_id for s_id, s_data in solver_outputs.items()
            if isinstance(s_data, dict) and s_data.get("success") is True and s_data.get("answer")
        ]
        if not successful_solvers:
            return False, "Zero solver agents completed successfully"

        # 5. Citation grounding validation: If citations are present, they must be formatted correctly
        citations = state.get("citations")
        if citations:
            for cit in citations:
                if not isinstance(cit, dict) or (not cit.get("filename") and not cit.get("citation_id")):
                    return False, "Citations list contains malformed or unverified citation entries"

        return True, None
