"""
Full System Test for 8 Agents Multi-Agent System

This script tests:
1. AI Router routing accuracy (37 test cases)
2. Agent execution with real queries
3. End-to-end performance metrics

Tests all 8 agents:
1. AnalysisSpecialist - Stock analysis
2. ScreenerSpecialist - Stock screening
3. AlertManager - Alerts
4. InvestmentPlanner - Investment planning
5. DiscoverySpecialist - Stock discovery
6. SubscriptionManager - Watchlist
7. MarketContextSpecialist - Market overview [NEW]
8. ComparisonSpecialist - Stock comparison [NEW]
"""

import asyncio
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add paths
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()


# ============================================================================
# TEST QUERIES FOR EACH AGENT
# ============================================================================

# Routing test cases (for accuracy measurement)
ROUTING_TEST_CASES = [
    # AnalysisSpecialist (5 cases)
    {"query": "Phan tich co phieu VCB", "expected": "AnalysisSpecialist"},
    {"query": "Gia FPT hom nay bao nhieu?", "expected": "AnalysisSpecialist"},
    {"query": "Du doan gia VNM 3 ngay toi", "expected": "AnalysisSpecialist"},
    {"query": "RSI cua HPG bao nhieu roi?", "expected": "AnalysisSpecialist"},
    {"query": "VCB co nen mua khong?", "expected": "AnalysisSpecialist"},

    # ScreenerSpecialist (5 cases)
    {"query": "Loc co phieu P/E < 15 va ROE > 20%", "expected": "ScreenerSpecialist"},
    {"query": "Top 10 co phieu thanh khoan cao nhat", "expected": "ScreenerSpecialist"},
    {"query": "Tim co phieu ngan hang co P/B < 2", "expected": "ScreenerSpecialist"},
    {"query": "Co phieu nao tang manh nhat tuan nay?", "expected": "ScreenerSpecialist"},
    {"query": "Sang loc co phieu von hoa lon EPS > 3000", "expected": "ScreenerSpecialist"},

    # DiscoverySpecialist (4 cases)
    {"query": "Co phieu nao dang mua nhat bay gio?", "expected": "DiscoverySpecialist"},
    {"query": "Goi y co phieu tiem nang", "expected": "DiscoverySpecialist"},
    {"query": "Kham pha co hoi dau tu nganh cong nghe", "expected": "DiscoverySpecialist"},
    {"query": "Nen mua co phieu gi?", "expected": "DiscoverySpecialist"},

    # AlertManager (3 cases)
    {"query": "Tao canh bao khi VCB vuot 95000", "expected": "AlertManager"},
    {"query": "Canh bao cua toi", "expected": "AlertManager"},
    {"query": "Xoa canh bao so 3", "expected": "AlertManager"},

    # InvestmentPlanner (4 cases)
    {"query": "Toi co 100 trieu muon dau tu", "expected": "InvestmentPlanner"},
    {"query": "Tu van danh muc 500 trieu cho nguoi moi", "expected": "InvestmentPlanner"},
    {"query": "Ke hoach DCA cho VCB 10 trieu/thang", "expected": "InvestmentPlanner"},
    {"query": "Chien luoc dau tu an toan dai han", "expected": "InvestmentPlanner"},

    # SubscriptionManager (3 cases)
    {"query": "Theo doi co phieu FPT", "expected": "SubscriptionManager"},
    {"query": "Danh sach co phieu toi dang theo doi", "expected": "SubscriptionManager"},
    {"query": "Bo theo doi VCB", "expected": "SubscriptionManager"},

    # MarketContextSpecialist (6 cases) [NEW]
    {"query": "VN-Index hom nay nhu the nao?", "expected": "MarketContextSpecialist"},
    {"query": "Tai sao thi truong giam?", "expected": "MarketContextSpecialist"},
    {"query": "Nganh nao dang hot?", "expected": "MarketContextSpecialist"},
    {"query": "Tong quan thi truong", "expected": "MarketContextSpecialist"},
    {"query": "Khoi ngoai dang mua hay ban?", "expected": "MarketContextSpecialist"},
    {"query": "Market breadth hom nay", "expected": "MarketContextSpecialist"},

    # ComparisonSpecialist (5 cases) [NEW]
    {"query": "So sanh VCB voi TCB", "expected": "ComparisonSpecialist"},
    {"query": "FPT hay CMG tot hon?", "expected": "ComparisonSpecialist"},
    {"query": "So sanh P/E cua VCB, TCB, MBB", "expected": "ComparisonSpecialist"},
    {"query": "VCB vs TCB cai nao dang mua hon?", "expected": "ComparisonSpecialist"},
    {"query": "Peer comparison cho VCB trong nganh ngan hang", "expected": "ComparisonSpecialist"},

    # Edge cases (2 cases)
    {"query": "VCB", "expected": "AnalysisSpecialist"},
    {"query": "FPT tang hay giam?", "expected": "AnalysisSpecialist"},
]

# Execution test queries (for real agent execution)
EXECUTION_TEST_QUERIES = [
    {
        "agent": "AnalysisSpecialist",
        "query": "Phan tich ky thuat co phieu FPT",
        "description": "Technical analysis for FPT"
    },
    {
        "agent": "ScreenerSpecialist",
        "query": "Loc top 5 co phieu von hoa lon nhat",
        "description": "Screen top 5 large cap stocks"
    },
    {
        "agent": "DiscoverySpecialist",
        "query": "Goi y co phieu tiem nang nganh ngan hang",
        "description": "Discover banking stocks"
    },
    {
        "agent": "MarketContextSpecialist",
        "query": "Tong quan thi truong hom nay",
        "description": "Market overview today"
    },
    {
        "agent": "ComparisonSpecialist",
        "query": "So sanh VCB va TCB",
        "description": "Compare VCB vs TCB"
    },
    {
        "agent": "InvestmentPlanner",
        "query": "Tu van danh muc 100 trieu cho nguoi moi bat dau",
        "description": "Portfolio advice for 100M VND"
    },
    {
        "agent": "AlertManager",
        "query": "Xem danh sach canh bao cua toi",
        "description": "View my alerts"
    },
    {
        "agent": "SubscriptionManager",
        "query": "Danh sach co phieu toi dang theo doi",
        "description": "View watchlist"
    },
]


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

async def test_routing_accuracy():
    """Test AI Router routing accuracy"""
    print("\n" + "=" * 70)
    print("PHASE 1: ROUTING ACCURACY TEST")
    print("=" * 70 + "\n")

    from src.ai_agent_hybrid.hybrid_system.orchestrator.specialist_router import SpecialistRouter

    router = SpecialistRouter(use_cache=False)

    correct = 0
    total = len(ROUTING_TEST_CASES)
    total_time = 0
    agent_stats = {}
    failures = []

    for i, test in enumerate(ROUTING_TEST_CASES, 1):
        query = test["query"]
        expected = test["expected"]

        start = time.time()
        try:
            decision = await router.route(query, "test_user")
            elapsed = time.time() - start
            total_time += elapsed

            actual = decision.specialist
            is_correct = actual == expected

            if is_correct:
                correct += 1
                status = "OK"
            else:
                status = "FAIL"
                failures.append({
                    "query": query,
                    "expected": expected,
                    "actual": actual,
                    "reasoning": decision.reasoning
                })

            # Track per-agent stats
            if expected not in agent_stats:
                agent_stats[expected] = {"correct": 0, "total": 0}
            agent_stats[expected]["total"] += 1
            if is_correct:
                agent_stats[expected]["correct"] += 1

            print(f"{i:2}. [{status:4}] {query[:45]:<45} -> {actual}")

        except Exception as e:
            print(f"{i:2}. [ERR ] {query[:45]:<45} -> ERROR: {e}")

    accuracy = (correct / total) * 100
    avg_time_ms = (total_time / total) * 1000

    print("\n" + "-" * 70)
    print(f"ROUTING ACCURACY: {correct}/{total} ({accuracy:.1f}%)")
    print(f"Average routing time: {avg_time_ms:.0f}ms")
    print("-" * 70)

    # Per-agent accuracy
    print("\nPER-AGENT ACCURACY:")
    for agent, stats in sorted(agent_stats.items()):
        acc = (stats["correct"] / stats["total"]) * 100
        print(f"  {agent:25} {stats['correct']}/{stats['total']} ({acc:.0f}%)")

    # Show failures
    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for f in failures:
            print(f"  - Query: {f['query']}")
            print(f"    Expected: {f['expected']} | Got: {f['actual']}")

    return {
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "avg_time_ms": avg_time_ms,
        "agent_stats": agent_stats,
        "failures": failures
    }


async def test_agent_execution():
    """Test actual agent execution with real queries"""
    print("\n" + "=" * 70)
    print("PHASE 2: AGENT EXECUTION TEST")
    print("=" * 70 + "\n")

    from src.ai_agent_hybrid.hybrid_system.orchestrator.multi_agent_orchestrator import MultiAgentOrchestrator

    # Initialize orchestrator with DirectMCPClient (no subprocess)
    print("Initializing MultiAgentOrchestrator with 8 agents (using DirectMCPClient)...")
    orchestrator = MultiAgentOrchestrator(use_direct_client=True)
    await orchestrator.initialize()
    print("Orchestrator initialized successfully!\n")

    results = []
    total_time = 0
    successful = 0

    for i, test in enumerate(EXECUTION_TEST_QUERIES, 1):
        agent = test["agent"]
        query = test["query"]
        desc = test["description"]

        print(f"\n{'-' * 60}")
        print(f"Test {i}: {desc}")
        print(f"Query: {query}")
        print(f"Expected Agent: {agent}")
        print(f"{'-' * 60}")

        start = time.time()
        try:
            # Execute query through orchestrator
            response_chunks = []
            async for event in orchestrator.process_query(query, f"test_user_{i}"):
                # Handle dict events from orchestrator
                if isinstance(event, dict):
                    event_type = event.get("type", "")
                    event_data = event.get("data", "")

                    if event_type == "chunk":
                        response_chunks.append(str(event_data))
                    elif event_type == "complete":
                        if isinstance(event_data, dict):
                            response_chunks.append(str(event_data.get("response", "")))
                    elif event_type == "error":
                        response_chunks.append(f"[ERROR] {event_data}")
                else:
                    response_chunks.append(str(event))

            elapsed = time.time() - start
            total_time += elapsed

            response = "".join(response_chunks)

            # Check if response is valid
            has_error = "[ERROR]" in response or "Loi" in response.lower()
            is_success = len(response) > 50 and not has_error

            if is_success:
                successful += 1
                status = "SUCCESS"
            else:
                status = "PARTIAL" if len(response) > 0 else "FAILED"

            # Print truncated response
            preview = response[:500] + "..." if len(response) > 500 else response
            print(f"\nStatus: {status}")
            print(f"Time: {elapsed:.2f}s")
            print(f"Response length: {len(response)} chars")
            print(f"\nResponse Preview:\n{preview}")

            results.append({
                "agent": agent,
                "query": query,
                "status": status,
                "time": elapsed,
                "response_length": len(response),
                "success": is_success
            })

        except Exception as e:
            elapsed = time.time() - start
            print(f"\nStatus: ERROR")
            print(f"Error: {str(e)}")
            results.append({
                "agent": agent,
                "query": query,
                "status": "ERROR",
                "time": elapsed,
                "response_length": 0,
                "success": False,
                "error": str(e)
            })

    # Cleanup
    if hasattr(orchestrator, 'close'):
        await orchestrator.close()
    elif hasattr(orchestrator, 'mcp_client') and hasattr(orchestrator.mcp_client, 'disconnect'):
        await orchestrator.mcp_client.disconnect()

    # Summary
    success_rate = (successful / len(EXECUTION_TEST_QUERIES)) * 100
    avg_time = total_time / len(EXECUTION_TEST_QUERIES)

    print("\n" + "=" * 70)
    print("EXECUTION TEST SUMMARY")
    print("=" * 70)
    print(f"Success Rate: {successful}/{len(EXECUTION_TEST_QUERIES)} ({success_rate:.1f}%)")
    print(f"Average execution time: {avg_time:.2f}s")
    print(f"Total time: {total_time:.2f}s")

    # Per-agent results
    print("\nPER-AGENT RESULTS:")
    for r in results:
        status_icon = "OK" if r["success"] else "X"
        print(f"  [{status_icon}] {r['agent']:25} - {r['time']:.2f}s - {r['response_length']} chars")

    return {
        "success_rate": success_rate,
        "successful": successful,
        "total": len(EXECUTION_TEST_QUERIES),
        "avg_time": avg_time,
        "results": results
    }


async def test_end_to_end_scenarios():
    """Test complete end-to-end scenarios"""
    print("\n" + "=" * 70)
    print("PHASE 3: END-TO-END SCENARIO TESTS")
    print("=" * 70 + "\n")

    from src.ai_agent_hybrid.hybrid_system.orchestrator.multi_agent_orchestrator import MultiAgentOrchestrator

    # Complex scenarios that may involve multiple agents or edge cases
    scenarios = [
        {
            "name": "Market Overview + Stock Analysis",
            "queries": [
                "Thi truong hom nay nhu the nao?",
                "Phan tich chi tiet co phieu FPT"
            ]
        },
        {
            "name": "Stock Comparison + Investment Planning",
            "queries": [
                "So sanh VCB va TCB cai nao tot hon?",
                "Toi co 50 trieu, nen mua VCB hay TCB?"
            ]
        },
        {
            "name": "Discovery + Screening",
            "queries": [
                "Tim co phieu tiem nang nganh cong nghe",
                "Loc co phieu cong nghe co P/E < 20"
            ]
        },
    ]

    orchestrator = MultiAgentOrchestrator(use_direct_client=True)
    await orchestrator.initialize()

    scenario_results = []

    for scenario in scenarios:
        print(f"\n{'='*60}")
        print(f"SCENARIO: {scenario['name']}")
        print(f"{'='*60}")

        scenario_success = True
        for query in scenario["queries"]:
            print(f"\n> Query: {query}")

            start = time.time()
            try:
                response_chunks = []
                async for event in orchestrator.process_query(query, "scenario_test"):
                    if isinstance(event, dict):
                        event_type = event.get("type", "")
                        event_data = event.get("data", "")
                        if event_type == "chunk":
                            response_chunks.append(str(event_data))
                        elif event_type == "complete":
                            if isinstance(event_data, dict):
                                response_chunks.append(str(event_data.get("response", "")))
                    else:
                        response_chunks.append(str(event))

                response = "".join(response_chunks)
                elapsed = time.time() - start

                # Check success
                has_content = len(response) > 100
                has_error = "[ERROR]" in response

                if has_content and not has_error:
                    print(f"  Status: SUCCESS ({elapsed:.2f}s, {len(response)} chars)")
                else:
                    print(f"  Status: FAILED ({elapsed:.2f}s)")
                    scenario_success = False

            except Exception as e:
                print(f"  Status: ERROR - {str(e)}")
                scenario_success = False

        scenario_results.append({
            "name": scenario["name"],
            "success": scenario_success
        })

    # Cleanup
    if hasattr(orchestrator, 'close'):
        await orchestrator.close()
    elif hasattr(orchestrator, 'mcp_client') and hasattr(orchestrator.mcp_client, 'disconnect'):
        await orchestrator.mcp_client.disconnect()

    # Summary
    passed = sum(1 for s in scenario_results if s["success"])
    print(f"\n{'='*60}")
    print(f"SCENARIO RESULTS: {passed}/{len(scenarios)} passed")
    print(f"{'='*60}")

    for s in scenario_results:
        icon = "PASS" if s["success"] else "FAIL"
        print(f"  [{icon}] {s['name']}")

    return scenario_results


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run full system test"""
    print("\n")
    print("=" * 70)
    print("FULL SYSTEM TEST - 8 AGENTS MULTI-AGENT SYSTEM")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    overall_start = time.time()

    # Phase 1: Routing Accuracy
    routing_results = await test_routing_accuracy()

    # Phase 2: Agent Execution
    execution_results = await test_agent_execution()

    # Phase 3: End-to-End Scenarios
    scenario_results = await test_end_to_end_scenarios()

    overall_time = time.time() - overall_start

    # Final Report
    print("\n")
    print("=" * 70)
    print("FINAL TEST REPORT")
    print("=" * 70)

    print(f"""
+----------------------------------+------------------+
| METRIC                           | RESULT           |
+----------------------------------+------------------+
| Routing Accuracy                 | {routing_results['accuracy']:.1f}%            |
| Routing Avg Time                 | {routing_results['avg_time_ms']:.0f}ms             |
| Execution Success Rate           | {execution_results['success_rate']:.1f}%            |
| Execution Avg Time               | {execution_results['avg_time']:.2f}s            |
| Scenarios Passed                 | {sum(1 for s in scenario_results if s['success'])}/{len(scenario_results)}              |
| Total Test Time                  | {overall_time:.2f}s           |
+----------------------------------+------------------+
""")

    # Overall assessment
    routing_ok = routing_results['accuracy'] >= 90
    execution_ok = execution_results['success_rate'] >= 75
    scenarios_ok = all(s['success'] for s in scenario_results)

    if routing_ok and execution_ok:
        print("OVERALL STATUS: PASS")
        print("The 8-agent system is working correctly!")
    else:
        print("OVERALL STATUS: NEEDS IMPROVEMENT")
        if not routing_ok:
            print("- Routing accuracy below 90%")
        if not execution_ok:
            print("- Execution success rate below 75%")
        if not scenarios_ok:
            print("- Some scenarios failed")

    print("\n" + "=" * 70)
    print("TEST COMPLETED")
    print("=" * 70 + "\n")

    return {
        "routing": routing_results,
        "execution": execution_results,
        "scenarios": scenario_results,
        "total_time": overall_time
    }


if __name__ == "__main__":
    asyncio.run(main())
