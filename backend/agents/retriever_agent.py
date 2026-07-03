"""
Retriever Agent - Handles RAG retrieval of similar problems and solutions
UPDATED (Hybrid Compatible) – Works with Local Embeddings + Cloud Fallback
"""

from typing import List, Dict, Any, Optional
import logging
import re
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.api_client import APIClient
from rag.vector_store import MathProblemVectorStore
from config import SYSTEM_CONFIG, RAG_CONFIG, PROBLEM_TYPES

logger = logging.getLogger(__name__)


class RetrieverAgent:
    """Agent responsible for retrieving similar problems and solutions for RAG"""

    def __init__(self, vector_store: Optional[MathProblemVectorStore] = None):
        """
        Initialize the Retriever Agent.

        Args:
            vector_store: MathProblemVectorStore instance for similarity search
        """
        self.agent_id = "retriever"
        self.role = "RAG Retrieval Specialist"
        self.vector_store = vector_store
        self.api_client: Optional[APIClient] = None

        # Load RAG configuration
        self.top_k_retrieval = SYSTEM_CONFIG.get("top_k_retrieval", 5)
        self.similarity_threshold = RAG_CONFIG.get("similarity_threshold", 0.55)

        logger.info("📚 RetrieverAgent created")

    def initialize(self) -> bool:
        """Initialize the retriever agent"""
        try:
            logger.info("🔧 Initializing RetrieverAgent...")

            # Initialize API client (local embeddings built-in)
            self.api_client = APIClient()

            # Vector store is optional, but recommended
            if not self.vector_store:
                logger.warning("⚠️ No vector store provided → RAG disabled")
                return False

            # Log vector store stats
            vs_stats = self.vector_store.get_stats()
            logger.info(f"✅ Vector Store Loaded: {vs_stats.get('total_documents', 0)} examples, Dim={vs_stats.get('dimension', '?')}")

            return True

        except Exception as e:
            logger.error(f"💥 RetrieverAgent init failed: {str(e)}", exc_info=False)
            return False

    def retrieve_similar_problems(
        self,
        query_problem: str,
        top_k: Optional[int] = None,
        problem_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar problems using vector similarity search.
        Uses Local Embeddings FIRST, then falls back to API if needed.
        """
        try:
            if not self.api_client or not self.vector_store:
                return []

            if not query_problem or not query_problem.strip():
                return []

            k = top_k or self.top_k_retrieval

            # Generate query embedding
            embedding = self.api_client.get_embeddings(query_problem)
            if not embedding:
                return []

            # Search vector store
            similar_docs = self.vector_store.search(
                query_embedding=embedding,
                top_k=k,
                threshold=self.similarity_threshold
            )

            # If user wants filtered type search
            if problem_type:
                similar_docs = [
                    d for d in similar_docs
                    if d.get("metadata", {}).get("type") == problem_type
                ]

            # Format results
            results = []
            for doc in similar_docs:
                meta = doc.get("metadata", {})
                results.append({
                    "problem": meta.get("problem", ""),
                    "solution": meta.get("solution", ""),
                    "answer": meta.get("answer", ""),
                    "type": meta.get("type", "unknown"),
                    "difficulty": meta.get("difficulty", "medium"),
                    "similarity_score": doc.get("score", 0.0),
                    "steps": meta.get("steps", []),
                })

            return results

        except Exception as e:
            logger.error(f"💥 Failed RAG retrieval: {str(e)}")
            return []

    def find_solution_patterns(self, problem: str) -> Dict[str, Any]:
        """Analyze problem and find common solution patterns from RAG context"""
        try:
            similar_problems = self.retrieve_similar_problems(problem, top_k=10)

            if not similar_problems:
                return {
                    'problem_type': 'unknown',
                    'difficulty': 'medium',
                    'concepts': 'basic_math',
                    'approaches': 'direct_calculation',
                    'similar_count': 0,
                    'confidence': 0.1,
                    'avg_similarity': 0.0
                }

            types = [p.get('type', 'unknown') for p in similar_problems]
            difficulties = [p.get('difficulty', 'medium') for p in similar_problems]

            most_common_type = max(set(types), key=types.count)
            most_common_difficulty = max(set(difficulties), key=difficulties.count)

            avg_similarity = sum(p.get('similarity_score', 0) for p in similar_problems) / len(similar_problems)

            return {
                'problem_type': most_common_type,
                'difficulty': most_common_difficulty,
                'concepts': self._extract_concepts(problem),
                'approaches': self._suggest_approaches(most_common_type, similar_problems),
                'similar_count': len(similar_problems),
                'confidence': min(0.9, len(similar_problems) / 10),
                'avg_similarity': avg_similarity
            }

        except Exception:
            return {
                'problem_type': 'unknown',
                'difficulty': 'medium',
                'concepts': 'basic_math',
                'approaches': 'direct_calculation',
                'similar_count': 0,
                'confidence': 0.1,
                'avg_similarity': 0.0
            }

    # (Helper functions stay same – unchanged for compatibility)

    def _extract_concepts(self, problem: str) -> str:
        # unchanged
        problem_lower = problem.lower()
        concepts = []
        concept_keywords = {
            'percentages': ['percent', '%', 'percentage'],
            'fractions': ['fraction', 'half', 'quarter', 'third', '1/2', '1/3', '1/4'],
            'geometry': ['area', 'perimeter', 'volume', 'radius', 'diameter', 'circle', 'square', 'triangle'],
            'algebra': ['equation', 'solve for', 'variable', 'x =', 'y =', 'unknown'],
            'rate_problems': ['rate', 'speed', 'time', 'distance', 'mph', 'kmh', 'velocity'],
            'probability': ['probability', 'chance', 'likely', 'odds', 'random'],
            'money_problems': ['money', '$', 'dollar', 'cost', 'price', 'payment', 'expense'],
        }

        for concept, keywords in concept_keywords.items():
            if any(word in problem_lower for word in keywords):
                concepts.append(concept)

        return ', '.join(concepts) if concepts else 'basic_arithmetic'

    def _suggest_approaches(self, problem_type: str, similar_problems: List[Dict]) -> str:
        # unchanged
        type_approaches = {
            'percentage': ['convert_to_decimal', 'use_proportion'],
            'fractions': ['find_common_denominator', 'convert_to_decimals'],
            'geometry': ['use_formulas', 'draw_diagram'],
            'algebra': ['isolate_variable', 'solve_equation'],
            'word_problem': ['identify_operations', 'translate_to_math'],
            'money': ['track_transactions', 'sum_costs'],
            'time_distance': ['use_rate_formula', 'unit_conversion'],
            'probability': ['count_outcomes', 'calculate_ratio'],
            'arithmetic': ['basic_operations', 'order_of_operations']
        }

        approaches = type_approaches.get(problem_type, [])[:3]
        approaches.extend(['step_by_step_calculation', 'verify_answer'])

        return ', '.join(approaches[:5])


    def get_agent_info(self) -> Dict[str, Any]:
        """Get retriever agent information"""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "rag_enabled": self.vector_store is not None,
            "top_k_retrieval": self.top_k_retrieval,
            "similarity_threshold": self.similarity_threshold,
            "vector_store_stats": self.vector_store.get_stats() if self.vector_store else {},
            "supported_problem_types": PROBLEM_TYPES
        }

    def get_stats(self) -> Dict[str, Any]:
        """Runtime statistics for monitoring"""
        stats = {
            "agent_id": self.agent_id,
            "role": self.role,
            "initialized": self.api_client is not None,
            "vector_store_available": self.vector_store is not None,
        }

        if self.vector_store:
            vs_stats = self.vector_store.get_stats()
            stats['vector_store'] = {
                'total_documents': vs_stats.get('total_documents', 0),
                'problem_types': vs_stats.get('problem_types', {}),
                'dimension': vs_stats.get('dimension', 0)
            }

        return stats
    def get_contextual_hints(self, problem: str, max_hints: int = 5):
        try:
            results = self.search_similar(problem, top_k=max_hints)
            hints = []

            for item in results:
                hint_text = item.get("hint") or item.get("solution") or ""
                if hint_text:
                    # Keep hint short
                    hint_text = hint_text.strip()
                    if len(hint_text) > 180:
                        hint_text = hint_text[:180] + "..."
                    hints.append(hint_text)
            return hints[:max_hints]

        except Exception as e:
            logger.error("Failed to generate contextual hints: %s", str(e))
            return []
