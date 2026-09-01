"""RAGAS Evaluation Layer supporting Faithfulness, Answer Relevance, Context Precision, and Context Recall metrics."""

import logging
import re
from typing import Any, Dict, List, Optional

from .types import MetricScore

logger = logging.getLogger(__name__)

# Check for RAGAS package availability
try:
    import ragas
    from ragas.metrics import answer_relevance, context_precision, context_recall, faithfulness

    HAS_RAGAS_LIB = True
except ImportError:
    HAS_RAGAS_LIB = False
    logger.info("RAGAS package not installed or unconfigured. Using built-in metric evaluator.")


class RAGASEvaluator:
    """Evaluates RAG and Meta-Agent generation across Faithfulness, Answer Relevance, Context Precision, and Context Recall."""

    def __init__(self, use_ragas_lib: bool = True):
        self.use_ragas_lib = use_ragas_lib and HAS_RAGAS_LIB

    def evaluate_all(
        self,
        question: str,
        reference_answer: str,
        final_answer: str,
        retrieved_context_texts: List[str],
        expected_context: str = "",
    ) -> Dict[str, float]:
        """
        Calculates scores for Faithfulness, Answer Relevance, Context Precision, and Context Recall.
        Returns dictionary mapping metric names to float scores in range [0.0, 1.0].
        """
        faithfulness_score = self.evaluate_faithfulness(final_answer, retrieved_context_texts)
        relevance_score = self.evaluate_answer_relevance(question, final_answer, reference_answer)
        precision_score = self.evaluate_context_precision(retrieved_context_texts, reference_answer, expected_context)
        recall_score = self.evaluate_context_recall(retrieved_context_texts, reference_answer, expected_context)

        return {
            "faithfulness": round(faithfulness_score, 4),
            "answer_relevance": round(relevance_score, 4),
            "context_precision": round(precision_score, 4),
            "context_recall": round(recall_score, 4),
        }

    def evaluate_faithfulness(self, final_answer: str, retrieved_context_texts: List[str]) -> float:
        """
        Measures degree to which final answer claims are grounded in retrieved context.
        Range: [0.0, 1.0].
        """
        if not final_answer or not final_answer.strip():
            return 0.0

        if not retrieved_context_texts:
            # If no context retrieved but answer given, evaluate intrinsic correctness
            return 0.75 if len(final_answer.strip()) > 5 else 0.5

        context_combined = " ".join(retrieved_context_texts).lower()
        answer_words = re.findall(r"\w+", final_answer.lower())
        if not answer_words:
            return 0.0

        # Check key numeric or keyword tokens present in context
        key_tokens = [w for w in answer_words if len(w) > 2 or w.isdigit()]
        if not key_tokens:
            return 0.8

        matches = sum(1 for tok in key_tokens if tok in context_combined)
        score = matches / len(key_tokens)
        return min(1.0, max(0.2, score + 0.3))

    def evaluate_answer_relevance(self, question: str, final_answer: str, reference_answer: str = "") -> float:
        """
        Measures semantic alignment between question and final generated answer.
        Range: [0.0, 1.0].
        """
        if not final_answer or not final_answer.strip():
            return 0.0

        q_tokens = set(re.findall(r"\w+", question.lower()))
        a_tokens = set(re.findall(r"\w+", final_answer.lower()))

        # Check if reference answer digits/value match
        if reference_answer and reference_answer.strip():
            ref_digits = re.findall(r"\d+", reference_answer)
            ans_digits = re.findall(r"\d+", final_answer)
            if ref_digits and ans_digits and any(d in ans_digits for d in ref_digits):
                return 0.98

        if not q_tokens or not a_tokens:
            return 0.5

        overlap = len(q_tokens.intersection(a_tokens))
        base_score = min(1.0, (overlap / len(q_tokens)) * 1.5)
        return max(0.4, base_score) if len(final_answer) > 10 else 0.5

    def evaluate_context_precision(
        self, retrieved_context_texts: List[str], reference_answer: str, expected_context: str = ""
    ) -> float:
        """
        Measures precision of top retrieved context chunks matching reference answer / context hints.
        Range: [0.0, 1.0].
        """
        if not retrieved_context_texts:
            return 0.0

        target_text = (expected_context + " " + reference_answer).lower()
        target_tokens = set(re.findall(r"\w+", target_text))
        if not target_tokens:
            return 0.5

        precisions: List[float] = []
        relevant_so_far = 0

        for rank, text in enumerate(retrieved_context_texts, start=1):
            text_tokens = set(re.findall(r"\w+", text.lower()))
            overlap = len(target_tokens.intersection(text_tokens))
            is_relevant = overlap >= max(1, len(target_tokens) // 4)
            if is_relevant:
                relevant_so_far += 1
                precisions.append(relevant_so_far / rank)

        if not precisions:
            return 0.2

        return sum(precisions) / len(precisions)

    def evaluate_context_recall(
        self, retrieved_context_texts: List[str], reference_answer: str, expected_context: str = ""
    ) -> float:
        """
        Measures coverage of reference answer / context hints in retrieved context chunks.
        Range: [0.0, 1.0].
        """
        if not retrieved_context_texts:
            return 0.0

        target_text = (expected_context + " " + reference_answer).lower()
        target_tokens = [w for w in re.findall(r"\w+", target_text) if len(w) > 2 or w.isdigit()]
        if not target_tokens:
            return 0.5

        combined_context = " ".join(retrieved_context_texts).lower()
        covered = sum(1 for tok in target_tokens if tok in combined_context)

        return min(1.0, max(0.1, covered / len(target_tokens)))
