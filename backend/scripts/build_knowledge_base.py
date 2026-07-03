"""
Knowledge Base Builder for RAG System
Builds vector database from multiple sources including GSM8K
FIXED: Explicit .env loading from backend directory
"""

import sys
import os
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════
# 🔧 FIX: Load .env from correct location BEFORE other imports
# ═══════════════════════════════════════════════════════════════════════

# Get the backend directory (parent of scripts/)
BACKEND_DIR = Path(__file__).resolve().parent.parent

# Load dotenv explicitly
from dotenv import load_dotenv

# Construct path to .env file
ENV_PATH = BACKEND_DIR / '.env'

# Debug output
print(f"DEBUG: Script location: {Path(__file__).resolve()}")
print(f"DEBUG: Backend directory: {BACKEND_DIR}")
print(f"DEBUG: .env path: {ENV_PATH}")
print(f"DEBUG: .env exists: {ENV_PATH.exists()}")

# Check if .env exists
if not ENV_PATH.exists():
    print("\n" + "="*70)
    print("❌ ERROR: .env file not found!")
    print("="*70)
    print(f"\nExpected location: {ENV_PATH}")
    print("\n💡 TO FIX:")
    print("   1. Create a .env file in the backend folder")
    print("   2. Add your API keys (see .env.example)")
    print("   3. Run this script again")
    print("="*70 + "\n")
    sys.exit(1)

# Load the .env file with override=True
load_dotenv(dotenv_path=ENV_PATH, override=True)

# Verify API keys were loaded
print(f"DEBUG: GROQ_API_KEY present: {bool(os.getenv('GROQ_API_KEY'))}")
print(f"DEBUG: OPENAI_API_KEY present: {bool(os.getenv('OPENAI_API_KEY'))}")
print(f"DEBUG: COHERE_API_KEY present: {bool(os.getenv('COHERE_API_KEY'))}")
print(f"DEBUG: HUGGING_FACE_API_KEY present: {bool(os.getenv('HUGGING_FACE_API_KEY'))}")
print()

# Add backend to Python path
sys.path.insert(0, str(BACKEND_DIR))

# ═══════════════════════════════════════════════════════════════════════
# Now safe to import project modules
# ═══════════════════════════════════════════════════════════════════════

import logging
import time
import argparse
from typing import Optional

from utils.knowledge_base_loader import KnowledgeBaseLoader
from utils.api_client import APIClient
from rag.vector_store import MathProblemVectorStore
from config import SYSTEM_CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_api_configuration(api_client: APIClient) -> bool:
    """Verify API configuration and display status"""
    print("\n" + "="*70)
    print("🔧 META-AGENT SYSTEM CONFIGURATION")
    print("="*70 + "\n")
    
    # Check configuration
    if not api_client.is_configured():
        print("❌ CRITICAL: NO API providers configured!\n")
        print("💡 TO FIX THIS:")
        print(f"   1. Verify .env file exists at: {ENV_PATH}")
        print("   2. Check API keys are present (no quotes, no spaces around =)")
        print("   3. Ensure at least ONE of these keys is set:")
        print("      - GROQ_API_KEY")
        print("      - OPENAI_API_KEY")
        print("      - COHERE_API_KEY")
        print("      - HUGGING_FACE_API_KEY")
        print("\n📝 Get free API keys:")
        print("   • Groq: https://console.groq.com/")
        print("   • Cohere: https://dashboard.cohere.com/")
        print("   • Hugging Face: https://huggingface.co/settings/tokens")
        print("="*70 + "\n")
        return False
    
    # Show provider status
    provider_status = api_client.get_provider_status()
    configured = [p for p, status in provider_status.items() if status]
    missing = [p for p, status in provider_status.items() if not status]
    
    print(f"📊 Status: {len(configured)}/4 providers configured")
    for provider in configured:
        print(f"   ✅ {provider:<18} - CONFIGURED")
    for provider in missing:
        print(f"   ❌ {provider:<18} - MISSING")
    print()
    
    print(f"✅ {len(configured)} API provider(s) configured successfully!")
    print("="*70 + "\n")
    
    return True


def build_knowledge_base(
    use_gsm8k: bool = True,
    use_custom: bool = True,
    gsm8k_limit: Optional[int] = 1000,
    use_test_set: bool = False
):
    """Build knowledge base from multiple sources"""
    
    print("\n" + "="*70)
    print("🏗️  BUILDING RAG KNOWLEDGE BASE WITH GSM8K")
    print("="*70 + "\n")
    
    # Initialize components
    logger.info("1️⃣ Initializing components...")
    kb_loader = KnowledgeBaseLoader()
    api_client = APIClient()
    vector_store = MathProblemVectorStore()
    
    # Check API configuration
    if not check_api_configuration(api_client):
        return False
    
    # Configure data sources
    logger.info("2️⃣ Configuring data sources...")
    sources = []
    
    # Custom problems
    if use_custom:
        custom_path = BACKEND_DIR / 'data' / 'math_problems.json'
        if custom_path.exists():
            sources.append({
                'path': str(custom_path),
                'format': 'json'
            })
            logger.info(f"   ✅ Custom problems: {custom_path.name}")
        else:
            logger.warning(f"   ⚠️ Custom file not found: {custom_path}")
            logger.info(f"      Expected at: {custom_path}")
    
    # GSM8K training set
    if use_gsm8k:
        gsm8k_train_path = BACKEND_DIR / 'data' / 'gsm8k_train.jsonl'
        if gsm8k_train_path.exists():
            sources.append({
                'path': str(gsm8k_train_path),
                'format': 'gsm8k',
                'max_problems': gsm8k_limit
            })
            limit_str = f"{gsm8k_limit}" if gsm8k_limit else "ALL"
            logger.info(f"   ✅ GSM8K train: {gsm8k_train_path.name} (limit: {limit_str})")
        else:
            logger.warning(f"   ⚠️ GSM8K not found: {gsm8k_train_path}")
            logger.info(f"      Expected at: {gsm8k_train_path}")
            logger.info(f"      Download from: https://github.com/openai/grade-school-math")
    
    # GSM8K test set (optional)
    if use_test_set:
        gsm8k_test_path = BACKEND_DIR / 'data' / 'gsm8k_test.jsonl'
        if gsm8k_test_path.exists():
            sources.append({
                'path': str(gsm8k_test_path),
                'format': 'gsm8k',
                'max_problems': 200
            })
            logger.info(f"   ✅ GSM8K test: {gsm8k_test_path.name}")
    
    if not sources:
        logger.error("\n❌ No data sources available!")
        logger.error("   Please add at least one data file:")
        logger.error(f"   • {BACKEND_DIR / 'data' / 'math_problems.json'}")
        logger.error(f"   • {BACKEND_DIR / 'data' / 'gsm8k_train.jsonl'}")
        return False
    
    # Load problems
    logger.info(f"\n3️⃣ Loading problems from {len(sources)} source(s)...")
    problems = kb_loader.load_multiple_sources(sources)
    
    if not problems:
        logger.error("❌ No problems loaded!")
        return False
    
    # Display statistics
    stats = kb_loader.get_statistics()
    logger.info(f"\n📊 Knowledge Base Statistics:")
    logger.info(f"   Total problems: {stats['total']}")
    logger.info(f"   By source: {stats['by_source']}")
    
    # Show top 5 problem types
    top_types = dict(list(stats['by_type'].items())[:5])
    logger.info(f"   By type (top 5): {top_types}...")
    logger.info(f"   By difficulty: {stats['by_difficulty']}")
    
    # Generate embeddings
    logger.info(f"\n4️⃣ Generating embeddings for {len(problems)} problems...")
    logger.info("   ⏳ This will take several minutes...")
    
    # Calculate estimated time (0.5 seconds per embedding)
    estimated_minutes = len(problems) * 0.5 / 60
    logger.info(f"   💡 Estimated time: {estimated_minutes:.1f} minutes")
    logger.info(f"   ℹ️  Progress updates every 50 embeddings\n")
    
    embeddings = []
    failed_count = 0
    start_time = time.time()
    
    for i, problem in enumerate(problems):
        # Progress indicator every 50 problems
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (len(problems) - i - 1) / rate if rate > 0 else 0
            progress = (i + 1) / len(problems) * 100
            logger.info(
                f"   Progress: {i+1}/{len(problems)} ({progress:.1f}%) "
                f"- ETA: {remaining/60:.1f} min"
            )
        
        # Generate embedding for problem text
        problem_text = problem.get('problem', '')
        
        if not problem_text:
            logger.warning(f"   ⚠️ Empty problem at index {i}")
            failed_count += 1
            embeddings.append([0.0] * SYSTEM_CONFIG['embedding_dimension'])
            continue
        
        emb = api_client.get_embeddings(problem_text)
        
        if emb and len(emb) > 0:
            embeddings.append(emb)
        else:
            failed_count += 1
            # Use zero vector as placeholder
            embeddings.append([0.0] * SYSTEM_CONFIG['embedding_dimension'])
            logger.warning(f"   ⚠️ Failed embedding for problem {i+1}")
        
        # Small delay to avoid rate limits (50ms)
        time.sleep(0.05)
    
    total_time = time.time() - start_time
    success_count = len(embeddings) - failed_count
    
    logger.info(f"\n   ✅ Generated {success_count}/{len(problems)} embeddings in {total_time/60:.1f} minutes")
    if failed_count > 0:
        logger.warning(f"   ⚠️ Failed: {failed_count} embeddings (using zero vectors)")
    
    # Build vector store
    logger.info("\n5️⃣ Building vector store...")
    success = vector_store.add_math_problems(problems, embeddings)
    
    if not success:
        logger.error("❌ Failed to build vector store")
        return False
    
    logger.info(f"   ✅ Added {len(problems)} problems to vector store")
    
    # Save to disk
    logger.info("\n6️⃣ Saving vector store...")
    save_path = BACKEND_DIR / SYSTEM_CONFIG.get('vector_db_path', './database/vector_store.db')
    
    # Ensure directory exists
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    if vector_store.save(str(save_path)):
        file_size = save_path.stat().st_size / (1024 * 1024)
        logger.info(f"   ✅ Saved: {save_path.name} ({file_size:.2f} MB)")
        logger.info(f"   📁 Full path: {save_path}")
    else:
        logger.error("❌ Failed to save vector store")
        return False
    
    # Final summary
    vs_stats = vector_store.get_stats()
    
    print("\n" + "="*70)
    print("✅ KNOWLEDGE BASE BUILD COMPLETE!")
    print("="*70)
    print(f"\n📊 Final Statistics:")
    print(f"   Documents: {vs_stats['total_documents']}")
    print(f"   Dimension: {vs_stats['dimension']}")
    print(f"   Memory: {vs_stats['memory_usage_mb']:.2f} MB")
    print(f"   Problem types: {len(vs_stats['problem_types'])} types")
    print(f"   Sources: {vs_stats.get('source_distribution', {})}")
    print(f"   Build time: {total_time/60:.1f} minutes")
    print(f"   Success rate: {(success_count/len(problems)*100):.1f}%")
    print(f"\n📁 Saved to: {save_path}")
    print(f"\n🎯 Your RAG system is ready!")
    print(f"   • Start app: python app.py")
    print(f"   • Check RAG: curl http://localhost:5000/api/rag-status")
    print(f"   • Test solve: POST /api/solve with your problem")
    print("="*70 + "\n")
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Build RAG Knowledge Base for Meta-Agent System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build with default settings (1000 GSM8K + custom)
  python scripts/build_knowledge_base.py
  
  # Use all GSM8K problems
  python scripts/build_knowledge_base.py --all
  
  # Only custom problems (no GSM8K)
  python scripts/build_knowledge_base.py --no-gsm8k
  
  # Custom GSM8K limit
  python scripts/build_knowledge_base.py --gsm8k-limit 500
  
  # Include test set
  python scripts/build_knowledge_base.py --include-test
        """
    )
    
    parser.add_argument(
        '--no-gsm8k',
        action='store_true',
        help='Exclude GSM8K dataset'
    )
    parser.add_argument(
        '--no-custom',
        action='store_true',
        help='Exclude custom problems'
    )
    parser.add_argument(
        '--gsm8k-limit',
        type=int,
        default=1000,
        help='Maximum GSM8K problems to use (default: 1000)'
    )
    parser.add_argument(
        '--include-test',
        action='store_true',
        help='Include GSM8K test set'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Use ALL GSM8K problems (ignores --gsm8k-limit)'
    )
    
    args = parser.parse_args()
    
    # Determine GSM8K limit
    gsm8k_limit = None if args.all else args.gsm8k_limit
    
    try:
        print("\n" + "="*70)
        print("🚀 META-AGENT RAG KNOWLEDGE BASE BUILDER")
        print("="*70)
        print(f"\nConfiguration:")
        print(f"   Backend directory: {BACKEND_DIR}")
        print(f"   Use GSM8K: {not args.no_gsm8k}")
        print(f"   GSM8K limit: {'ALL' if args.all else gsm8k_limit}")
        print(f"   Use custom: {not args.no_custom}")
        print(f"   Include test set: {args.include_test}")
        
        success = build_knowledge_base(
            use_gsm8k=not args.no_gsm8k,
            use_custom=not args.no_custom,
            gsm8k_limit=gsm8k_limit,
            use_test_set=args.include_test
        )
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Build interrupted by user")
        logger.info("Build cancelled by keyboard interrupt")
        sys.exit(1)
        
    except Exception as e:
        print("\n" + "="*70)
        print("💥 UNEXPECTED ERROR")
        print("="*70)
        logger.error(f"Error: {str(e)}", exc_info=True)
        print("="*70 + "\n")
        sys.exit(1)
