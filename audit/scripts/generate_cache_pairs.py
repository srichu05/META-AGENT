import sys
import os
import json
import numpy as np

# Set offline mode so it uses cached HuggingFace models without hanging on network checks
os.environ['HF_HUB_OFFLINE'] = '1'
sys.path.insert(0, r'e:\Meta_Agent_Math_Debate_System\backend')
from ingestion.embeddings import BGEEmbeddingService

pairs = [
    # 1. Identical repeated queries
    {
        'pair_id': 'pair_001',
        'type': 'identical',
        'query_a': 'What is 15 + 27?',
        'query_b': 'What is 15 + 27?',
        'expected_relationship': 'equivalent',
        'reason': 'Exact identical question string.',
        'exact_match': True,
        'requires_corpus_invalidation': False
    },
    {
        'pair_id': 'pair_002',
        'type': 'identical',
        'query_a': 'Solve for x in the linear equation: 4x - 12 = 28.',
        'query_b': 'Solve for x in the linear equation: 4x - 12 = 28.',
        'expected_relationship': 'equivalent',
        'reason': 'Exact identical equation query string.',
        'exact_match': True,
        'requires_corpus_invalidation': False
    },
    # 2. Paraphrases (same math intent)
    {
        'pair_id': 'pair_003',
        'type': 'paraphrase',
        'query_a': 'Find the perimeter of a rectangle with length 12m and width 8m.',
        'query_b': 'What is the perimeter of a rectangular garden that is 12 meters long and 8 meters wide?',
        'expected_relationship': 'equivalent',
        'reason': 'Same mathematical parameters and objective with minor wording variations.',
        'exact_match': False,
        'requires_corpus_invalidation': False
    },
    {
        'pair_id': 'pair_004',
        'type': 'paraphrase',
        'query_a': 'Solve for x in the equation 4x - 12 = 28.',
        'query_b': 'Determine the value of x satisfying 4*x - 12 = 28.',
        'expected_relationship': 'equivalent',
        'reason': 'Equivalent algebraic problem with formal phrasing.',
        'exact_match': False,
        'requires_corpus_invalidation': False
    },
    {
        'pair_id': 'pair_005',
        'type': 'paraphrase',
        'query_a': 'A car travels at 60 mph for 2.5 hours. How far does the car travel?',
        'query_b': 'Calculate the total distance traveled by an automobile moving at 60 miles per hour over 2.5 hours.',
        'expected_relationship': 'equivalent',
        'reason': 'Identical physical constants and formula.',
        'exact_match': False,
        'requires_corpus_invalidation': False
    },
    {
        'pair_id': 'pair_006',
        'type': 'paraphrase',
        'query_a': 'What is 20% discount on an $80 item?',
        'query_b': 'If an item costs $80 and has a 20 percent discount, what is the discount amount?',
        'expected_relationship': 'equivalent',
        'reason': 'Identical percentage computation.',
        'exact_match': False,
        'requires_corpus_invalidation': False
    },
    # 3. Number Change (semantically similar text, different numbers -> NON-EQUIVALENT)
    {
        'pair_id': 'pair_007',
        'type': 'number_change',
        'query_a': 'A car travels at 60 mph for 2.5 hours. How far does the car travel?',
        'query_b': 'A car travels at 40 mph for 2.5 hours. How far does the car travel?',
        'expected_relationship': 'non_equivalent',
        'reason': 'Speed changed from 60 to 40 mph; result is 100 miles instead of 150 miles.',
        'exact_match': False,
        'requires_corpus_invalidation': False
    },
    {
        'pair_id': 'pair_008',
        'type': 'number_change',
        'query_a': 'A bakery sells cupcakes for $3 each. If Sarah buys 8 cupcakes with a $50 bill, how much change will she receive?',
        'query_b': 'A bakery sells cupcakes for $4 each. If Sarah buys 8 cupcakes with a $50 bill, how much change will she receive?',
        'expected_relationship': 'non_equivalent',
        'reason': 'Unit price altered from $3 to $4; change received is $18 instead of $26.',
        'exact_match': False,
        'requires_corpus_invalidation': False
    },
    {
        'pair_id': 'pair_009',
        'type': 'number_change',
        'query_a': 'Solve for x: 4x - 12 = 28.',
        'query_b': 'Solve for x: 4x - 12 = 32.',
        'expected_relationship': 'non_equivalent',
        'reason': 'RHS changed; x=10 vs x=11.',
        'exact_match': False,
        'requires_corpus_invalidation': False
    },
    {
        'pair_id': 'pair_010',
        'type': 'number_change',
        'query_a': 'A rectangle has a length of 15 cm and a width of 8 cm. What is the area?',
        'query_b': 'A rectangle has a length of 25 cm and a width of 8 cm. What is the area?',
        'expected_relationship': 'non_equivalent',
        'reason': 'Length altered; area changes from 120 to 200 cm^2.',
        'exact_match': False,
        'requires_corpus_invalidation': False
    },
    # 4. Critical Operator / Constraint Change
    {
        'pair_id': 'pair_011',
        'type': 'operator_constraint_change',
        'query_a': 'Solve for x: 4x - 12 = 28.',
        'query_b': 'Solve for x: 4x + 12 = 28.',
        'expected_relationship': 'non_equivalent',
        'reason': 'Operator changed from minus to plus; x=10 vs x=4.',
        'exact_match': False,
        'requires_corpus_invalidation': False
    },
    {
        'pair_id': 'pair_012',
        'type': 'operator_constraint_change',
        'query_a': 'What is the perimeter of a rectangle with length 12m and width 8m?',
        'query_b': 'What is the area of a rectangle with length 12m and width 8m?',
        'expected_relationship': 'non_equivalent',
        'reason': 'Target metric changed from perimeter to area (40m vs 96m^2).',
        'exact_match': False,
        'requires_corpus_invalidation': False
    },
    {
        'pair_id': 'pair_013',
        'type': 'operator_constraint_change',
        'query_a': 'In a box there are 5 red, 3 blue, and 2 green balls. Probability of picking a blue ball?',
        'query_b': 'In a box there are 5 red, 3 blue, and 2 green balls. Probability of not picking a blue ball?',
        'expected_relationship': 'non_equivalent',
        'reason': 'Complementary event: P(blue)=0.3 vs P(not blue)=0.7.',
        'exact_match': False,
        'requires_corpus_invalidation': False
    },
    {
        'pair_id': 'pair_014',
        'type': 'operator_constraint_change',
        'query_a': 'The sum of two consecutive even numbers is 46. What are the two numbers?',
        'query_b': 'The sum of two consecutive odd numbers is 46. What are the two numbers?',
        'expected_relationship': 'non_equivalent',
        'reason': 'Parity constraint changed from even to odd (22, 24 vs no integer solution since odd+odd=even, e.g. 22.5 is not integer).',
        'exact_match': False,
        'requires_corpus_invalidation': False
    },
    # 5. Questions requiring different supporting documents
    {
        'pair_id': 'pair_015',
        'type': 'different_document',
        'query_a': 'According to Document Chapter 1, what is the Euler characteristic formula for polyhedra?',
        'query_b': 'According to Document Chapter 4, what is the Euler characteristic formula for planar graphs?',
        'expected_relationship': 'non_equivalent',
        'reason': 'Different source chapters and mathematical domain context.',
        'exact_match': False,
        'requires_corpus_invalidation': True
    },
    {
        'pair_id': 'pair_016',
        'type': 'different_document',
        'query_a': 'What are the grading weights for Homework 1 in syllabus.pdf?',
        'query_b': 'What are the grading weights for Midterm Exam in syllabus.pdf?',
        'expected_relationship': 'non_equivalent',
        'reason': 'Different syllabus sections and assessment policies.',
        'exact_match': False,
        'requires_corpus_invalidation': True
    },
    {
        'pair_id': 'pair_017',
        'type': 'different_document',
        'query_a': 'State Theorem 3.1 from textbook_algebra.pdf',
        'query_b': 'State Theorem 5.2 from textbook_geometry.pdf',
        'expected_relationship': 'non_equivalent',
        'reason': 'Different document files and mathematical theorems.',
        'exact_match': False,
        'requires_corpus_invalidation': True
    },
    # 6. Corpus-Dependent Questions (answer changes when knowledge corpus changes)
    {
        'pair_id': 'pair_018',
        'type': 'corpus_dependent',
        'query_a': 'What is the current policy on late math assignment submissions?',
        'query_b': 'What is the policy on late math assignment submissions in the updated course handbook?',
        'expected_relationship': 'equivalent',
        'reason': 'Identical intent, but answer strictly depends on active document index version.',
        'exact_match': False,
        'requires_corpus_invalidation': True
    },
    {
        'pair_id': 'pair_019',
        'type': 'corpus_dependent',
        'query_a': 'What are the official competition math rules for calculator usage in Section 2?',
        'query_b': 'What are the official math olympiad calculator rules in Section 2?',
        'expected_relationship': 'equivalent',
        'reason': 'Requires invalidation if rule document is re-uploaded.',
        'exact_match': False,
        'requires_corpus_invalidation': True
    },
    {
        'pair_id': 'pair_020',
        'type': 'corpus_dependent',
        'query_a': 'What is the value of the departmental budget constant C_math in finance.docx?',
        'query_b': 'Retrieve the value of C_math from finance.docx',
        'expected_relationship': 'equivalent',
        'reason': 'Corpus document lookup, invalid if document is updated.',
        'exact_match': False,
        'requires_corpus_invalidation': True
    },
    # Additional pairs for sample size and variance
    {
        'pair_id': 'pair_021',
        'type': 'paraphrase',
        'query_a': 'Janet’s ducks lay 16 eggs per day. She eats 3 and bakes 4. How many does she sell?',
        'query_b': 'Janet has ducks producing 16 eggs daily. Eating 3 for breakfast and using 4 for muffins, how many eggs remain for sale?',
        'expected_relationship': 'equivalent',
        'reason': 'Same math structure, paraphrased wording.',
        'exact_match': False,
        'requires_corpus_invalidation': False
    },
    {
        'pair_id': 'pair_022',
        'type': 'number_change',
        'query_a': 'Janet’s ducks lay 16 eggs per day. She eats 3 and bakes 4. How many does she sell?',
        'query_b': 'Janet’s ducks lay 20 eggs per day. She eats 3 and bakes 4. How many does she sell?',
        'expected_relationship': 'non_equivalent',
        'reason': 'Total eggs changed from 16 to 20; answer changes from 9 to 13.',
        'exact_match': False,
        'requires_corpus_invalidation': False
    },
    {
        'pair_id': 'pair_023',
        'type': 'operator_constraint_change',
        'query_a': 'Find two numbers whose product is 24 and sum is 10.',
        'query_b': 'Find two numbers whose product is 24 and difference is 10.',
        'expected_relationship': 'non_equivalent',
        'reason': 'Constraint changed from sum to difference (4,6 vs 2,12).',
        'exact_match': False,
        'requires_corpus_invalidation': False
    },
    {
        'pair_id': 'pair_024',
        'type': 'paraphrase',
        'query_a': 'In a class of 30 students, 18 are girls. What percentage are boys?',
        'query_b': 'There are 30 students total in a classroom, with 18 being female. Find the percentage of male students.',
        'expected_relationship': 'equivalent',
        'reason': 'Paraphrased gender terminology, identical math.',
        'exact_match': False,
        'requires_corpus_invalidation': False
    },
    {
        'pair_id': 'pair_025',
        'type': 'number_change',
        'query_a': 'A pizza has 8 slices. If 3 people eat 2 slices each, what fraction remains?',
        'query_b': 'A pizza has 8 slices. If 3 people eat 1 slice each, what fraction remains?',
        'expected_relationship': 'non_equivalent',
        'reason': 'Slices eaten changed from 6 to 3; fraction remaining 2/8 (1/4) vs 5/8.',
        'exact_match': False,
        'requires_corpus_invalidation': False
    }
]

print(f"Loading BGEEmbeddingService to compute cosine similarities for {len(pairs)} query pairs...")
service = BGEEmbeddingService('BAAI/bge-small-en-v1.5', batch_size=16, expected_dimension=384)

all_texts = []
for p in pairs:
    all_texts.append(p['query_a'])
    all_texts.append(p['query_b'])

embeddings = service.generate(all_texts)
print(f"Generated embeddings shape: {embeddings.shape}")

out_records = []
for i, p in enumerate(pairs):
    vec_a = embeddings[2 * i]
    vec_b = embeddings[2 * i + 1]
    cos_sim = float(np.dot(vec_a, vec_b))
    record = dict(p)
    record['embedding_model'] = 'BAAI/bge-small-en-v1.5'
    record['cosine_similarity'] = round(cos_sim, 4)
    out_records.append(record)

out_file = r'audit\baseline_v1\cache_query_pairs.jsonl'
with open(out_file, 'w', encoding='utf-8') as f:
    for r in out_records:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print(f"Wrote {len(out_records)} pairs to {out_file}")

by_cat = {}
for r in out_records:
    cat = r['type']
    by_cat.setdefault(cat, []).append(r['cosine_similarity'])

print("\nMean Cosine Similarity by Category:")
for cat, scores in by_cat.items():
    print(f"  {cat:25s}: n={len(scores)}, mean={np.mean(scores):.4f}, min={np.min(scores):.4f}, max={np.max(scores):.4f}")

