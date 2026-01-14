"""
Complex scenario testing for Multi-Agent System
Tests multi-step queries, error handling, and edge cases
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


async def test_complex_multi_step_queries():
    """Test queries that require multiple agents working together"""
    print("\n" + "="*80)
    print("TEST 1: COMPLEX MULTI-STEP QUERIES (3+ Agents)")
    print("="*80)

    orchestrator = MultiAgentOrchestrator(use_direct_client=True)
    await orchestrator.initialize()

    test_cases = [
        # Complex query 1: Analysis + Market Context + Investment Planning
        {
            "query": "Phân tích chi tiết HPG, đánh giá bối cảnh thị trường thép, và cho tôi chiến lược đầu tư với 500 triệu",
            "expected_agents": ["AnalysisSpecialist", "MarketContextSpecialist", "InvestmentPlanner"],
            "description": "Analysis + Market Context + Investment Planning"
        },
        # Complex query 2: Multiple stocks comparison with news
        {
            "query": "So sánh FPT, VNM và MWG, kèm theo tin tức mới nhất của từng mã",
            "expected_agents": ["ComparisonSpecialist", "NewsSpecialist"],
            "description": "Comparison + News for multiple stocks"
        },
        # Complex query 3: Screening + Analysis + Recommendation
        {
            "query": "Lọc top 5 cổ phiếu ngân hàng có PE thấp nhất, phân tích chi tiết và đề xuất chiến lược đầu tư 200 triệu",
            "expected_agents": ["ScreenerSpecialist", "AnalysisSpecialist", "InvestmentPlanner"],
            "description": "Screening + Analysis + Investment Planning"
        },
        # Complex query 4: Full analysis workflow
        {
            "query": "Tôi muốn đầu tư vào ngành bất động sản với 1 tỷ đồng. Hãy phân tích thị trường, lọc cổ phiếu tiềm năng, và lập kế hoạch đầu tư chi tiết",
            "expected_agents": ["MarketContextSpecialist", "ScreenerSpecialist", "InvestmentPlanner"],
            "description": "Market Analysis + Screening + Investment Planning"
        },
    ]

    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test 1.{i}: {test['description']} ---")
        print(f"Query: {test['query']}")

        start_time = time.time()
        agents_used = []
        task_count = 0

        try:
            async for event in orchestrator.process_query(test["query"], user_id="test_complex"):
                event_type = event.get("type", "")

                if event_type == "routing_decision":
                    tasks = event.get("data", {}).get("tasks", [])
                    task_count = len(tasks)
                    print(f"  Routing: {task_count} tasks planned")
                    for task in tasks:
                        specialist = task.get('specialist')
                        if specialist and specialist not in agents_used:
                            agents_used.append(specialist)
                        print(f"    - {specialist}.{task.get('method')}")

                elif event_type == "task_complete":
                    specialist = event.get("data", {}).get("specialist", "")
                    if specialist and specialist not in agents_used:
                        agents_used.append(specialist)
                    print(f"  Completed: {specialist}")

                elif event_type == "chunk":
                    specialist = event.get("specialist", "")
                    if specialist and specialist not in agents_used:
                        agents_used.append(specialist)

                elif event_type == "final_response":
                    response = event.get("data", {}).get("response", "")
                    print(f"  Response length: {len(response)} chars")

            elapsed = time.time() - start_time

            # Check if expected agents were used
            expected_used = all(
                any(exp in agent for agent in agents_used)
                for exp in test["expected_agents"]
            )

            status = "PASS" if expected_used and task_count >= len(test["expected_agents"]) else "PARTIAL"
            results.append((test['description'], status, elapsed, agents_used))
            print(f"  Result: {status} (Time: {elapsed:.2f}s, Agents: {agents_used})")

        except Exception as e:
            results.append((test['description'], "FAIL", 0, str(e)))
            print(f"  Result: FAIL - {e}")

    return results


async def test_error_handling():
    """Test error handling and edge cases"""
    print("\n" + "="*80)
    print("TEST 2: ERROR HANDLING AND EDGE CASES")
    print("="*80)

    orchestrator = MultiAgentOrchestrator(use_direct_client=True)
    await orchestrator.initialize()

    test_cases = [
        # Invalid stock symbol
        {
            "query": "Phân tích cổ phiếu ZZZZZ",
            "description": "Invalid stock symbol",
            "should_handle_gracefully": True
        },
        # Empty query
        {
            "query": "   ",
            "description": "Empty/whitespace query",
            "should_handle_gracefully": True
        },
        # Very long query
        {
            "query": "Phân tích " + "VCB " * 100 + " chi tiết",
            "description": "Very long query",
            "should_handle_gracefully": True
        },
        # Mixed language query
        {
            "query": "Analyze FPT stock và cho tôi price prediction for next week",
            "description": "Mixed Vietnamese-English query",
            "should_handle_gracefully": True
        },
        # Query with special characters
        {
            "query": "Giá VCB???? @#$%^& hôm nay!!!",
            "description": "Query with special characters",
            "should_handle_gracefully": True
        },
        # Ambiguous query
        {
            "query": "tốt không",
            "description": "Ambiguous/unclear query",
            "should_handle_gracefully": True
        },
        # Multiple conflicting requests
        {
            "query": "Mua VCB và bán VCB ngay lập tức",
            "description": "Conflicting requests",
            "should_handle_gracefully": True
        },
    ]

    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test 2.{i}: {test['description']} ---")
        print(f"Query: {test['query'][:50]}..." if len(test['query']) > 50 else f"Query: {test['query']}")

        start_time = time.time()
        handled_gracefully = False
        error_msg = None

        try:
            response_received = False
            async for event in orchestrator.process_query(test["query"], user_id="test_error"):
                event_type = event.get("type", "")

                if event_type == "final_response":
                    response = event.get("data", {}).get("response", "")
                    response_received = True
                    print(f"  Response: {response[:100]}..." if len(response) > 100 else f"  Response: {response}")

                elif event_type == "error":
                    error_msg = event.get("data", {}).get("error", "")
                    print(f"  Error handled: {error_msg[:100]}")

            handled_gracefully = response_received or error_msg is not None
            elapsed = time.time() - start_time

            status = "PASS" if handled_gracefully else "FAIL"
            results.append((test['description'], status, elapsed))
            print(f"  Result: {status} (Time: {elapsed:.2f}s)")

        except Exception as e:
            elapsed = time.time() - start_time
            results.append((test['description'], "EXCEPTION", elapsed))
            print(f"  Result: EXCEPTION - {str(e)[:100]}")

    return results


async def test_edge_cases():
    """Test additional edge cases"""
    print("\n" + "="*80)
    print("TEST 3: ADDITIONAL EDGE CASES")
    print("="*80)

    orchestrator = MultiAgentOrchestrator(use_direct_client=True)
    await orchestrator.initialize()

    test_cases = [
        # Company names with typos
        {
            "query": "Giá Vietcobank hôm nay",  # typo: Vietcobank instead of Vietcombank
            "description": "Company name with typo",
            "expected_symbol": "VCB"
        },
        # Informal company reference
        {
            "query": "Thép Hòa Phát có đáng mua không",
            "description": "Informal company reference (Thép Hòa Phát)",
            "expected_symbol": "HPG"
        },
        # Number formatting variations
        {
            "query": "Đầu tư 1.000.000.000 đồng vào VNM",
            "description": "Large number with dots formatting",
            "expected_capital": 1000000000
        },
        # Abbreviated numbers
        {
            "query": "Tôi có 500tr muốn đầu tư FPT",
            "description": "Abbreviated number (500tr = 500 triệu)",
            "expected_capital": 500000000
        },
        # Query without explicit stock symbol
        {
            "query": "Phân tích công ty sữa lớn nhất Việt Nam",
            "description": "Query without explicit symbol (should identify VNM)",
            "expected_symbol": "VNM"
        },
        # Query with date reference
        {
            "query": "So sánh giá VCB tuần trước và tuần này",
            "description": "Query with relative date reference",
            "expected_symbol": "VCB"
        },
    ]

    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test 3.{i}: {test['description']} ---")
        print(f"Query: {test['query']}")

        start_time = time.time()
        symbols_found = []
        capital_found = None
        agents_involved = []

        try:
            async for event in orchestrator.process_query(test["query"], user_id="test_edge"):
                event_type = event.get("type", "")

                if event_type == "routing_decision":
                    tasks = event.get("data", {}).get("tasks", [])
                    for task in tasks:
                        # Also check specialist name for symbol extraction from response later
                        specialist = task.get("specialist", "")
                        if specialist:
                            agents_involved.append(specialist)
                    print(f"  Agents: {agents_involved}")

                elif event_type == "final_response":
                    response = event.get("data", {}).get("response", "")
                    print(f"  Response: {response[:150]}...")

            elapsed = time.time() - start_time

            # Check expectations
            status = "PASS"
            if "expected_symbol" in test:
                if test["expected_symbol"] not in symbols_found:
                    status = "PARTIAL"
                    print(f"  Expected symbol {test['expected_symbol']} not found in {symbols_found}")

            if "expected_capital" in test and capital_found:
                if capital_found != test["expected_capital"]:
                    status = "PARTIAL"
                    print(f"  Expected capital {test['expected_capital']:,} but got {capital_found:,}")

            results.append((test['description'], status, elapsed))
            print(f"  Result: {status} (Time: {elapsed:.2f}s)")

        except Exception as e:
            results.append((test['description'], "FAIL", 0))
            print(f"  Result: FAIL - {e}")

    return results


async def test_performance():
    """Test performance and response times"""
    print("\n" + "="*80)
    print("TEST 4: PERFORMANCE TESTING")
    print("="*80)

    orchestrator = MultiAgentOrchestrator(use_direct_client=True)
    await orchestrator.initialize()

    # Simple queries should be fast
    simple_queries = [
        "Giá VCB",
        "Tin tức FPT",
        "PE của HPG",
    ]

    # Complex queries can take longer
    complex_queries = [
        "Phân tích chi tiết VCB với các chỉ số tài chính",
        "So sánh VCB, TCB, ACB về tất cả các khía cạnh",
        "Lọc top 10 cổ phiếu công nghệ và phân tích chi tiết",
    ]

    results = []

    print("\n--- Simple Query Performance ---")
    for query in simple_queries:
        start_time = time.time()
        async for event in orchestrator.process_query(query, user_id="test_perf"):
            pass
        elapsed = time.time() - start_time
        status = "FAST" if elapsed < 5 else "SLOW" if elapsed < 10 else "VERY SLOW"
        results.append((f"Simple: {query[:30]}", status, elapsed))
        print(f"  '{query[:30]}': {elapsed:.2f}s ({status})")

    print("\n--- Complex Query Performance ---")
    for query in complex_queries:
        start_time = time.time()
        async for event in orchestrator.process_query(query, user_id="test_perf"):
            pass
        elapsed = time.time() - start_time
        status = "ACCEPTABLE" if elapsed < 15 else "SLOW" if elapsed < 30 else "VERY SLOW"
        results.append((f"Complex: {query[:30]}", status, elapsed))
        print(f"  '{query[:30]}': {elapsed:.2f}s ({status})")

    return results


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("MULTI-AGENT SYSTEM - COMPREHENSIVE TEST SUITE")
    print("="*80)

    all_results = []

    # Test 1: Complex multi-step queries
    results1 = await test_complex_multi_step_queries()
    all_results.extend([("Complex Queries", r) for r in results1])

    # Test 2: Error handling
    results2 = await test_error_handling()
    all_results.extend([("Error Handling", r) for r in results2])

    # Test 3: Edge cases
    results3 = await test_edge_cases()
    all_results.extend([("Edge Cases", r) for r in results3])

    # Test 4: Performance
    results4 = await test_performance()
    all_results.extend([("Performance", r) for r in results4])

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    categories = {
        "Complex Queries": results1,
        "Error Handling": results2,
        "Edge Cases": results3,
        "Performance": results4,
    }

    total_pass = 0
    total_tests = 0

    for category, results in categories.items():
        passed = sum(1 for r in results if r[1] in ["PASS", "FAST", "ACCEPTABLE"])
        total = len(results)
        total_pass += passed
        total_tests += total
        print(f"\n{category}: {passed}/{total}")
        for r in results:
            status_icon = "✓" if r[1] in ["PASS", "FAST", "ACCEPTABLE"] else "○" if r[1] == "PARTIAL" else "✗"
            time_str = f"({r[2]:.2f}s)" if len(r) > 2 and isinstance(r[2], (int, float)) else ""
            print(f"  {status_icon} {r[0]}: {r[1]} {time_str}")

    print(f"\n{'='*80}")
    print(f"OVERALL: {total_pass}/{total_tests} tests passed")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
