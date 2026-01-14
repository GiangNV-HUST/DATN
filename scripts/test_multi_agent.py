"""
Test script for Multi-Agent Query Handling

Tests the new multi-agent routing and execution capabilities.
"""

import asyncio
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from ai_agent_hybrid.hybrid_system.orchestrator.specialist_router import (
    SpecialistRouter,
    MultiAgentRoutingDecision
)


async def test_multi_agent_routing():
    """Test the multi-agent routing logic"""
    router = SpecialistRouter(use_cache=False)

    # Test cases for multi-agent queries
    test_queries = [
        # Sequential: Screen -> Invest
        {
            "query": "Loc co phieu P/E < 15, sau do tu van dau tu 100 trieu",
            "expected_multi": True,
            "expected_mode": "sequential",
            "expected_specialists": ["ScreenerSpecialist", "InvestmentPlanner"]
        },
        # Market -> Discovery (can be sequential or parallel, both valid)
        {
            "query": "VN-Index hom nay the nao? Goi y co phieu dang mua",
            "expected_multi": True,
            "expected_mode": ["sequential", "parallel"],  # Both modes are acceptable
            "expected_specialists": ["MarketContextSpecialist", "DiscoverySpecialist"]
        },
        # Sequential: Analyze -> Compare
        {
            "query": "Phan tich VCB va TCB, sau do so sanh xem cai nao tot hon",
            "expected_multi": True,
            "expected_mode": "sequential",
            "expected_specialists": ["AnalysisSpecialist", "ComparisonSpecialist"]
        },
        # Sequential: Screen -> Analyze
        {
            "query": "Loc top 5 co phieu tang manh nhat, phan tich chi tiet",
            "expected_multi": True,
            "expected_mode": "sequential",
            "expected_specialists": ["ScreenerSpecialist", "AnalysisSpecialist"]
        },
        # Single agent queries (should NOT be multi-agent)
        {
            "query": "Gia VCB hom nay",
            "expected_multi": False,
            "expected_mode": "single",
            "expected_specialists": ["AnalysisSpecialist"]
        },
        {
            "query": "Loc co phieu P/E < 15",
            "expected_multi": False,
            "expected_mode": "single",
            "expected_specialists": ["ScreenerSpecialist"]
        },
        {
            "query": "Tong quan thi truong",
            "expected_multi": False,
            "expected_mode": "single",
            "expected_specialists": ["MarketContextSpecialist"]
        },
    ]

    print("=" * 70)
    print("TESTING MULTI-AGENT ROUTING")
    print("=" * 70)

    passed = 0
    failed = 0

    for i, test in enumerate(test_queries, 1):
        query = test["query"]
        print(f"\n[Test {i}] Query: {query[:60]}...")

        try:
            decision = await router.route_multi_agent(query, "test_user")

            # Check results
            is_multi = decision.is_multi_agent
            mode = decision.execution_mode
            specialists = [t.specialist for t in decision.tasks]

            # Verify expectations
            multi_match = is_multi == test["expected_multi"]
            expected_modes = test["expected_mode"] if isinstance(test["expected_mode"], list) else [test["expected_mode"]]
            mode_match = mode in expected_modes

            # For multi-agent, check if expected specialists are present
            if test["expected_multi"]:
                specialists_match = all(s in specialists for s in test["expected_specialists"])
            else:
                specialists_match = specialists[0] == test["expected_specialists"][0]

            all_pass = multi_match and mode_match and specialists_match

            status = "PASS" if all_pass else "FAIL"
            if all_pass:
                passed += 1
            else:
                failed += 1

            print(f"  [{status}]")
            print(f"    is_multi_agent: {is_multi} (expected: {test['expected_multi']})")
            print(f"    execution_mode: {mode} (expected: {test['expected_mode']})")
            print(f"    specialists: {specialists}")
            print(f"    reasoning: {decision.reasoning[:80]}...")
            print(f"    confidence: {decision.confidence:.2f}")

        except Exception as e:
            failed += 1
            print(f"  [ERROR] {str(e)}")

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_queries)} tests")
    print("=" * 70)

    return passed, failed


async def test_fallback_routing():
    """Test fallback pattern matching for multi-agent queries"""
    router = SpecialistRouter(use_cache=False)

    print("\n" + "=" * 70)
    print("TESTING FALLBACK PATTERN MATCHING")
    print("=" * 70)

    # Test fallback directly
    test_queries = [
        "Loc co phieu P/E < 15, sau do tu van dau tu",
        "Thi truong hom nay the nao, goi y co phieu",
        "Phan tich VCB TCB roi so sanh",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        decision = router._fallback_multi_agent_routing(query, "test_user", "Test error")

        print(f"  is_multi_agent: {decision.is_multi_agent}")
        print(f"  execution_mode: {decision.execution_mode}")
        print(f"  tasks: {[(t.specialist, t.depends_on) for t in decision.tasks]}")


async def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("MULTI-AGENT QUERY HANDLING TEST SUITE")
    print("=" * 70)

    # Test routing logic
    passed, failed = await test_multi_agent_routing()

    # Test fallback
    await test_fallback_routing()

    print("\n" + "=" * 70)
    print("TEST SUITE COMPLETE")
    print("=" * 70)

    return passed, failed


if __name__ == "__main__":
    passed, failed = asyncio.run(main())
    sys.exit(0 if failed == 0 else 1)
