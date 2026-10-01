// High-fidelity scientific benchmark data for Laboratory Simulation Mode

export const MOCK_SOLVE_RESULT = {
  best_agent: 'Proposer Agent (Alpha)',
  solver_used: 'Proposer Agent (Alpha)',
  answer: '22 and 24',
  confidence: 0.984,
  total_time: 1.38,
  rag_used: true,
  rag_context_count: 3,
  api_used: 'Groq (Llama-3.3-70B-Versatile)',
  api_latency_ms: 138,
  solution: `Step 1: Algebraic Formulation
Let the first even integer be denoted as 2n, where n ∈ ℤ.
Since the next even integer is consecutive, it must be 2n + 2.

Step 2: Linear Equation Construction
According to the problem statement:
(2n) + (2n + 2) = 46

Step 3: Simplification and Isolation
Combine like algebraic terms:
4n + 2 = 46
4n = 44
n = 11

Step 4: Evaluating the Integer Values
First even integer: 2(11) = 22
Second even integer: 2(11) + 2 = 24

Step 5: Parity and Sum Verification
22 is an even integer.
24 is an even integer.
Consecutive verification: 24 - 22 = 2 (Valid).
Sum verification: 22 + 24 = 46.

Conclusion:
The two consecutive even numbers are 22 and 24.`,
};

export const MOCK_DEBATE_RESULT = {
  debate_winner: 'Proposer Agent (Alpha)',
  debate_rounds: 3,
  final_solution: `Theorem: For two consecutive even integers whose sum is 46, the unique integers are 22 and 24.

Proof:
1. Define consecutive even integers as x and x + 2 for x = 2k.
2. The equation x + (x + 2) = 46 simplifies to 2x + 2 = 46, yielding 2x = 44, hence x = 22.
3. The successive integer is 22 + 2 = 24.
4. Lean 4 theorem specification verified:
   theorem consecutive_even_sum (n : ℤ) (h : (2*n) + (2*n + 2) = 46) : 2*n = 22 ∧ 2*n + 2 = 24 := by
     linarith`,
  debate_history: {
    rounds: [
      {
        round: 1,
        timestamp: new Date(Date.now() - 45000).toISOString(),
        critiques: {
          'Proposer Agent (Alpha)':
            'Proposed hypothesis: Set integers as 2n and 2n + 2. Sum is 4n + 2 = 46, which resolves to n = 11. Thus numbers are 22 and 24.',
          'Critic Agent (Beta)':
            'Counterargument audit: Check boundary conditions where n is negative or non-integer. If n = -11, sum is -46. We must ensure positive consecutive ordering is verified.',
        },
      },
      {
        round: 2,
        timestamp: new Date(Date.now() - 25000).toISOString(),
        critiques: {
          'Proposer Agent (Alpha)':
            'Rebuttal & Refinement: The problem asks for integers whose sum is +46. Since 4n + 2 = 46 has a unique linear root n = 11 in ℝ and ℤ, no alternate branches exist.',
          'Critic Agent (Beta)':
            'Verification passed: Algebraic uniqueness confirmed. No parity anomalies detected.',
        },
      },
      {
        round: 3,
        timestamp: new Date(Date.now() - 10000).toISOString(),
        critiques: {
          'Meta-Agent Synthesizer':
            'Convergence achieved. Synthesized proof steps align with formal Peano arithmetic. Ready for judicial sign-off.',
        },
      },
    ],
    final_decision: {
      best_agent: 'Proposer Agent (Alpha)',
      evaluation_reasoning:
        'Agent Alpha provided a rigorous linear proof without parity violations. Critic Agent Beta verified boundary conditions and confirmed uniqueness.',
      confidence: 0.985,
    },
  },
};

export const MOCK_ANALYZE_RESULT = {
  success: true,
  problem_type: 'Algebra & Linear Equations',
  difficulty: 'Intermediate (1420 ELO)',
  concepts: 'Consecutive Parity, Linear Systems in ℤ, Invariant Sums',
  approaches: 'Algebraic substitution with parity verification',
  hints: [
    'Express consecutive even numbers algebraically as 2n and 2n + 2.',
    'Set up the linear equation: 2n + (2n + 2) = 46.',
    'Combine like terms to isolate 4n = 44, yielding n = 11.',
    'Substitute n back into 2n and 2n + 2 to confirm values 22 and 24.',
  ],
  confidence: 0.94,
  similar_count: 5,
};

export const MOCK_STATS_RESULT = {
  success: true,
  stats: {
    agent_count: 4,
    total_problems: 1319,
    vector_store_stats: {
      total_documents: 1319,
      memory_usage_mb: 24.8,
      dimension: 384,
      index_type: 'FlatL2 (Exact)',
    },
    problem_types: {
      Arithmetic: 420,
      Algebra: 385,
      Geometry: 215,
      'Number Theory': 175,
      Combinatorics: 124,
    },
  },
};

export const MOCK_EVALUATION_RESULT = {
  timestamp: new Date().toISOString(),
  problem: 'The sum of two consecutive even numbers is 46. What are the two numbers?',
  success: true,
  accuracy: 0.985,
  confidence: 0.984,
  total_time: 1.38,
  api_used: 'Groq (Llama-3.3-70B)',
  rag_used: true,
  rag_similarity: 0.914,
  feedback: 'OK — Verified proof convergence in 2 turns. Zero hallucinated terms detected.',
};

export const MOCK_CORPUS_DATA = [
  {
    problem: 'A bakery sells cupcakes for $3 each. If Sarah buys 8 cupcakes and pays with a $50 bill, how much change will she receive?',
    answer: '$26',
    solution: '8 cupcakes × $3 = $24 total cost. $50 - $24 = $26 change.',
    type: 'Arithmetic',
    difficulty: 'Introductory',
  },
  {
    problem: 'A rectangular garden is 12 meters long and 8 meters wide. What is the perimeter of the garden?',
    answer: '40 meters',
    solution: 'Perimeter = 2 × (length + width) = 2 × (12 + 8) = 2 × 20 = 40 meters.',
    type: 'Geometry',
    difficulty: 'Introductory',
  },
  {
    problem: 'Tom has 24 marbles. He gives 1/3 of them to his friend and 1/4 of the remaining marbles to his sister. How many marbles does Tom have left?',
    answer: '12 marbles',
    solution: 'Tom gives 1/3 × 24 = 8 marbles. Remaining: 24 - 8 = 16 marbles. Gives 1/4 × 16 = 4 marbles. Left: 16 - 4 = 12 marbles.',
    type: 'Fractions',
    difficulty: 'Intermediate',
  },
  {
    problem: 'The sum of two consecutive even numbers is 46. What are the two numbers?',
    answer: '22 and 24',
    solution: '2n + (2n + 2) = 46 => 4n + 2 = 46 => 4n = 44 => n = 11. Numbers are 22 and 24.',
    type: 'Algebra',
    difficulty: 'Intermediate',
  },
  {
    problem: 'A car travels at 60 mph for 2.5 hours. How far does the car travel?',
    answer: '150 miles',
    solution: 'Distance = Speed × Time = 60 mph × 2.5 hours = 150 miles.',
    type: 'Rates & Motion',
    difficulty: 'Introductory',
  },
  {
    problem: 'Find all positive integers n such that n^2 + 19n + 48 is a perfect square.',
    answer: 'n = 1 or n = 28',
    solution: 'Let n^2 + 19n + 48 = k^2. Completing the square: (2n + 19)^2 - 4k^2 = 19^2 - 192 = 169 = 13^2. Factor as difference of squares.',
    type: 'Number Theory',
    difficulty: 'Olympiad',
  },
];
