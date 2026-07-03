# backend/utils/data_processor.py
"""
Data Processor for loading and managing math problems and solutions
PRO VERSION (Sri build):
- Smart-relative paths (works even if run from elsewhere)
- Auto-repair corrupted JSON (reset only if corrupted)
- Merge + dedupe with safety checks
- Versioned backups on each successful write
- Max DB size = 5000 with auto-archive of older entries
- Friendly emoji logging

Compatible with Meta-Agent Math Debate System.
"""

import json
import csv
import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# -----------------------------------------------------------------------------
# Logging (emoji-friendly)
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Smart project root resolution (Option S)
# -----------------------------------------------------------------------------
def _detect_project_root() -> str:
    """
    Detect project root robustly:
    - If we find a 'backend' folder up the chain, use that as root of backend.
    - Otherwise, use two levels up from this file.
    """
    here = os.path.abspath(os.path.dirname(__file__))
    cur = here
    # Walk up to find "backend" folder (expected structure)
    for _ in range(6):
        base = os.path.basename(cur)
        if base.lower() == "backend":
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    # Fallback: 2 levels up from this file
    fallback = os.path.abspath(os.path.join(here, ".."))
    return fallback

PROJECT_ROOT = _detect_project_root()

# Make sure project root is on sys.path so `config` resolves
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Now we can import config items
from config import SYSTEM_CONFIG, PROBLEM_TYPES  # type: ignore


def _resolve_smart_path(config_path: str, default_rel_path: str) -> str:
    """
    Resolve paths smartly:
    - If config_path is absolute, return it.
    - If config_path is relative (or missing), join with PROJECT_ROOT.
    - If config_path missing, use default_rel_path under PROJECT_ROOT.
    """
    if config_path and os.path.isabs(config_path):
        return config_path
    base_rel = config_path if config_path else default_rel_path
    return os.path.abspath(os.path.join(PROJECT_ROOT, base_rel))


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


class DataProcessor:
    """Handles loading, processing, and managing math problem data"""

    # ---- Pro settings (your picks) ----
    MAX_DB_RECORDS = 5000  # (Q3=A)
    CREATE_VERSIONED_BACKUP = True  # (Q2=C)
    RESET_ONLY_IF_CORRUPTED = True  # (Q1=D)

    def __init__(self):
        """Initialize the Data Processor with configuration from .env"""
        logger.info("=" * 70)
        logger.info("📊 DataProcessor.__init__() called")
        logger.info("=" * 70)

        # Load raw config paths
        raw_problems_path = SYSTEM_CONFIG.get("problems_db_path", "./data/math_problems.json")
        raw_solutions_path = SYSTEM_CONFIG.get("solutions_db_path", "./database/solutions.csv")

        # Smart-resolve paths (Option S)
        self.problems_db_path = _resolve_smart_path(raw_problems_path, "./data/math_problems.json")
        self.solutions_db_path = _resolve_smart_path(raw_solutions_path, "./database/solutions.csv")

        # Derived locations
        self.archive_dir = os.path.abspath(os.path.join(PROJECT_ROOT, "database", "archives"))
        os.makedirs(self.archive_dir, exist_ok=True)

        self.sample_problems: List[Dict[str, Any]] = []

        # Track statistics
        self.problems_loaded = 0
        self.solutions_saved = 0

        logger.info(f"   📁 Problems DB: {self.problems_db_path}")
        logger.info(f"   📁 Solutions DB: {self.solutions_db_path}")
        logger.info("=" * 70 + "\n")
        
        sample_problems = self.load_sample_data()
        logger.info("✅ Loaded %d sample problems", len(sample_problems))

        # ✅ FIX: Auto-populate DB if empty
        if not os.path.exists(self.problems_db_path) or os.path.getsize(self.problems_db_path) < 5:
            logger.warning("📌 Problems DB empty → Saving sample problems...")
            self.save_problems(sample_problems)
    # -------------------------------------------------------------------------
    # Sample dataset loader
    # -------------------------------------------------------------------------
    def load_sample_data(self) -> bool:
        """
        Load sample math problems for testing and demonstration.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("📚 Loading sample math problems...")

            # Create sample GSM8K-style problems
            sample_data = [
                {
                    "problem": "A bakery sells cupcakes for $3 each. If Sarah buys 8 cupcakes and pays with a $50 bill, how much change will she receive?",
                    "solution": "First, calculate the total cost: 8 cupcakes × $3 = $24. Then, calculate the change: $50 - $24 = $26.",
                    "answer": "26",
                    "type": "money",
                    "difficulty": "easy",
                    "steps": [
                        "Calculate total cost: 8 × $3 = $24",
                        "Calculate change: $50 - $24 = $26"
                    ]
                },
                {
                    "problem": "A rectangular garden is 12 meters long and 8 meters wide. What is the perimeter of the garden?",
                    "solution": "The perimeter of a rectangle is 2 × (length + width). So the perimeter is 2 × (12 + 8) = 2 × 20 = 40 meters.",
                    "answer": "40",
                    "type": "geometry",
                    "difficulty": "easy",
                    "steps": [
                        "Use perimeter formula: P = 2(l + w)",
                        "Substitute values: P = 2(12 + 8)",
                        "Calculate: P = 2 × 20 = 40 meters"
                    ]
                },
                {
                    "problem": "Tom has 24 marbles. He gives 1/3 of them to his friend and 1/4 of the remaining marbles to his sister. How many marbles does Tom have left?",
                    "solution": "First, Tom gives 1/3 of 24 = 8 marbles to his friend. He has 24 - 8 = 16 marbles left. Then he gives 1/4 of 16 = 4 marbles to his sister. Tom has 16 - 4 = 12 marbles left.",
                    "answer": "12",
                    "type": "fractions",
                    "difficulty": "medium",
                    "steps": [
                        "Calculate 1/3 of 24: 24 ÷ 3 = 8",
                        "Remaining after friend: 24 - 8 = 16",
                        "Calculate 1/4 of 16: 16 ÷ 4 = 4",
                        "Final remaining: 16 - 4 = 12"
                    ]
                },
                {
                    "problem": "A car travels at 60 mph for 2.5 hours. How far does the car travel?",
                    "solution": "Distance = Speed × Time. Distance = 60 mph × 2.5 hours = 150 miles.",
                    "answer": "150",
                    "type": "time_distance",
                    "difficulty": "easy",
                    "steps": [
                        "Use formula: Distance = Speed × Time",
                        "Substitute values: Distance = 60 × 2.5",
                        "Calculate: Distance = 150 miles"
                    ]
                },
                {
                    "problem": "The sum of two consecutive even numbers is 46. What are the two numbers?",
                    "solution": "Let the first even number be x, then the next even number is x + 2. So x + (x + 2) = 46, which gives 2x + 2 = 46. Solving: 2x = 44, so x = 22. The two numbers are 22 and 24.",
                    "answer": "22 and 24",
                    "type": "algebra",
                    "difficulty": "hard",
                    "steps": [
                        "Let first number be x, second be x + 2",
                        "Set up equation: x + (x + 2) = 46",
                        "Simplify: 2x + 2 = 46",
                        "Solve: 2x = 44, so x = 22",
                        "The numbers are 22 and 24"
                    ]
                },
                {
                    "problem": "A pizza is cut into 8 equal slices. If 3 people eat 2 slices each, what fraction of the pizza is left?",
                    "solution": "Total slices eaten: 3 people × 2 slices = 6 slices. Slices remaining: 8 - 6 = 2 slices. Fraction remaining: 2/8 = 1/4.",
                    "answer": "1/4",
                    "type": "fractions",
                    "difficulty": "medium",
                    "steps": [
                        "Calculate slices eaten: 3 × 2 = 6",
                        "Calculate remaining: 8 - 6 = 2",
                        "Convert to fraction: 2/8 = 1/4"
                    ]
                },
                {
                    "problem": "A store offers a 20% discount on a jacket that originally costs $80. What is the final price after the discount?",
                    "solution": "The discount amount is 20% of $80 = 0.20 × $80 = $16. The final price is $80 - $16 = $64.",
                    "answer": "64",
                    "type": "percentage",
                    "difficulty": "easy",
                    "steps": [
                        "Calculate discount: 20% of $80 = 0.20 × $80 = $16",
                        "Subtract discount: $80 - $16 = $64"
                    ]
                },
                {
                    "problem": "In a class of 30 students, 18 are girls. What percentage of the class are boys?",
                    "solution": "Number of boys = 30 - 18 = 12. Percentage of boys = (12/30) × 100% = 0.4 × 100% = 40%.",
                    "answer": "40",
                    "type": "percentage",
                    "difficulty": "medium",
                    "steps": [
                        "Calculate number of boys: 30 - 18 = 12",
                        "Calculate percentage: (12/30) × 100%",
                        "Simplify: 0.4 × 100% = 40%"
                    ]
                },
                {
                    "problem": "A triangle has sides of length 3 cm, 4 cm, and 5 cm. What is its area?",
                    "solution": "This is a right triangle (3² + 4² = 5²). Area = (1/2) × base × height = (1/2) × 3 × 4 = 6 cm².",
                    "answer": "6",
                    "type": "geometry",
                    "difficulty": "medium",
                    "steps": [
                        "Recognize right triangle: 3² + 4² = 5²",
                        "Use area formula: A = (1/2) × base × height",
                        "Calculate: A = (1/2) × 3 × 4 = 6 cm²"
                    ]
                },
                {
                    "problem": "A coin is flipped 3 times. What is the probability of getting exactly 2 heads?",
                    "solution": "Total outcomes: 2³ = 8. Favorable outcomes (exactly 2 heads): HHT, HTH, THH = 3. Probability = 3/8 = 0.375.",
                    "answer": "3/8",
                    "type": "probability",
                    "difficulty": "hard",
                    "steps": [
                        "Calculate total outcomes: 2³ = 8",
                        "List favorable outcomes: HHT, HTH, THH",
                        "Count favorable: 3 outcomes",
                        "Calculate probability: 3/8"
                    ]
                }
            ]

            # Validate all sample problems
            valid_problems = []
            invalid_count = 0

            for i, problem in enumerate(sample_data):
                if self.validate_problem_data(problem):
                    valid_problems.append(problem)
                else:
                    invalid_count += 1
                    logger.warning(f"⚠️ Sample problem {i} failed validation")

            if invalid_count > 0:
                logger.warning(f"⚠️ {invalid_count} problems failed validation")

            self.sample_problems = valid_problems
            self.problems_loaded = len(valid_problems)

            logger.info(f"✅ Loaded {len(self.sample_problems)} sample problems")

            # Log problem distribution
            stats = self.get_problem_statistics()
            logger.info(f"   By type: {stats['by_type']}")
            logger.info(f"   By difficulty: {stats['by_difficulty']}")

            # Try to save to database file (merge + dedupe, heal if corrupted)
            try:
                self.save_problems_to_file(valid_problems)
            except Exception as e:
                logger.warning(f"⚠️ Could not save to file: {str(e)}")

            return self.sample_problems

        except Exception as e:
            logger.error(f"💥 Failed to load sample data: {str(e)}", exc_info=True)
            return []

    def get_sample_problems(self) -> List[Dict[str, Any]]:
        """Get all sample problems"""
        logger.debug(f"get_sample_problems() called, returning {len(self.sample_problems)} problems")
        return self.sample_problems.copy()

    def get_problems_by_type(self, problem_type: str) -> List[Dict[str, Any]]:
        """Get problems filtered by type."""
        if problem_type not in PROBLEM_TYPES:
            logger.warning(f"⚠️ Unknown problem type: {problem_type}. Valid: {PROBLEM_TYPES}")

        filtered = [p for p in self.sample_problems if p.get("type") == problem_type]
        logger.info(f"🔍 Found {len(filtered)} problems of type '{problem_type}'")
        return filtered

    def get_problems_by_difficulty(self, difficulty: str) -> List[Dict[str, Any]]:
        """Get problems filtered by difficulty."""
        valid_difficulties = ['easy', 'medium', 'hard']
        if difficulty not in valid_difficulties:
            logger.warning(f"⚠️ Unknown difficulty: {difficulty}. Valid: {valid_difficulties}")

        filtered = [p for p in self.sample_problems if p.get("difficulty") == difficulty]
        logger.info(f"🔍 Found {len(filtered)} problems with difficulty '{difficulty}'")
        return filtered

    # -------------------------------------------------------------------------
    # PRO Save (merge + dedupe + heal + backup + archive)
    # -------------------------------------------------------------------------
    def _load_existing_safe(self) -> List[Dict[str, Any]]:
        """
        Load existing problems safely:
        - If file missing: return []
        - If corrupted and RESET_ONLY_IF_CORRUPTED: return [] (and log)
        - If dict: wrap as list
        - If list with mixed junk: filter to dicts only
        """
        if not os.path.exists(self.problems_db_path):
            logger.info(f"📁 File not found: {self.problems_db_path} (will create new)")
            return []

        try:
            with open(self.problems_db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            if self.RESET_ONLY_IF_CORRUPTED:
                logger.warning(f"🧯 Corrupted JSON detected. Auto-resetting DB. Reason: {e}")
                return []
            else:
                raise

        # Normalize to list of dicts
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            logger.warning("⚠️ Existing problems file not a list. Resetting to empty.")
            return []

        cleaned: List[Dict[str, Any]] = []
        bad = 0
        for i, item in enumerate(data):
            if isinstance(item, dict) and "problem" in item:
                cleaned.append(item)
            else:
                bad += 1
        if bad:
            logger.warning(f"🧹 Cleaned out {bad} invalid record(s) from existing DB")
        return cleaned

    def _backup_current_db(self) -> None:
        """Create a versioned backup of the current DB (if it exists)."""
        if not os.path.exists(self.problems_db_path):
            return
        if not self.CREATE_VERSIONED_BACKUP:
            return
        ts = _timestamp()
        base = f"math_problems_{ts}.json"
        dest = os.path.join(self.archive_dir, base)
        try:
            os.makedirs(self.archive_dir, exist_ok=True)
            with open(self.problems_db_path, 'r', encoding='utf-8') as src, open(dest, 'w', encoding='utf-8') as out:
                out.write(src.read())
            logger.info(f"🗂️ Backup created: {dest}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to create backup: {e}")

    def _archive_excess(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        If records exceed MAX_DB_RECORDS, archive the oldest tail and keep the newest MAX.
        Assumes records order: existing first, then newly appended.
        """
        if len(records) <= self.MAX_DB_RECORDS:
            return records

        ts = _timestamp()
        archive_name = os.path.join(self.archive_dir, f"math_problems_archive_{ts}.json")
        try:
            os.makedirs(self.archive_dir, exist_ok=True)
            excess = records[:-self.MAX_DB_RECORDS]  # older items to archive
            with open(archive_name, 'w', encoding='utf-8') as f:
                json.dump(excess, f, indent=2, ensure_ascii=False)
            logger.info(f"📦 Archived {len(excess)} older problem(s) → {archive_name}")
            kept = records[-self.MAX_DB_RECORDS:]  # keep most recent
            return kept
        except Exception as e:
            logger.warning(f"⚠️ Failed to archive excess records: {e}")
            # If archiving fails, still enforce the cap by keeping newest
            return records[-self.MAX_DB_RECORDS:]

    def overwrite_problems_file(self, problems: List[Dict[str, Any]]) -> bool:
        """Overwrite the problems database file with a completely new list of problems (bypassing merge/dedupe)."""
        try:
            logger.info(f"💾 Overwriting problems database with {len(problems)} new records...")
            os.makedirs(os.path.dirname(self.problems_db_path), exist_ok=True)

            self._backup_current_db()
            capped_problems = self._archive_excess(problems)

            with open(self.problems_db_path, 'w', encoding='utf-8') as f:
                json.dump(capped_problems, f, indent=2, ensure_ascii=False)

            self.sample_problems = capped_problems
            self.problems_loaded = len(capped_problems)
            logger.info(f"✅ Database overwritten successfully (active size: {len(capped_problems)})")
            return True
        except Exception as e:
            logger.error(f"💥 Failed to overwrite problems database: {str(e)}", exc_info=True)
            return False

    def save_problems_to_file(self, problems: List[Dict[str, Any]]) -> bool:
        """Save problems to JSON file safely (handles bad data, dict/list cases, backups, cap)."""
        try:
            logger.info(f"💾 Saving {len(problems)} problems to {self.problems_db_path}...")

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.problems_db_path), exist_ok=True)

            existing = self._load_existing_safe()
            logger.debug(f"   Loaded {len(existing)} existing valid problems")

            # Build set of existing problem texts (normalized)
            existing_set = {
                (p.get('problem', '').strip() or f"__idx_{i}")
                for i, p in enumerate(existing)
                if isinstance(p, dict)
            }

            # Filter + normalize incoming problems
            incoming: List[Dict[str, Any]] = []
            bad_new = 0
            for item in problems:
                if not isinstance(item, dict):
                    bad_new += 1
                    continue
                txt = item.get('problem', '')
                if not isinstance(txt, str) or not txt.strip():
                    bad_new += 1
                    continue
                norm = txt.strip()
                if norm in existing_set:
                    continue
                incoming.append(item)

            if bad_new:
                logger.warning(f"🧹 Skipped {bad_new} invalid incoming problem(s)")

            # Merge
            merged = existing + incoming

            # Enforce size cap with archive
            merged_capped = self._archive_excess(merged)

            # Backup current DB (before overwrite)
            self._backup_current_db()

            # Write out
            with open(self.problems_db_path, 'w', encoding='utf-8') as f:
                json.dump(merged_capped, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Saved {len(incoming)} new problems (total now: {len(merged_capped)})")
            return True

        except Exception as e:
            logger.error(f"💥 Failed to save problems: {str(e)}", exc_info=True)
            return False

    # -------------------------------------------------------------------------
    # Loaders / CSV I/O
    # -------------------------------------------------------------------------
    def load_problems_from_file(self) -> List[Dict[str, Any]]:
        """Load problems from JSON file."""
        try:
            if not os.path.exists(self.problems_db_path):
                logger.info(f"📁 File not found: {self.problems_db_path}, using sample data")
                return self.sample_problems

            logger.info(f"📂 Loading from {self.problems_db_path}...")

            with open(self.problems_db_path, 'r', encoding='utf-8') as f:
                problems = json.load(f)

            # Normalize & validate
            if isinstance(problems, dict):
                problems = [problems]
            if not isinstance(problems, list):
                logger.warning("⚠️ Problems file not a list. Falling back to sample data.")
                return self.sample_problems

            valid_problems = []
            for i, problem in enumerate(problems):
                if isinstance(problem, dict) and self.validate_problem_data(problem):
                    valid_problems.append(problem)
                else:
                    logger.warning(f"⚠️ Problem {i} failed validation")

            logger.info(f"✅ Loaded {len(valid_problems)} valid problems from file")
            return valid_problems

        except Exception as e:
            logger.error(f"💥 Failed to load from file: {str(e)}", exc_info=True)
            return self.sample_problems

    def save_solution_to_csv(self, problem: str, solution_data: Dict[str, Any]) -> bool:
        """Save a solution to CSV file."""
        try:
            logger.debug(f"💾 Saving solution to {self.solutions_db_path}...")

            # Create directory if needed
            os.makedirs(os.path.dirname(self.solutions_db_path), exist_ok=True)

            # Add timestamp if not provided
            if 'timestamp' not in solution_data or not solution_data['timestamp']:
                solution_data['timestamp'] = datetime.now().isoformat()

            # Prepare CSV row
            row_data = {
                "timestamp": solution_data.get("timestamp", ""),
                "problem": (problem or "")[:200],
                "solution": solution_data.get("solution", "")[:500],
                "answer": solution_data.get("answer", ""),
                "confidence": solution_data.get("confidence", 0.0),
                "best_agent": solution_data.get("best_agent", ""),
                "total_time": solution_data.get("total_time", 0.0),
                "problem_type": solution_data.get("problem_type", "unknown")
            }

            # Check if file exists
            file_exists = os.path.exists(self.solutions_db_path)

            with open(self.solutions_db_path, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = list(row_data.keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()

                writer.writerow(row_data)

            self.solutions_saved += 1
            logger.debug(f"✅ Solution saved (total: {self.solutions_saved})")
            return True

        except Exception as e:
            logger.error(f"💥 Failed to save solution: {str(e)}", exc_info=True)
            return False

    def load_solutions_from_csv(self) -> List[Dict[str, Any]]:
        """Load solutions from CSV file."""
        try:
            if not os.path.exists(self.solutions_db_path):
                logger.debug(f"📁 CSV not found: {self.solutions_db_path}")
                return []

            logger.info(f"📂 Loading solutions from {self.solutions_db_path}...")

            solutions = []
            with open(self.solutions_db_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        row['confidence'] = float(row.get('confidence', 0.0))
                        row['total_time'] = float(row.get('total_time', 0.0))
                    except ValueError:
                        row['confidence'] = 0.0
                        row['total_time'] = 0.0
                    solutions.append(row)

            logger.info(f"✅ Loaded {len(solutions)} solutions")
            return solutions

        except Exception as e:
            logger.error(f"💥 Failed to load solutions: {str(e)}", exc_info=True)
            return []

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------
    def create_problem_from_text(
        self,
        problem_text: str,
        problem_type: Optional[str] = None,
        difficulty: str = "medium"
    ) -> Dict[str, Any]:
        """Create a problem dictionary from text."""
        if problem_type is None:
            problem_type = self._detect_problem_type(problem_text)

        if problem_type not in PROBLEM_TYPES:
            logger.warning(f"⚠️ Unknown type '{problem_type}', using 'word_problem'")
            problem_type = "word_problem"

        return {
            "problem": problem_text,
            "solution": "",
            "answer": "",
            "type": problem_type,
            "difficulty": difficulty,
            "steps": []
        }

    def _detect_problem_type(self, problem_text: str) -> str:
        """Auto-detect problem type from text."""
        text_lower = problem_text.lower()

        if any(word in text_lower for word in ['$', 'dollar', 'cost', 'price', 'payment']):
            return 'money'
        elif any(word in text_lower for word in ['area', 'perimeter', 'volume', 'triangle', 'circle']):
            return 'geometry'
        elif any(word in text_lower for word in ['fraction', '1/2', '1/3', '1/4', 'half', 'quarter']):
            return 'fractions'
        elif any(word in text_lower for word in ['%', 'percent', 'percentage']):
            return 'percentage'
        elif any(word in text_lower for word in ['speed', 'distance', 'time', 'mph', 'hours']):
            return 'time_distance'
        elif any(word in text_lower for word in ['probability', 'chance', 'odds', 'likely']):
            return 'probability'
        elif any(word in text_lower for word in ['equation', 'solve for', 'x =', 'variable']):
            return 'algebra'
        else:
            return 'word_problem'

    def validate_problem_data(self, problem_data: Dict[str, Any]) -> bool:
        """Validate problem data structure."""
        required_fields = ["problem", "type"]

        for field in required_fields:
            if field not in problem_data or not problem_data[field]:
                return False

        if len(problem_data["problem"]) < 10:
            return False

        return True

    def get_problem_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded problems."""
        problems = self.sample_problems

        if not problems:
            return {
                "total_problems": 0,
                "by_type": {},
                "by_difficulty": {},
                "average_steps": 0
            }

        # Count by type
        type_counts: Dict[str, int] = {}
        for problem in problems:
            ptype = problem.get("type", "unknown")
            type_counts[ptype] = type_counts.get(ptype, 0) + 1

        # Count by difficulty
        difficulty_counts: Dict[str, int] = {}
        for problem in problems:
            difficulty = problem.get("difficulty", "medium")
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1

        # Calculate statistics
        avg_steps = sum(len(p.get("steps", [])) for p in problems) / len(problems)
        avg_length = sum(len(p.get("problem", "")) for p in problems) / len(problems)

        return {
            "total_problems": len(problems),
            "by_type": type_counts,
            "by_difficulty": difficulty_counts,
            "average_steps": round(avg_steps, 2),
            "average_problem_length": round(avg_length, 0),
            "problems_loaded": self.problems_loaded,
            "solutions_saved": self.solutions_saved
        }

    def export_problems_to_csv(self, output_path: str) -> bool:
        """Export problems to CSV format."""
        try:
            problems = self.sample_problems

            if not problems:
                logger.warning("⚠️ No problems to export")
                return False

            logger.info(f"📤 Exporting {len(problems)} problems to {output_path}...")

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ["problem", "solution", "answer", "type", "difficulty", "steps"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for problem in problems:
                    problem_copy = problem.copy()
                    if "steps" in problem_copy and isinstance(problem_copy["steps"], list):
                        problem_copy["steps"] = "; ".join(problem_copy["steps"])
                    writer.writerow(problem_copy)

            logger.info(f"✅ Exported to {output_path}")
            return True

        except Exception as e:
            logger.error(f"💥 Export failed: {str(e)}", exc_info=True)
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the data processor"""
        return {
            "problems_loaded": self.problems_loaded,
            "solutions_saved": self.solutions_saved,
            "problems_db_path": self.problems_db_path,
            "solutions_db_path": self.solutions_db_path,
            "sample_problems_count": len(self.sample_problems)
        }

    def cleanup(self):
        """Cleanup resources"""
        logger.debug("🧹 DataProcessor cleanup")
