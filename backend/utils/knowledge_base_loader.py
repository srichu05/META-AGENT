"""
Knowledge Base Loader for RAG System
Supports: Custom JSON, GSM8K, CSV
"""

# TODO(Draft 2): GSM8K loading is legacy-only. Future ingestion accepts user
# documents and must not use GSM8K as the primary knowledge source.

import json
import csv
import os
import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class KnowledgeBaseLoader:
    """Loads and processes math problem knowledge bases from various sources"""
    
    def __init__(self):
        self.problems: List[Dict[str, Any]] = []
        self.sources_loaded: List[str] = []
        logger.info("📚 Knowledge Base Loader initialized")
    
    def load_from_json(self, file_path: str) -> List[Dict[str, Any]]:
        """Load problems from standard JSON file"""
        try:
            logger.info(f"📂 Loading from JSON: {file_path}")
            
            if not os.path.exists(file_path):
                logger.error(f"❌ File not found: {file_path}")
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                problems = data
            elif isinstance(data, dict) and 'problems' in data:
                problems = data['problems']
            else:
                logger.error("❌ Unexpected JSON structure")
                return []
            
            valid_problems = []
            for i, problem in enumerate(problems):
                if self._validate_problem(problem):
                    normalized = self._normalize_problem(problem)
                    valid_problems.append(normalized)
                else:
                    logger.warning(f"⚠️ Invalid problem at index {i}")
            
            self.problems.extend(valid_problems)
            self.sources_loaded.append(file_path)
            logger.info(f"✅ Loaded {len(valid_problems)} problems from JSON")
            
            return valid_problems
            
        except Exception as e:
            logger.error(f"💥 Failed to load JSON: {str(e)}", exc_info=True)
            return []
    
    def load_gsm8k(self, file_path: str, max_problems: Optional[int] = None) -> List[Dict[str, Any]]:
        """Load problems from GSM8K dataset (JSONL format)"""
        try:
            logger.info(f"📂 Loading GSM8K from: {file_path}")
            
            if not os.path.exists(file_path):
                logger.error(f"❌ File not found: {file_path}")
                return []
            
            problems = []
            line_count = 0
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line_count += 1
                    
                    if max_problems and len(problems) >= max_problems:
                        logger.info(f"   Reached limit of {max_problems} problems")
                        break
                    
                    try:
                        data = json.loads(line.strip())
                        
                        question = data.get('question', '')
                        answer_text = data.get('answer', '')
                        
                        final_answer = self._extract_gsm8k_answer(answer_text)
                        problem_type = self._detect_problem_type(question)
                        steps = self._extract_gsm8k_steps(answer_text)
                        
                        problem = {
                            'id': len(self.problems) + len(problems) + 1,
                            'problem': question,
                            'solution': answer_text,
                            'answer': final_answer,
                            'type': problem_type,
                            'difficulty': 'medium',
                            'steps': steps,
                            'tags': self._extract_tags(question),
                            'source': 'gsm8k'
                        }
                        
                        if self._validate_problem(problem):
                            problems.append(problem)
                        
                    except json.JSONDecodeError:
                        logger.warning(f"⚠️ Invalid JSON at line {line_count}")
                        continue
                    except Exception as e:
                        logger.warning(f"⚠️ Error at line {line_count}: {str(e)}")
                        continue
            
            self.problems.extend(problems)
            self.sources_loaded.append(file_path)
            logger.info(f"✅ Loaded {len(problems)} problems from GSM8K")
            
            return problems
            
        except Exception as e:
            logger.error(f"💥 Failed to load GSM8K: {str(e)}", exc_info=True)
            return []
    
    def load_multiple_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Load from multiple sources"""
        all_problems = []
        
        logger.info(f"\n📚 Loading from {len(sources)} source(s)...")
        
        for idx, source in enumerate(sources):
            path = source.get('path', '')
            format_type = source.get('format', 'json').lower()
            max_problems = source.get('max_problems', None)
            
            logger.info(f"\n   Source {idx + 1}/{len(sources)}: {os.path.basename(path)}")
            
            if format_type == 'json':
                problems = self.load_from_json(path)
            elif format_type == 'gsm8k':
                problems = self.load_gsm8k(path, max_problems)
            else:
                logger.warning(f"   ⚠️ Unknown format: {format_type}")
                continue
            
            all_problems.extend(problems)
        
        logger.info(f"\n✅ Total problems loaded: {len(all_problems)}")
        return all_problems
    
    def _extract_gsm8k_answer(self, answer_text: str) -> str:
        """Extract final numerical answer from GSM8K solution"""
        if '####' in answer_text:
            final = answer_text.split('####')[-1].strip()
            final = re.sub(r'[^\d.-]', '', final)
            return final
        
        numbers = re.findall(r'-?\d+\.?\d*', answer_text)
        return numbers[-1] if numbers else ''
    
    def _extract_gsm8k_steps(self, answer_text: str) -> List[str]:
        """Extract calculation steps from GSM8K solution"""
        lines = [line.strip() for line in answer_text.split('\n') if line.strip()]
        steps = [line for line in lines if not line.startswith('####')]
        return steps
    
    def _detect_problem_type(self, problem_text: str) -> str:
        """Auto-detect problem type from text"""
        text_lower = problem_text.lower()
        
        type_keywords = {
            'money': ['$', 'dollar', 'cost', 'price', 'payment', 'buy', 'sell', 'spend', 'paid'],
            'geometry': ['area', 'perimeter', 'volume', 'triangle', 'circle', 'rectangle', 'square'],
            'fractions': ['fraction', '1/2', '1/3', '1/4', 'half', 'quarter', 'third'],
            'percentage': ['%', 'percent', 'percentage', 'discount', 'off'],
            'time_distance': ['speed', 'distance', 'time', 'mph', 'hours', 'travel', 'miles'],
            'probability': ['probability', 'chance', 'odds', 'likely', 'dice', 'coin'],
            'algebra': ['equation', 'solve for', 'x =', 'variable', 'unknown']
        }
        
        for ptype, keywords in type_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return ptype
        
        return 'word_problem'
    
    def _extract_tags(self, problem_text: str) -> List[str]:
        """Extract relevant tags from problem text"""
        tags = []
        text_lower = problem_text.lower()
        
        concepts = ['addition', 'subtraction', 'multiplication', 'division', 
                   'fraction', 'percentage', 'ratio', 'proportion', 'average',
                   'money', 'time', 'distance', 'geometry']
        
        for concept in concepts:
            if concept in text_lower:
                tags.append(concept)
        
        return tags[:5]
    
    def _validate_problem(self, problem: Dict[str, Any]) -> bool:
        """Validate problem has required fields"""
        if 'problem' not in problem or not problem['problem']:
            return False
        if len(problem.get('problem', '')) < 10:
            return False
        return True
    
    def _normalize_problem(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize problem to consistent format"""
        return {
            'id': problem.get('id', 0),
            'problem': problem.get('problem', ''),
            'solution': problem.get('solution', ''),
            'answer': problem.get('answer', ''),
            'type': problem.get('type', 'word_problem'),
            'difficulty': problem.get('difficulty', 'medium'),
            'steps': problem.get('steps', []),
            'tags': problem.get('tags', []),
            'source': problem.get('source', 'unknown')
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics about loaded knowledge base"""
        if not self.problems:
            return {"total": 0}
        
        types = {}
        difficulties = {}
        sources = {}
        
        for problem in self.problems:
            ptype = problem.get('type', 'unknown')
            types[ptype] = types.get(ptype, 0) + 1
            
            diff = problem.get('difficulty', 'medium')
            difficulties[diff] = difficulties.get(diff, 0) + 1
            
            source = problem.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        return {
            "total": len(self.problems),
            "by_type": types,
            "by_difficulty": difficulties,
            "by_source": sources,
            "sources_loaded": self.sources_loaded
        }
    
    def get_all_problems(self) -> List[Dict[str, Any]]:
        """Get all loaded problems"""
        return self.problems.copy()
    
    def clear(self):
        """Clear all loaded problems"""
        count = len(self.problems)
        self.problems = []
        self.sources_loaded = []
        logger.info(f"🧹 Cleared {count} problems from loader")
