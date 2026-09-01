"""Controlled GSM8K Benchmark Dataset Loader for Meta-Agent Math Debate System."""

from typing import List, Optional

from .types import BenchmarkItem

# Curated, reproducible GSM8K math problem subset with reference answers
GSM8K_SUBSET: List[BenchmarkItem] = [
    BenchmarkItem(
        question_id="gsm8k_001",
        question="Natalia sold clips to 48 of her friends in April, and then she sold half as many clips in May. How many clips did Natalia sell altogether in April and May?",
        reference_answer="72",
        expected_context="April sales: 48 clips. May sales: 48 / 2 = 24 clips. Total sales: 48 + 24 = 72 clips.",
        category="arithmetic",
        difficulty="easy",
    ),
    BenchmarkItem(
        question_id="gsm8k_002",
        question="Weng earns $12 an hour for babysitting. Yesterday, she babysat for 5 hours. Yesterday, she also earned $15 for walking dogs. How much money did Weng earn altogether yesterday?",
        reference_answer="75",
        expected_context="Babysitting earnings: 5 hours * $12/hour = $60. Dog walking earnings: $15. Total earnings: $60 + $15 = $75.",
        category="word_problem",
        difficulty="easy",
    ),
    BenchmarkItem(
        question_id="gsm8k_003",
        question="Solve for x in the linear equation: 4x - 12 = 28.",
        reference_answer="10",
        expected_context="Linear equation isolation: Add 12 to both sides -> 4x = 40. Divide by 4 -> x = 10.",
        category="algebra",
        difficulty="medium",
    ),
    BenchmarkItem(
        question_id="gsm8k_004",
        question="Betty is saving money for a new phone that costs $120. She has $40 already and earns $10 per week doing chores. How many weeks will it take Betty to save enough money to buy the phone?",
        reference_answer="8",
        expected_context="Remaining amount needed: $120 - $40 = $80. Weeks needed: $80 / $10/week = 8 weeks.",
        category="money",
        difficulty="easy",
    ),
    BenchmarkItem(
        question_id="gsm8k_005",
        question="A rectangle has a length of 15 cm and a width of 8 cm. What is the area and perimeter of the rectangle?",
        reference_answer="Area = 120 cm^2, Perimeter = 46 cm",
        expected_context="Area formula: Length * Width = 15 * 8 = 120. Perimeter formula: 2 * (Length + Width) = 2 * (15 + 8) = 46.",
        category="geometry",
        difficulty="medium",
    ),
    BenchmarkItem(
        question_id="gsm8k_006",
        question="Janet’s ducks lay 16 eggs per day. She eats 3 for breakfast every morning and uses 4 each day to bake muffins. She sells the remainder at the farmers' market every day for $2 per egg. How much money does she make every day at the farmers' market?",
        reference_answer="18",
        expected_context="Eggs eaten or baked: 3 + 4 = 7. Eggs remaining: 16 - 7 = 9. Money earned: 9 eggs * $2/egg = $18.",
        category="word_problem",
        difficulty="medium",
    ),
    BenchmarkItem(
        question_id="gsm8k_007",
        question="A store offers a 20% discount on a jacket originally priced at $80. What is the final sale price of the jacket after discount?",
        reference_answer="64",
        expected_context="Discount amount: 20% of $80 = 0.20 * 80 = $16. Final price: $80 - $16 = $64.",
        category="percentage",
        difficulty="easy",
    ),
    BenchmarkItem(
        question_id="gsm8k_008",
        question="A train travels at a constant speed of 60 miles per hour. How far will the train travel in 3 hours and 30 minutes?",
        reference_answer="210",
        expected_context="Time in hours: 3 + 30/60 = 3.5 hours. Distance formula: Speed * Time = 60 mph * 3.5 hours = 210 miles.",
        category="time_distance",
        difficulty="medium",
    ),
    BenchmarkItem(
        question_id="gsm8k_009",
        question="Solve the quadratic equation x^2 - 9 = 0 for x.",
        reference_answer="x = 3 or x = -3",
        expected_context="Factoring: (x - 3)(x + 3) = 0 -> x = 3 or x = -3.",
        category="algebra",
        difficulty="medium",
    ),
    BenchmarkItem(
        question_id="gsm8k_010",
        question="In a box there are 5 red balls, 3 blue balls, and 2 green balls. What is the probability of randomly picking a blue ball?",
        reference_answer="0.3",
        expected_context="Total balls: 5 + 3 + 2 = 10. Blue balls: 3. Probability: 3 / 10 = 0.3 or 30%.",
        category="probability",
        difficulty="medium",
    ),
]


class GSM8KBenchmarkDataset:
    """Provides controlled access to the curated GSM8K benchmark dataset."""

    def __init__(self, items: Optional[List[BenchmarkItem]] = None):
        self.items = items if items is not None else list(GSM8K_SUBSET)

    def get_all(self) -> List[BenchmarkItem]:

        return list(self.items)

    def get_subset(self, limit: int = 5) -> List[BenchmarkItem]:
        return list(self.items[:max(1, limit)])

    def get_by_id(self, question_id: str) -> Optional[BenchmarkItem]:
        for item in self.items:
            if item.question_id == question_id:
                return item
        return None
