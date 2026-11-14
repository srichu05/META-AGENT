"""Mathematical text normalization, hashing, and scope calculation."""

import hashlib
import re
from typing import Any, Dict, List, Optional


# Common words for numbers to standardize representation
NUMBER_WORDS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "half": "0.5",
    "quarter": "0.25",
}

# Conversational prefixes that do not change mathematical content
CONVERSATIONAL_PREFIXES = [
    r"^(?:can\s+you\s+|could\s+you\s+)?(?:please\s+)?(?:can\s+you\s+|could\s+you\s+)?(?:help\s+me\s+)?(?:to\s+)?(?:solve|calculate|compute|evaluate|find|determine)\s+(?:the\s+value\s+of\s+)?",
    r"^(?:what\s+is\s+the\s+value\s+of|what\s+is|what\s+are)\s+",
    r"^(?:determine|evaluate|find|calculate|solve)\s+",
]


def normalize_query(query: str) -> str:
    """
    Normalizes a mathematical query by standardizing symbols, LaTeX notation,
    collapsing whitespace, and removing non-semantic conversational filler.
    """
    if not query:
        return ""

    text = query.strip()

    # 1. Strip surrounding LaTeX math delimiters
    text = re.sub(r"^\$+\s*", "", text)
    text = re.sub(r"\s*\$+$", "", text)
    text = re.sub(r"^\\\[\s*", "", text)
    text = re.sub(r"\s*\\\]$", "", text)
    text = re.sub(r"^\\\(\s*", "", text)
    text = re.sub(r"\s*\\\)$", "", text)

    # 2. Lowercase standard words (will normalize math symbols separately)
    text = text.lower()

    # 3. Unicode and LaTeX symbol normalization
    text = text.replace("−", "-").replace("—", "-")
    text = text.replace("×", "*").replace("·", "*")
    text = text.replace("÷", "/")
    text = text.replace("²", "^2").replace("³", "^3").replace("⁴", "^4")
    text = text.replace("≠", "!=").replace("≤", "<=").replace("≥", ">=")

    # LaTeX commands
    text = re.sub(r"\\times\b", "*", text)
    text = re.sub(r"\\cdot\b", "*", text)
    text = re.sub(r"\\div\b", "/", text)
    text = re.sub(r"\\pm\b", "+/-", text)
    text = re.sub(r"\\pi\b", "pi", text)
    text = re.sub(r"\\theta\b", "theta", text)
    text = re.sub(r"\\sqrt\{([^}]+)\}", r"sqrt(\1)", text)
    text = re.sub(r"\\frac\{([^}]+)\}\{([^}]+)\}", r"(\1)/(\2)", text)
    text = text.replace(r"\left", "").replace(r"\right", "")

    # 4. Standardize spacing around operators: +, -, *, /, =, <, >
    # Avoid splitting negative numbers e.g. -3
    text = re.sub(r"\s*([=+\*\/<>])\s*", r" \1 ", text)
    text = re.sub(r"\s*-\s*", r" - ", text)

    # 5. Collapse repeated whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # 6. Remove conversational prefixes carefully if mathematical core remains
    for prefix_pat in CONVERSATIONAL_PREFIXES:
        match = re.search(prefix_pat, text, flags=re.IGNORECASE)
        if match:
            candidate = text[match.end():].strip()
            # Only strip prefix if substantive math content remains
            if len(candidate) >= 3 and any(c in candidate for c in "0123456789xyzabc=+-*/^"):
                text = candidate
                break

    # 7. Strip trailing punctuation: ?, ., !
    text = re.sub(r"[\?\.\!]+$", "", text).strip()

    # 8. Re-collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def compute_scope_hash(
    namespace: str = "math_debate",
    schema_version: str = "v1.0",
    prompt_version: str = "v1.0",
    model: str = "gemini-2.5-flash",
    temperature: float = 0.2,
    user_id: Optional[str] = None,
) -> str:
    """Computes a deterministic hash isolating execution parameters, tenant namespace, and user context."""
    user_segment = f":user_{user_id}" if user_id else ""
    scope_str = f"{namespace}:{schema_version}:{prompt_version}:{model}:{temperature:.2f}{user_segment}"
    return hashlib.sha256(scope_str.encode("utf-8")).hexdigest()[:16]


def compute_query_hash(normalized_query: str, scope_hash: str) -> str:
    """Computes a unique SHA-256 hash identifying a normalized query within a scope."""
    key = f"{scope_hash}:{normalized_query}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def compute_context_hash(context: Any) -> Optional[str]:
    """
    Computes a deterministic hash over retrieved context chunks.
    Ensures that if underlying document corpus changes, cached entries mismatch safely.
    """
    if context is None:
        return None

    if isinstance(context, str):
        if not context.strip():
            return None
        return hashlib.sha256(context.strip().encode("utf-8")).hexdigest()[:16]

    if isinstance(context, dict):
        chunks = context.get("chunks", [])
        if not chunks:
            return None
        # Hash sorted chunk IDs or content
        chunk_sigs = []
        for c in chunks:
            if isinstance(c, dict):
                sig = f"{c.get('document_id')}:{c.get('chunk_id')}:{c.get('vector_index')}"
            else:
                sig = str(c)
            chunk_sigs.append(sig)
        chunk_sigs.sort()
        joined = "|".join(chunk_sigs)
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]

    if isinstance(context, (list, tuple)):
        if not context:
            return None
        joined = "|".join(str(c) for c in context)
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]

    return None
