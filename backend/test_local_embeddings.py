"""
Test Local Embeddings with Sentence Transformers
Verifies that local embeddings work before building knowledge base
"""

import sys
import os
from pathlib import Path

# Setup paths
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

print("\n" + "="*70)
print("🧪 TESTING LOCAL EMBEDDINGS")
print("="*70 + "\n")

print(f"Backend directory: {BACKEND_DIR}\n")

# Test 1: Check if sentence-transformers is installed
print("1️⃣ Checking sentence-transformers installation...")
try:
    import sentence_transformers
    print(f"   ✅ sentence-transformers installed (version {sentence_transformers.__version__})")
except ImportError:
    print("   ❌ sentence-transformers NOT installed!")
    print("\n💡 Install with:")
    print("   pip install sentence-transformers torch")
    sys.exit(1)

# Test 2: Load the model
print("\n2️⃣ Loading model (sentence-transformers/all-MiniLM-L6-v2)...")
try:
    from sentence_transformers import SentenceTransformer
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("   ✅ Model loaded successfully")
    
    print(f"\n   Model info:")
    print(f"      Embedding dimension: {model.get_sentence_embedding_dimension()}")
    print(f"      Max sequence length: {model.max_seq_length}")
    
except Exception as e:
    print(f"   ❌ Failed to load model: {str(e)}")
    sys.exit(1)

# Test 3: Generate embeddings
print(f"\n3️⃣ Testing embedding generation...")

test_texts = [
    "What is 2 + 2?",
    "A train travels 60 miles per hour for 3 hours. How far does it go?",
    "Calculate the area of a rectangle with length 5 and width 3."
]

all_success = True

for i, text in enumerate(test_texts, 1):
    print(f"\n   Test {i}: '{text[:50]}{'...' if len(text) > 50 else ''}'")
    
    try:
        embedding = model.encode(text, convert_to_numpy=True)
        
        print(f"      ✅ Success!")
        print(f"         Dimension: {len(embedding)}")
        print(f"         Sample values: {embedding[:5].tolist()}")
        print(f"         Data type: {type(embedding[0])}")
        
    except Exception as e:
        print(f"      ❌ Failed: {str(e)}")
        all_success = False

# Test 4: Test with API Client (optional)
print(f"\n4️⃣ Testing with API Client...")
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=BACKEND_DIR / '.env', override=True)
    
    from utils.api_client import APIClient
    
    api_client = APIClient()
    
    test_text = "What is 10 divided by 2?"
    print(f"\n   Test text: '{test_text}'")
    
    embedding = api_client.get_embeddings(test_text)
    
    if embedding and len(embedding) > 0:
        print(f"   ✅ API Client embeddings SUCCESS!")
        print(f"      Dimension: {len(embedding)}")
        print(f"      Sample: {embedding[:5]}")
    else:
        print(f"   ❌ API Client embeddings FAILED!")
        print(f"      Result: {embedding}")
        all_success = False
        
except Exception as e:
    print(f"   ⚠️ API Client test skipped: {str(e)}")

# Final result
print("\n" + "="*70)
if all_success:
    print("✅ ALL TESTS PASSED - LOCAL EMBEDDINGS WORKING!")
    print("\n🎯 You're ready to build the knowledge base!")
    print("   Run: python scripts\\build_knowledge_base.py")
else:
    print("❌ SOME TESTS FAILED")
    print("\n💡 Fix the issues above before building knowledge base")
print("="*70 + "\n")

sys.exit(0 if all_success else 1)
