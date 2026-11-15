"""Objective Mathematical Verification Engine.

Performs reference-based mathematical equivalence and correctness checking.
Distinguishes between exact matches, numeric equivalence, algebraic solution sets,
and explicitly inconclusive results. Does NOT rely on string similarity or LLM judgment.
"""

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class VerificationResult:
    """Outcome of deterministic mathematical verification against a reference answer."""

    is_correct: Optional[bool]
    score: Optional[float]
    status: str  # "completed", "inconclusive", "not_applicable"
    method: str  # "exact", "numeric", "fraction", "percentage", "algebraic_set", "multi_part", "inconclusive", "none"
    details: str = ""
    extracted_predicted: Optional[str] = None
    extracted_reference: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_correct": self.is_correct,
            "score": round(self.score, 4) if self.score is not None else None,
            "status": self.status,
            "method": self.method,
            "details": self.details,
            "extracted_predicted": self.extracted_predicted,
            "extracted_reference": self.extracted_reference,
        }


class MathVerifier:
    """Deterministic mathematical correctness verifier."""

    # Patterns for extracting final answers from text
    FINAL_ANSWER_PATTERNS = [
        r"####\s*([^\n\r]+)",
        r"(?:final\s+answer|the\s+answer\s+is|answer\s*:)\s*[:\s]*([^\n\r.]+)",
        r"\\boxed\{([^}]+)\}",
        r"(?:therefore|thus|hence)[,\s]+.*?(?:is|=|equals)\s*([^\n\r.]+)",
    ]

    @classmethod
    def extract_answer_candidate(cls, text: str) -> str:
        """Extracts the most likely concise final answer candidate from solver output."""
        if not text:
            return ""
        text_str = str(text).strip()

        # Try structured markers first
        for pat in cls.FINAL_ANSWER_PATTERNS:
            matches = list(re.finditer(pat, text_str, re.IGNORECASE))
            if matches:
                # Take the last match in the text
                cand = matches[-1].group(1).strip()
                if cand:
                    # Clean markdown and trailing punctuation
                    cand = re.sub(r"[\*`$]", "", cand).strip().rstrip(".")
                    return cand

        # If text is short (< 100 chars), take the whole text
        if len(text_str) < 100:
            return re.sub(r"[\*`$]", "", text_str).strip().rstrip(".")

        # Look at the last non-empty line
        lines = [line.strip() for line in text_str.split("\n") if line.strip()]
        if lines:
            last_line = lines[-1]
            last_line = re.sub(r"[\*`$]", "", last_line).strip().rstrip(".")
            return last_line

        return text_str

    @classmethod
    def verify(
        cls,
        predicted: str,
        reference: Optional[str],
        tolerance: float = 1e-4,
    ) -> VerificationResult:
        """Verifies predicted answer against reference answer.

        Returns VerificationResult with status:
        - 'not_applicable': if reference is None or empty.
        - 'completed': if deterministically verified as True or False.
        - 'inconclusive': if predicted or reference format is too ambiguous.
        """
        if reference is None or not str(reference).strip():
            return VerificationResult(
                is_correct=None,
                score=None,
                status="not_applicable",
                method="none",
                details="No reference answer provided for objective verification.",
            )

        ref_str = str(reference).strip()
        pred_raw = str(predicted or "").strip()
        if not pred_raw:
            return VerificationResult(
                is_correct=False,
                score=0.0,
                status="completed",
                method="exact",
                details="Predicted answer is empty.",
                extracted_predicted="",
                extracted_reference=ref_str,
            )

        pred_cand = cls.extract_answer_candidate(pred_raw)

        # 1. Exact string / normalized string match
        norm_ref = cls._normalize_text(ref_str)
        norm_pred = cls._normalize_text(pred_cand)

        if norm_ref == norm_pred:
            return VerificationResult(
                is_correct=True,
                score=1.0,
                status="completed",
                method="exact",
                details="Exact normalized string match.",
                extracted_predicted=pred_cand,
                extracted_reference=ref_str,
            )

        # 2. Check multi-part expressions (e.g. Area = 120 cm^2, Perimeter = 46 cm)
        multi_part_res = cls._verify_multipart(pred_cand, pred_raw, ref_str)
        if multi_part_res is not None:
            return multi_part_res

        # 3. Check single numeric equivalence
        num_res = cls._verify_numeric(pred_cand, pred_raw, ref_str, tolerance)
        if num_res is not None:
            return num_res

        # 4. Check algebraic solution sets (e.g. x = 3 or x = -3)
        alg_res = cls._verify_algebraic_set(pred_cand, pred_raw, ref_str)
        if alg_res is not None:
            return alg_res

        # 5. Check fractions vs decimals vs percentages
        frac_res = cls._verify_fraction_or_percentage(pred_cand, ref_str, tolerance)
        if frac_res is not None:
            return frac_res

        # 6. Fallback check: If reference is a single clean number and that number is nowhere in pred_raw
        ref_num = cls._parse_single_number(ref_str)
        if ref_num is not None:
            all_pred_nums = cls._extract_all_numbers(pred_raw)
            if not any(abs(n - ref_num) <= tolerance for n in all_pred_nums):
                return VerificationResult(
                    is_correct=False,
                    score=0.0,
                    status="completed",
                    method="numeric",
                    details=f"Reference number {ref_num} not found in predicted output.",
                    extracted_predicted=pred_cand,
                    extracted_reference=ref_str,
                )

        # 7. If structure is too complex or ambiguous to determine deterministically
        return VerificationResult(
            is_correct=None,
            score=None,
            status="inconclusive",
            method="inconclusive",
            details="Answer format is too complex or qualitative for deterministic verification.",
            extracted_predicted=pred_cand,
            extracted_reference=ref_str,
        )

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        """Removes punctuation, extraneous whitespace, LaTeX wrappers, and casing."""
        s = text.lower()
        s = re.sub(r"[\$*`]", "", s)
        s = re.sub(r"\\(?:text|textbf|mathrm)\{([^}]+)\}", r"\1", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @classmethod
    def _parse_single_number(cls, text: str) -> Optional[float]:
        """Parses a single number if the string represents one."""
        cleaned = re.sub(r"[,\$]", "", text.strip())
        # Check fraction a/b
        frac_match = re.fullmatch(r"([+-]?\d+)\s*/\s*(\d+)", cleaned)
        if frac_match:
            den = float(frac_match.group(2))
            if den != 0:
                return float(frac_match.group(1)) / den
        # Check percentage
        pct_match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*%", cleaned)
        if pct_match:
            return float(pct_match.group(1)) / 100.0
        # Check standard float
        try:
            return float(cleaned)
        except ValueError:
            return None

    @classmethod
    def _extract_all_numbers(cls, text: str) -> List[float]:
        """Extracts all standalone numbers from text."""
        nums: List[float] = []
        for m in re.finditer(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", text):
            try:
                nums.append(float(m.group(0)))
            except ValueError:
                continue
        return nums

    @classmethod
    def _verify_numeric(
        cls,
        pred_cand: str,
        pred_raw: str,
        ref_str: str,
        tolerance: float,
    ) -> Optional[VerificationResult]:
        """Checks if reference is a clean number and compares against predicted candidates."""
        ref_num = cls._parse_single_number(ref_str)
        if ref_num is None:
            return None

        # Check candidate first
        pred_num = cls._parse_single_number(pred_cand)
        if pred_num is not None:
            is_match = abs(pred_num - ref_num) <= max(tolerance, abs(ref_num) * tolerance)
            method = "fraction" if ("/" in pred_cand or "/" in ref_str) else ("percentage" if ("%" in pred_cand or "%" in ref_str) else "numeric")
            return VerificationResult(
                is_correct=is_match,
                score=1.0 if is_match else 0.0,
                status="completed",
                method=method,
                details=f"Candidate {method} match: {pred_num} vs reference {ref_num}.",
                extracted_predicted=str(pred_num),
                extracted_reference=str(ref_num),
            )

        # Extract all numbers from pred_cand
        cand_nums = cls._extract_all_numbers(pred_cand)
        if cand_nums:
            last_num = cand_nums[-1]
            is_match = abs(last_num - ref_num) <= max(tolerance, abs(ref_num) * tolerance)
            if is_match:
                return VerificationResult(
                    is_correct=True,
                    score=1.0,
                    status="completed",
                    method="numeric",
                    details=f"Numeric match from candidate tokens: {last_num} == {ref_num}.",
                    extracted_predicted=str(last_num),
                    extracted_reference=str(ref_num),
                )

        return None

    @classmethod
    def _verify_fraction_or_percentage(
        cls,
        pred_cand: str,
        ref_str: str,
        tolerance: float,
    ) -> Optional[VerificationResult]:
        """Checks equivalent values across fractions, decimals, and percentages."""
        ref_pct = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*%", ref_str.strip())
        pred_pct = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%", pred_cand.strip())

        ref_val = cls._parse_single_number(ref_str)
        pred_val = cls._parse_single_number(pred_cand)

        if ref_val is not None and pred_val is not None:
            # Check direct or 100x ratio (e.g. 0.3 vs 30%)
            if abs(ref_val - pred_val) <= tolerance:
                return VerificationResult(
                    is_correct=True,
                    score=1.0,
                    status="completed",
                    method="fraction",
                    details=f"Value equivalence: {pred_val} == {ref_val}.",
                    extracted_predicted=pred_cand,
                    extracted_reference=ref_str,
                )
            if (ref_pct or pred_pct) and abs(ref_val * 100 - pred_val) <= tolerance:
                return VerificationResult(
                    is_correct=True,
                    score=1.0,
                    status="completed",
                    method="percentage",
                    details=f"Percentage equivalence: {pred_val}% == {ref_val}.",
                    extracted_predicted=pred_cand,
                    extracted_reference=ref_str,
                )
        return None

    @classmethod
    def _verify_algebraic_set(
        cls,
        pred_cand: str,
        pred_raw: str,
        ref_str: str,
    ) -> Optional[VerificationResult]:
        """Verifies solution sets such as 'x = 3 or x = -3' against reference."""
        # Check if reference has "or" / "," pattern with numbers
        if "or" in ref_str.lower() or "," in ref_str:
            ref_nums = set(cls._extract_all_numbers(ref_str))
            if ref_nums:
                # Check candidate numbers
                pred_nums = set(cls._extract_all_numbers(pred_cand))
                if not pred_nums:
                    pred_nums = set(cls._extract_all_numbers(pred_raw))

                if ref_nums.issubset(pred_nums):
                    # Check for extra unwanted numbers in candidate if candidate is concise
                    if len(pred_nums) == len(ref_nums):
                        return VerificationResult(
                            is_correct=True,
                            score=1.0,
                            status="completed",
                            method="algebraic_set",
                            details=f"Exact algebraic solution set match: {sorted(list(ref_nums))}.",
                            extracted_predicted=str(sorted(list(pred_nums))),
                            extracted_reference=str(sorted(list(ref_nums))),
                        )
                    # If reference values are all present
                    return VerificationResult(
                        is_correct=True,
                        score=1.0,
                        status="completed",
                        method="algebraic_set",
                        details=f"All reference roots {sorted(list(ref_nums))} found in solution.",
                        extracted_predicted=str(sorted(list(pred_nums))),
                        extracted_reference=str(sorted(list(ref_nums))),
                    )
                else:
                    missing = ref_nums - pred_nums
                    return VerificationResult(
                        is_correct=False,
                        score=0.0,
                        status="completed",
                        method="algebraic_set",
                        details=f"Missing roots from solution set: {sorted(list(missing))}.",
                        extracted_predicted=str(sorted(list(pred_nums))),
                        extracted_reference=str(sorted(list(ref_nums))),
                    )
        return None

    @classmethod
    def _verify_multipart(
        cls,
        pred_cand: str,
        pred_raw: str,
        ref_str: str,
    ) -> Optional[VerificationResult]:
        """Verifies multi-part answers such as 'Area = 120 cm^2, Perimeter = 46 cm'."""
        # Check if reference has key labels like Area, Perimeter, etc.
        parts = [p.strip() for p in re.split(r"[,;]", ref_str) if p.strip()]
        if len(parts) >= 2 and any("=" in p or ":" in p for p in parts):
            all_parts_matched = True
            mismatches: List[str] = []

            for part in parts:
                nums = cls._extract_all_numbers(part)
                # Find label
                label_match = re.search(r"([a-zA-Z]+)\s*[=:]", part)
                label = label_match.group(1).lower() if label_match else ""

                if nums:
                    target_num = nums[0]
                    # Check if target_num appears near label or in candidate
                    if label:
                        label_pattern = rf"{label}\s*[=:]?\s*[-+]?(?:\d*\.\d+|\d+)"
                        found = re.search(label_pattern, pred_raw, re.IGNORECASE)
                        if found and str(int(target_num) if target_num.is_integer() else target_num) in found.group(0):
                            continue
                    # Check if number appears anywhere in prediction
                    if target_num in cls._extract_all_numbers(pred_raw):
                        continue
                    all_parts_matched = False
                    mismatches.append(f"{label or part} expected {target_num}")

            if all_parts_matched:
                return VerificationResult(
                    is_correct=True,
                    score=1.0,
                    status="completed",
                    method="multi_part",
                    details=f"All {len(parts)} reference parts verified successfully.",
                    extracted_predicted=pred_cand,
                    extracted_reference=ref_str,
                )
            else:
                return VerificationResult(
                    is_correct=False,
                    score=0.0,
                    status="completed",
                    method="multi_part",
                    details=f"Multi-part mismatch: {'; '.join(mismatches)}.",
                    extracted_predicted=pred_cand,
                    extracted_reference=ref_str,
                )
        return None
