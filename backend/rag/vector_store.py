"""
Vector Store for RAG implementation
Handles document embeddings and similarity search
UPDATED: Optimized for GSM8K external corpus integration
"""

# TODO(Draft 2): Replace this custom store with FAISS in the dedicated RAG phase.
import numpy as np
import json
import pickle
import os
import sys
from typing import List, Dict, Any, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import SYSTEM_CONFIG, RAG_CONFIG, PROBLEM_TYPES

logger = logging.getLogger(__name__)


class VectorStore:
    """Base Vector Store class for handling embeddings and similarity search"""
    
    def __init__(self, dimension: Optional[int] = None):
        """
        Initialize the Vector Store.
        
        Args:
            dimension: Embedding dimension (uses config default if None)
        """
        # Use config default if dimension not provided
        self.dimension = dimension or SYSTEM_CONFIG.get("embedding_dimension", 384)
        self.vectors: List[np.ndarray] = []
        self.metadata: List[Dict] = []
        self.documents: List[str] = []
        
        # Load cache path from config
        self.cache_path = RAG_CONFIG.get("embeddings_cache", "./database/vector_store.db")  # ✅ CHANGED: Better default name
        
        # Load RAG configuration
        self.chunk_size = RAG_CONFIG.get("chunk_size", 500)
        self.chunk_overlap = RAG_CONFIG.get("chunk_overlap", 50)
        self.similarity_threshold = RAG_CONFIG.get("similarity_threshold", 0.55)
        
        logger.info(f"📚 Vector store initialized (dimension={self.dimension}, cache={self.cache_path})")
    
    def add_documents(
        self, 
        documents: List[str], 
        metadata: Optional[List[Dict]] = None, 
        embeddings: Optional[List[List[float]]] = None
    ) -> bool:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of document texts
            metadata: List of metadata dictionaries for each document
            embeddings: List of embedding vectors for each document
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Input validation
            if not documents:
                logger.warning("⚠️ No documents provided to add")
                return False
            
            if metadata is None:
                metadata = [{"id": i} for i in range(len(documents))]
            
            if embeddings is None:
                logger.error("❌ Embeddings must be provided")
                raise ValueError("Embeddings must be provided")
            
            # Validate lengths match
            if not (len(documents) == len(metadata) == len(embeddings)):
                logger.error(f"❌ Length mismatch: docs={len(documents)}, meta={len(metadata)}, emb={len(embeddings)}")
                raise ValueError("Documents, metadata, and embeddings must have the same length")
            
            # Validate embedding dimensions
            for i, emb in enumerate(embeddings):
                if len(emb) != self.dimension:
                    logger.error(f"❌ Embedding {i} has dimension {len(emb)}, expected {self.dimension}")
                    raise ValueError(f"Embedding dimension mismatch at index {i}")
            
            # Add to store
            added_count = 0
            for doc, meta, emb in zip(documents, metadata, embeddings):
                self.documents.append(doc)
                self.metadata.append(meta)
                self.vectors.append(np.array(emb))
                added_count += 1
            
            logger.info(f"✅ Added {added_count} documents to vector store (total: {len(self.documents)})")
            return True
            
        except Exception as e:
            logger.error(f"💥 Failed to add documents: {str(e)}", exc_info=True)
            return False
    
    def search(
        self, 
        query_embedding: List[float], 
        top_k: Optional[int] = None, 
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using cosine similarity.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return (uses config default if None)
            threshold: Similarity threshold (uses config default if None)
            
        Returns:
            List of similar documents with scores
        """
        # Use config defaults
        k = top_k or SYSTEM_CONFIG.get("top_k_retrieval", 5)
        thresh = threshold or self.similarity_threshold
        
        if not self.vectors:
            logger.warning("⚠️ Vector store is empty, cannot search")
            return []
        
        try:
            # Validate query embedding dimension
            if len(query_embedding) != self.dimension:
                logger.error(f"❌ Query embedding dimension {len(query_embedding)} doesn't match store dimension {self.dimension}")
                return []
            
            query_vector = np.array(query_embedding).reshape(1, -1)
            vectors_matrix = np.vstack(self.vectors)
            
            # Calculate cosine similarities
            similarities = cosine_similarity(query_vector, vectors_matrix)[0]
            indices = np.argsort(similarities)[::-1]
            
            # Filter by threshold and get top_k
            results = []
            for idx in indices:
                if len(results) >= k:
                    break
                    
                if similarities[idx] >= thresh:
                    self.rag_usage_count += 1
                    self.rag_similarity_scores.append(float(similarities[idx]))
                    prob_type = self.metadata[idx].get("type", "unknown")
                    self.rag_type_usage[prob_type] = self.rag_type_usage.get(prob_type, 0) + 1

                    results.append({
                        "document": self.documents[idx],
                        "metadata": self.metadata[idx],
                        "score": float(similarities[idx]),
                        "index": int(idx)
                    })
            
            logger.info(f"🔍 Search found {len(results)} results above threshold {thresh:.2f}")
            return results
            
        except Exception as e:
            logger.error(f"💥 Error in vector search: {str(e)}", exc_info=True)
            return []
    
    def save(self, path: Optional[str] = None) -> bool:
        """
        Save vector store to disk.
        
        Args:
            path: Path to save to (uses default cache path if None)
            
        Returns:
            True if successful, False otherwise
        """
        save_path = path or self.cache_path
        
        try:
            logger.info(f"💾 Saving vector store to {save_path}...")
            
            data = {
                "vectors": [vec.tolist() for vec in self.vectors],
                "metadata": self.metadata,
                "documents": self.documents,
                "dimension": self.dimension,
                "version": "1.0",  # Version for compatibility
                "config": {  # ✅ NEW: Save config used
                    "similarity_threshold": self.similarity_threshold,
                    "chunk_size": self.chunk_size,
                    "chunk_overlap": self.chunk_overlap
                }
            }
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'wb') as f:
                pickle.dump(data, f)
            
            file_size = os.path.getsize(save_path) / (1024 * 1024)  # ✅ NEW: Show file size
            logger.info(f"✅ Vector store saved successfully ({len(self.documents)} documents, {file_size:.2f} MB)")
            return True
            
        except Exception as e:
            logger.error(f"💥 Failed to save vector store: {str(e)}", exc_info=True)
            return False
    
    def load(self, path: Optional[str] = None) -> bool:
        """
        Load vector store from disk.
        
        Args:
            path: Path to load from (uses default cache path if None)
            
        Returns:
            True if successful, False otherwise
        """
        load_path = path or self.cache_path
        
        try:
            if not os.path.exists(load_path):
                logger.info(f"📁 Vector store file not found at {load_path}")
                return False
            
            logger.info(f"📂 Loading vector store from {load_path}...")
            
            with open(load_path, 'rb') as f:
                data = pickle.load(f)
            
            # Validate loaded data
            if not isinstance(data, dict):
                logger.error("❌ Invalid vector store format")
                return False
            
            required_keys = ["vectors", "metadata", "documents", "dimension"]
            if not all(key in data for key in required_keys):
                logger.error(f"❌ Missing required keys in vector store file")
                return False
            
            self.vectors = [np.array(vec) for vec in data["vectors"]]
            self.metadata = data["metadata"]
            self.documents = data["documents"]
            self.dimension = data["dimension"]
            
            # ✅ NEW: Load saved config if available
            if "config" in data:
                saved_config = data["config"]
                logger.info(f"   Loaded config: threshold={saved_config.get('similarity_threshold')}")
            
            file_size = os.path.getsize(load_path) / (1024 * 1024)  # ✅ NEW: Show file size
            logger.info(f"✅ Vector store loaded successfully ({len(self.documents)} documents, {file_size:.2f} MB, dimension={self.dimension})")
            return True
                
        except Exception as e:
            logger.error(f"💥 Failed to load vector store: {str(e)}", exc_info=True)
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        memory_mb = sum(vec.nbytes for vec in self.vectors) / (1024 * 1024) if self.vectors else 0
        
        # ✅ NEW: Calculate average vector magnitude for health check
        avg_magnitude = 0.0
        if self.vectors:
            magnitudes = [np.linalg.norm(vec) for vec in self.vectors]
            avg_magnitude = sum(magnitudes) / len(magnitudes)
        
        return {
            "total_documents": len(self.documents),
            "dimension": self.dimension,
            "memory_usage_mb": round(memory_mb, 2),
            "cache_path": self.cache_path,
            "similarity_threshold": self.similarity_threshold,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "avg_vector_magnitude": round(avg_magnitude, 4)  # ✅ NEW: Health metric
        }
    
    def clear(self) -> None:
        """Clear all data from vector store"""
        doc_count = len(self.documents)
        self.vectors = []
        self.metadata = []
        self.documents = []
        logger.info(f"🧹 Vector store cleared ({doc_count} documents removed)")
    
    def get_document(self, index: int) -> Optional[Dict[str, Any]]:
        """Get a specific document by index"""
        if 0 <= index < len(self.documents):
            return {
                "document": self.documents[index],
                "metadata": self.metadata[index],
                "vector": self.vectors[index].tolist()
            }
        return None
    
    def remove_documents(self, indices: List[int]) -> bool:
        """Remove documents by indices"""
        try:
            # Sort indices in reverse to avoid index shifting issues
            for idx in sorted(indices, reverse=True):
                if 0 <= idx < len(self.documents):
                    del self.documents[idx]
                    del self.metadata[idx]
                    del self.vectors[idx]
            
            logger.info(f"🗑️ Removed {len(indices)} documents from vector store")
            return True
            
        except Exception as e:
            logger.error(f"💥 Failed to remove documents: {str(e)}")
            return False
    
    # ✅ NEW: Add batch search for efficiency
    def batch_search(
        self,
        query_embeddings: List[List[float]],
        top_k: Optional[int] = None
    ) -> List[List[Dict[str, Any]]]:
        """
        Search for multiple queries at once (more efficient than multiple calls)
        
        Args:
            query_embeddings: List of query vectors
            top_k: Number of results per query
            
        Returns:
            List of result lists (one per query)
        """
        return [self.search(qe, top_k) for qe in query_embeddings]


class MathProblemVectorStore(VectorStore):
    """Specialized vector store for math problems with GSM8K support"""
    
    def __init__(self, dimension: Optional[int] = None):
        """
        Initialize the Math Problem Vector Store.
        
        Args:
            dimension: Embedding dimension (uses config default if None)
        """
        super().__init__(dimension)
        self.problem_types: Dict[str, int] = {}
        self.difficulty_counts: Dict[str, int] = {}  # ✅ NEW: Track difficulty distribution
        self.source_counts: Dict[str, int] = {}  # ✅ NEW: Track data sources
        
        # Track supported problem types from config
        self.supported_types = PROBLEM_TYPES
        logger.info(f"📐 Math Problem Vector Store initialized (supports {len(self.supported_types)} problem types)")
        # RAG evaluation tracking
        self.rag_usage_count = 0
        self.rag_similarity_scores = []
        self.rag_type_usage = {}

    def add_math_problems(
        self, 
        problems: List[Dict[str, Any]], 
        embeddings: List[List[float]]
    ) -> bool:
        """
        Add math problems to the vector store.
        Optimized for GSM8K format.
        
        Args:
            problems: List of problem dictionaries
            embeddings: List of embedding vectors
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Input validation
            if not problems:
                logger.warning("⚠️ No problems provided to add")
                return False
            
            if len(problems) != len(embeddings):
                logger.error(f"❌ Length mismatch: {len(problems)} problems, {len(embeddings)} embeddings")
                return False
            
            documents = []
            metadata = []
            valid_embeddings = []  # ✅ NEW: Track valid embeddings
            
            for i, problem in enumerate(problems):
                # Validate problem structure
                if not isinstance(problem, dict) or 'problem' not in problem:
                    logger.warning(f"⚠️ Skipping invalid problem at index {i}")
                    continue
                
                # ✅ ENHANCED: Create rich document text for better retrieval
                doc_text = f"Problem: {problem['problem']}"
                
                # Add solution if available (important for GSM8K)
                if problem.get('solution'):
                    # Limit solution length to avoid token overflow
                    solution = problem['solution']
                    if len(solution) > 500:
                        solution = solution[:500] + "..."
                    doc_text += f"\nSolution: {solution}"
                
                # Add answer for quick reference
                if problem.get('answer'):
                    doc_text += f"\nAnswer: {problem['answer']}"
                
                documents.append(doc_text)
                
                # Create comprehensive metadata
                prob_type = problem.get('type', 'word_problem')  # ✅ CHANGED: Better default
                
                # Validate problem type against config
                if prob_type not in self.supported_types:
                    logger.warning(f"⚠️ Unknown problem type '{prob_type}' at index {i}, using 'word_problem'")
                    prob_type = 'word_problem'
                
                difficulty = problem.get('difficulty', 'medium')
                source = problem.get('source', 'unknown')
                
                meta = {
                    "id": len(self.documents) + len(documents),  # Global ID
                    "problem": problem['problem'],
                    "solution": problem.get('solution', ''),
                    "answer": problem.get('answer', ''),
                    "type": prob_type,
                    "difficulty": difficulty,
                    "steps": problem.get('steps', []),
                    "tags": problem.get('tags', []),  # ✅ NEW: Support tags
                    "source": source  # ✅ NEW: Track data source (gsm8k, custom, etc.)
                }
                metadata.append(meta)
                valid_embeddings.append(embeddings[i])
                
                # Track statistics
                self.problem_types[prob_type] = self.problem_types.get(prob_type, 0) + 1
                self.difficulty_counts[difficulty] = self.difficulty_counts.get(difficulty, 0) + 1  # ✅ NEW
                self.source_counts[source] = self.source_counts.get(source, 0) + 1  # ✅ NEW
            
            # Only add if we have valid documents
            if not documents:
                logger.warning("⚠️ No valid problems to add after validation")
                return False
            
            # Add to base store
            result = self.add_documents(documents, metadata, valid_embeddings)
            
            if result:
                logger.info(f"✅ Added {len(documents)} math problems to vector store")
                logger.info(f"   Problem types: {dict(list(self.problem_types.items())[:5])}...")
                logger.info(f"   Difficulties: {self.difficulty_counts}")
                logger.info(f"   Sources: {self.source_counts}")
            
            return result
            
        except Exception as e:
            logger.error(f"💥 Failed to add math problems: {str(e)}", exc_info=True)
            return False
    
    def get_problem_types_stats(self) -> Dict[str, int]:
        """Get statistics about problem types"""
        return self.problem_types.copy()
    
    def search_by_type(
        self, 
        query_embedding: List[float], 
        problem_type: str, 
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar problems of a specific type.
        
        Args:
            query_embedding: Query vector
            problem_type: Type of problem to filter by
            top_k: Number of results to return
            
        Returns:
            List of similar problems of the specified type
        """
        # Validate problem type
        if problem_type not in self.supported_types:
            logger.warning(f"⚠️ Unknown problem type '{problem_type}'. Supported: {list(self.supported_types)[:5]}...")
        
        k = top_k or SYSTEM_CONFIG.get("top_k_retrieval", 5)
        
        # Get more results to allow for filtering (multiply by 3 for safety)
        all_results = self.search(query_embedding, top_k=k * 3, threshold=self.similarity_threshold * 0.8)  # ✅ CHANGED: Lower threshold for type search
        
        # Filter by problem type
        filtered_results = [
            result for result in all_results 
            if result.get('metadata', {}).get('type') == problem_type
        ]
        
        logger.info(f"🔍 Found {len(filtered_results)}/{len(all_results)} problems of type '{problem_type}'")
        return filtered_results[:k]
    
    def search_by_difficulty(
        self, 
        query_embedding: List[float], 
        difficulty: str, 
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar problems of a specific difficulty level"""
        k = top_k or SYSTEM_CONFIG.get("top_k_retrieval", 5)
        all_results = self.search(query_embedding, top_k=k * 2)
        
        filtered_results = [
            result for result in all_results 
            if result.get('metadata', {}).get('difficulty') == difficulty
        ]
        
        logger.info(f"🔍 Found {len(filtered_results)} problems of difficulty '{difficulty}'")
        return filtered_results[:k]
    
    # ✅ NEW: Search by source (e.g., get only GSM8K problems)
    def search_by_source(
        self,
        query_embedding: List[float],
        source: str,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar problems from a specific source (e.g., 'gsm8k', 'custom')"""
        k = top_k or SYSTEM_CONFIG.get("top_k_retrieval", 5)
        all_results = self.search(query_embedding, top_k=k * 2)
        
        filtered_results = [
            result for result in all_results
            if result.get('metadata', {}).get('source') == source
        ]
        
        logger.info(f"🔍 Found {len(filtered_results)} problems from source '{source}'")
        return filtered_results[:k]
    
    def get_random_problems(
        self, 
        count: int = 5, 
        problem_type: Optional[str] = None,
        difficulty: Optional[str] = None  # ✅ NEW: Filter by difficulty
    ) -> List[Dict[str, Any]]:
        """Get random problems from the store with optional filters"""
        try:
            if not self.documents:
                return []
            
            # Build filter criteria
            indices = []
            for i, meta in enumerate(self.metadata):
                # Type filter
                if problem_type and meta.get('type') != problem_type:
                    continue
                # Difficulty filter
                if difficulty and meta.get('difficulty') != difficulty:
                    continue
                indices.append(i)
            
            if not indices:
                logger.warning(f"⚠️ No problems match filters: type={problem_type}, difficulty={difficulty}")
                return []
            
            # Randomly sample
            sample_size = min(count, len(indices))
            sampled_indices = np.random.choice(indices, size=sample_size, replace=False)
            
            results = []
            for idx in sampled_indices:
                results.append({
                    "document": self.documents[idx],
                    "metadata": self.metadata[idx],
                    "index": int(idx)
                })
            
            logger.info(f"🎲 Retrieved {len(results)} random problems")
            return results
            
        except Exception as e:
            logger.error(f"💥 Failed to get random problems: {str(e)}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extended statistics including problem types, difficulty, source & RAG usage"""
        base_stats = super().get_stats()
        base_stats.update({
            "problem_types": self.problem_types,
            "difficulty_distribution": self.difficulty_counts,      # ✅ NEW
            "source_distribution": self.source_counts,              # ✅ NEW
            "supported_types": list(self.supported_types),          # ✅ CHANGED: Convert to list for JSON
            "unique_types_stored": len(self.problem_types),
            "rag_stats": {                                          # ✅ NEW BLOCK
                "usage_count": self.rag_usage_count,
                "avg_similarity": round(
                    np.mean(self.rag_similarity_scores), 3
                ) if self.rag_similarity_scores else 0.0,
                "usage_by_type": self.rag_type_usage
            }
        })
        return base_stats

    # ✅ NEW: Get problems that need review (low quality indicators)
    def get_problems_needing_review(self) -> List[Dict[str, Any]]:
        """Identify problems that might need review (e.g., missing solutions)"""
        problems_to_review = []
        
        for i, meta in enumerate(self.metadata):
            needs_review = False
            reason = []
            
            # Check for missing solution
            if not meta.get('solution'):
                needs_review = True
                reason.append("missing_solution")
            
            # Check for missing answer
            if not meta.get('answer'):
                needs_review = True
                reason.append("missing_answer")
            
            # Check for unknown type
            if meta.get('type') == 'unknown':
                needs_review = True
                reason.append("unknown_type")
            
            if needs_review:
                problems_to_review.append({
                    "index": i,
                    "problem": meta.get('problem', '')[:100],
                    "reasons": reason,
                    "metadata": meta
                })
        
        logger.info(f"📋 Found {len(problems_to_review)} problems needing review")
        return problems_to_review
