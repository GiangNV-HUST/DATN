"""
Quick End-to-End Execution Test for Multi-Agent System
Tests actual execution with a few simple queries
"""

import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from src.ai_agent_hybrid.hybrid_system.orchestrator.multi_agent_orchestrator import MultiAgentOrchestrator


async def test_quick_execution():
    """Quick test of actual execution"""
    print("\n" + "="*80)
    print("QUICK END-TO-END EXECUTION TEST")
    print("="*80)

    orchestrator = MultiAgentOrchestrator(use_direct_client=True)
    await orchestrator.initialize()

    # Just test a few simple queries that should work without database
    test_cases = [
        {
            "query": "Giá VCB hôm nay",
            "expected_agent": "AnalysisSpecialist",
            "description": "Simple price query"
        },
        {
            "query": "So sánh VCB và TCB",
            "expected_agent": "ComparisonSpecialist",
            "description": "Simple comparison"
        },
        {
            "query": "VN-Index hôm nay như thế nào?",
            "expected_agent": "MarketContextSpecialist",
            "description": "Market overview"
        },
    ]

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test['description']} ---")
        print(f"Query: {test['query']}")

        start_time = time.time()
        response_chunks = []
        agents_used = []
        got_response = False

        try:
            async for event in orchestrator.process_query(test["query"], user_id="test_exec"):
                event_type = event.get("type", "")

                if event_type == "routing_decision":
                    tasks = event.get("data", {}).get("tasks", [])
                    for task in tasks:
                        agent = task.get("specialist", "")
                        if agent and agent not in agents_used:
                            agents_used.append(agent)
                    print(f"  Routed to: {agents_used}")

                elif event_type == "chunk":
                    chunk = event.get("data", "")
                    if isinstance(chunk, str) and len(chunk) > 0:
                        response_chunks.append(chunk)
                        if not got_response:
                            print(f"  First chunk received...")
                            got_response = True

                elif event_type == "complete":
                    print(f"  Completed!")

            elapsed = time.time() - start_time
            full_response = "".join(response_chunks)

            # Check if we got a meaningful response
            has_response = len(full_response) > 50
            correct_agent = test["expected_agent"] in agents_used

            status = "PASS" if has_response and correct_agent else "PARTIAL" if has_response or correct_agent else "FAIL"
            results.append((test['description'], status, elapsed, len(full_response)))

            print(f"  Response length: {len(full_response)} chars")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Result: {status}")

            # Show snippet of response
            if full_response:
                snippet = full_response[:200].replace('\n', ' ')
                print(f"  Preview: {snippet}...")

        except Exception as e:
            elapsed = time.time() - start_time
            results.append((test['description'], "ERROR", elapsed, 0))
            print(f"  ERROR: {str(e)[:100]}")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    passed = 0
    for desc, status, elapsed, resp_len in results:
        icon = "✓" if status == "PASS" else "○" if status == "PARTIAL" else "✗"
        print(f"  {icon} {desc}: {status} ({elapsed:.2f}s, {resp_len} chars)")
        if status == "PASS":
            passed += 1

    print(f"\n{'='*80}")
    print(f"OVERALL: {passed}/{len(test_cases)} tests passed")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_quick_execution())
