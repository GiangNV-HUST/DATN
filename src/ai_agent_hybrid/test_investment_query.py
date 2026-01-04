"""
Test Investment Query: "Voi 100 trieu thi nen dau tu chung khoan nao"

This tests the full Hybrid System with AI routing and specialized agents.
"""

import sys
import os
import asyncio

# IMPORTANT: Load .env BEFORE any imports
from dotenv import load_dotenv
final_root = os.path.join(os.path.dirname(__file__), '..', '..')
load_dotenv(os.path.join(final_root, '.env'))

# Add paths - add ai_agent_hybrid directory to path, not hybrid_system
sys.path.insert(0, final_root)
sys.path.insert(0, os.path.dirname(__file__))  # ai_agent_hybrid directory

print("=" * 70)
print("TEST INVESTMENT QUERY")
print("=" * 70)
print()
print("Query: 'Voi 100 trieu thi nen dau tu chung khoan nao'")
print()

# Check if GEMINI_API_KEY is loaded
gemini_key = os.getenv("GEMINI_API_KEY")
if not gemini_key:
    print("[ERROR] GEMINI_API_KEY not found in .env!")
    print("Please make sure .env contains:")
    print("  GEMINI_API_KEY=your_api_key_here")
    sys.exit(1)

print(f"[OK] GEMINI_API_KEY loaded: {gemini_key[:20]}...")
print()

# Test 1: Import HybridOrchestrator
print("[1/4] Importing HybridOrchestrator...")
try:
    from hybrid_system.orchestrator import HybridOrchestrator
    print("[OK] HybridOrchestrator imported")
except Exception as e:
    print(f"[FAIL] Cannot import: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Create orchestrator
print("\n[2/4] Creating HybridOrchestrator instance...")
try:
    orchestrator = HybridOrchestrator()
    print("[OK] Orchestrator created")
except Exception as e:
    print(f"[FAIL] Cannot create orchestrator: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Initialize
print("\n[3/4] Initializing orchestrator...")
async def test_query():
    try:
        await orchestrator.initialize()
        print("[OK] Orchestrator initialized")
    except Exception as e:
        print(f"[FAIL] Cannot initialize: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test 4: Process query
    print("\n[4/4] Processing investment query...")
    print("=" * 70)

    user_query = "Voi 100 trieu thi nen dau tu chung khoan nao"
    user_id = "test_user_123"

    try:
        full_response = []

        async for event in orchestrator.process_query(
            user_query=user_query,
            user_id=user_id,
            mode="auto"  # Let AI router decide
        ):
            event_type = event.get("type")
            data = event.get("data")

            if event_type == "status":
                print(f"\n[STATUS] {data}")

            elif event_type == "routing_decision":
                print(f"\n[ROUTING DECISION]")
                print(f"  Mode: {data.get('mode')}")
                print(f"  Complexity: {data.get('complexity')}")
                print(f"  Confidence: {data.get('confidence')}")
                print(f"  Reasoning: {data.get('reasoning')}")
                print(f"  Estimated time: {data.get('estimated_time')}s")
                if data.get('suggested_tools'):
                    print(f"  Suggested tools: {', '.join(data.get('suggested_tools'))}")
                print()

            elif event_type == "chunk":
                print(data, end='', flush=True)
                full_response.append(data)

            elif event_type == "complete":
                print(f"\n\n[COMPLETE]")
                print(f"  Elapsed time: {data.get('elapsed_time'):.2f}s")
                print(f"  Mode used: {data.get('mode_used')}")
                if data.get('time_saved'):
                    print(f"  Time saved: {data.get('time_saved'):.2f}s")

            elif event_type == "error":
                print(f"\n[ERROR] {data}")

        print("\n" + "=" * 70)
        print("[SUCCESS] Query processed successfully!")
        print("=" * 70)

        # Show metrics
        print("\n[METRICS]")
        metrics = orchestrator.get_metrics()
        print(f"  Total queries: {metrics.get('total_queries')}")
        print(f"  Agent mode: {metrics.get('agent_mode_count')}")
        print(f"  Direct mode: {metrics.get('direct_mode_count')}")
        print(f"  Cache hits: {metrics.get('cache_hits', 0)}")
        print(f"  Cache hit rate: {metrics.get('cache_hit_rate', '0%')}")

    except Exception as e:
        print(f"\n[FAIL] Error processing query: {e}")
        import traceback
        traceback.print_exc()

    # Cleanup
    print("\n[CLEANUP] Closing orchestrator...")
    try:
        await orchestrator.cleanup()
        print("[OK] Orchestrator cleaned up")
    except:
        pass

# Run test
if __name__ == "__main__":
    print()
    asyncio.run(test_query())
    print()
