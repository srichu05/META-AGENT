"""Mathematical equivalence safeguards preventing false-positive semantic cache hits."""

import re
from typing import List, Optional, Set, Tuple


MATH_OPERATORS = [
    "!=", "<=", ">=", "+/-", "==",
    "+", "-", "*", "/", "^", "=", "<", ">",
    "sqrt", "det", "sin", "cos", "tan", "log", "ln", "exp",
]

MATH_INTENTS = [
    "solve", "evaluate", "simplify", "determinant", "invertible", "inverse",
    "eigenvalue", "eigenvector", "trace", "rank", "derivative", "differentiate",
    "integrate", "factor", "expand", "roots",
]

UNIT_PATTERNS = {
    "meter": r"\b(?:meter|meters|m)\b",
    "kilometer": r"\b(?:kilometer|kilometers|km)\b",
    "centimeter": r"\b(?:centimeter|centimeters|cm)\b",
    "millimeter": r"\b(?:millimeter|millimeters|mm)\b",
    "second": r"\b(?:second|seconds|sec|s)\b",
    "hour": r"\b(?:hour|hours|hr|h)\b",
    "minute": r"\b(?:minute|minutes|min)\b",
    "kilogram": r"\b(?:kilogram|kilograms|kg)\b",
    "gram": r"\b(?:gram|grams|g)\b",
    "degree": r"\b(?:degree|degrees|deg)\b",
    "radian": r"\b(?:radian|radians|rad)\b",
    "percent": r"(?:%|\bpercent\b)",
    "dollar": r"(?:\$|\bdollar|dollars\b)",
    "mph": r"\bmph\b",
    "mps": r"\bmps\b",
}


def extract_numbers(text: str) -> List[float]:
    """
    Extracts all numeric values including integers, floats, scientific notation,
    fractions, and named constants from mathematical prose.
    """
    if not text:
        return []

    lower = text.lower()
    numbers: List[float] = []

    # 1. Named math constants
    for _ in re.finditer(r"\bpi\b", lower):
        numbers.append(3.14159)
    for _ in re.finditer(r"\be\b(?!\^?[a-z])", lower):
        # Match standalone 'e' (Euler's number) when not part of variable/word
        numbers.append(2.71828)

    # 2. Fractions e.g. 1/2, 3/4
    frac_matches = list(re.finditer(r"\b(\d+)\s*\/\s*(\d+)\b", lower))
    frac_spans = set()
    for m in frac_matches:
        num, den = float(m.group(1)), float(m.group(2))
        if den != 0:
            numbers.append(round(num / den, 4))
            for i in range(m.start(), m.end()):
                frac_spans.add(i)

    # 3. Standard floating point and integer numbers
    # Exclude indices covered by fraction match
    cleaned = "".join(" " if i in frac_spans else ch for i, ch in enumerate(lower))
    num_matches = re.findall(r"[-+]?(?:\d+\.\d+|\d+)(?:[eE][-+]?\d+)?", cleaned)
    for token in num_matches:
        try:
            val = float(token)
            numbers.append(round(val, 4))
        except ValueError:
            continue

    return sorted(numbers)


def extract_operators(text: str) -> List[str]:
    """Extracts mathematical operators, functions, and relational symbols."""
    if not text:
        return []

    lower = text.lower()
    found: List[str] = []

    # Check multi-char operators first
    for op in MATH_OPERATORS:
        if len(op) > 1 and op in lower:
            # For alphabetic function names, require word boundary
            if op.isalpha():
                if re.search(r"\b" + re.escape(op) + r"\b", lower):
                    found.append(op)
            else:
                found.append(op)

    # Check single-char operators
    for op in ["+", "-", "*", "/", "^", "=", "<", ">"]:
        # Only count if present outside multi-char operators already caught
        if op in lower:
            found.append(op)

    return sorted(list(set(found)))


def extract_variables(text: str) -> List[str]:
    """Extracts algebraic variables (x, y, z, a, b, c, etc.) from mathematical expressions."""
    if not text:
        return []

    # Match single letters adjacent to digits or operators e.g. 2x, x^2, x +, = y
    vars_found: Set[str] = set()
    pattern = r"(?:(?<=[0-9+\-*\/=\s])|^)([a-zA-Z])(?=(?:[0-9+\-*\/=\s\^]|$))"
    for m in re.finditer(pattern, text):
        var = m.group(1).lower()
        # Filter out common single-letter English words ('a', 'i' when used as pronoun)
        if var in {"x", "y", "z", "n", "k", "t", "u", "v", "w", "b", "c", "d", "m"}:
            vars_found.add(var)
        elif var in {"a", "i"} and any(op in text for op in ["=", "+", "-", "*", "^", "\\"]):
            vars_found.add(var)

    return sorted(list(vars_found))


def extract_units(text: str) -> List[str]:
    """Extracts physical and scientific measurement units."""
    if not text:
        return []

    lower = text.lower()
    found_units: List[str] = []
    for unit_name, regex_pat in UNIT_PATTERNS.items():
        if re.search(regex_pat, lower):
            found_units.append(unit_name)

    return sorted(found_units)


def extract_intents(text: str) -> List[str]:
    """Extracts mathematical operation intent keywords."""
    if not text:
        return []

    lower = text.lower()
    found_intents: List[str] = []
    for intent in MATH_INTENTS:
        if re.search(r"\b" + re.escape(intent) + r"\b", lower):
            found_intents.append(intent)

    return sorted(found_intents)


class MathEquivalenceValidator:
    """
    Conservative mathematical validator that ensures candidate semantic cache
    hits share identical mathematical structure, numbers, operators, and units.
    """

    @classmethod
    def validate_semantic_equivalence(
        cls,
        query_a: str,
        query_b: str,
        context_hash_a: Optional[str] = None,
        context_hash_b: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates whether query_a and query_b represent the identical mathematical problem.
        Returns (True, None) if mathematically equivalent, or (False, rejection_reason).
        """
        # 1. Number Invariant: Must contain identical numerical quantities
        nums_a = extract_numbers(query_a)
        nums_b = extract_numbers(query_b)
        if nums_a != nums_b:
            return False, f"Numerical values differ: {nums_a} vs {nums_b}"

        # 2. Operator Invariant: Must use identical mathematical relations
        ops_a = extract_operators(query_a)
        ops_b = extract_operators(query_b)
        if ops_a != ops_b:
            return False, f"Mathematical operators differ: {ops_a} vs {ops_b}"

        # 3. Unit Invariant: Must use identical physical units
        units_a = extract_units(query_a)
        units_b = extract_units(query_b)
        if units_a != units_b:
            return False, f"Physical units differ: {units_a} vs {units_b}"

        # 4. Intent Invariant: Must request the same mathematical operation
        intents_a = extract_intents(query_a)
        intents_b = extract_intents(query_b)
        if (intents_a or intents_b) and intents_a != intents_b:
            return False, f"Mathematical operation intents differ: {intents_a} vs {intents_b}"

        # 5. Variable Invariant: Algebraic variables must match
        vars_a = extract_variables(query_a)
        vars_b = extract_variables(query_b)
        if (vars_a or vars_b) and vars_a != vars_b:
            return False, f"Algebraic variables differ: {vars_a} vs {vars_b}"

        # 6. Context Invariant: If retrieved context was required, hashes must match
        if context_hash_b and context_hash_a != context_hash_b:
            return False, f"Retrieved knowledge context differs ({context_hash_a} != {context_hash_b})"

        return True, None

