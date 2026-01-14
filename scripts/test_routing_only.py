"""
Test ROUTING ONLY for Multi-Agent System
Tests if queries are routed to correct specialists without full execution
"""

import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from src.ai_agent_hybrid.hybrid_system.orchestrator.specialist_router import SpecialistRouter


async def test_routing():
    """Test routing decisions without full execution"""
    print("\n" + "="*80)
    print("ROUTING LOGIC TEST (Fast - No Execution)")
    print("="*80)

    router = SpecialistRouter(use_cache=True)

    test_cases = [
        # Complex multi-agent queries
        {
            "query": "Phân tích chi tiết HPG, đánh giá bối cảnh thị trường thép, và cho tôi chiến lược đầu tư với 500 triệu",
            "expected_agents": ["AnalysisSpecialist", "MarketContextSpecialist", "InvestmentPlanner"],
            "min_agents": 2,
            "description": "Complex: Analysis + Market + Investment"
        },
        {
            "query": "So sánh FPT, VNM và MWG, kèm theo tin tức mới nhất",
            "expected_agents": ["ComparisonSpecialist"],
            "min_agents": 1,
            "description": "Comparison with news"
        },
        {
            "query": "Lọc top 5 cổ phiếu ngân hàng có PE thấp nhất và phân tích chi tiết",
            "expected_agents": ["ScreenerSpecialist", "AnalysisSpecialist"],
            "min_agents": 2,
            "description": "Screening + Analysis"
        },
        # Company name recognition
        {
            "query": "Giá cổ phiếu Vietcombank hôm nay",
            "expected_agents": ["AnalysisSpecialist"],
            "expected_symbol": "VCB",
            "description": "Company name: Vietcombank -> VCB"
        },
        {
            "query": "Phân tích Hòa Phát",
            "expected_agents": ["AnalysisSpecialist"],
            "expected_symbol": "HPG",
            "description": "Company name: Hòa Phát -> HPG"
        },
        {
            "query": "So sánh Techcombank và VCB",
            "expected_agents": ["ComparisonSpecialist"],
            "expected_symbols": ["TCB", "VCB"],
            "description": "Company names: Techcombank + VCB"
        },
        # Market context queries
        {
            "query": "Tình hình thị trường hôm nay",
            "expected_agents": ["MarketContextSpecialist"],
            "description": "Market overview"
        },
        {
            "query": "VN-Index giảm vì sao?",
            "expected_agents": ["MarketContextSpecialist"],
            "description": "Market analysis - VN-Index"
        },
        # Alert queries
        {
            "query": "Tạo cảnh báo khi VCB vượt 80000",
            "expected_agents": ["AlertManager"],
            "description": "Create price alert"
        },
        # Investment planning
        {
            "query": "Tôi có 500 triệu muốn đầu tư dài hạn",
            "expected_agents": ["InvestmentPlanner"],
            "description": "Investment planning"
        },
        # Screening queries
        {
            "query": "Top 10 cổ phiếu có ROE cao nhất",
            "expected_agents": ["ScreenerSpecialist"],
            "description": "Stock screening"
        },
        # Edge cases
        {
            "query": "FPT hay VNM tốt hơn?",
            "expected_agents": ["ComparisonSpecialist"],
            "expected_symbols": ["FPT", "VNM"],
            "description": "Simple comparison"
        },
        {
            "query": "Giá VCB",
            "expected_agents": ["AnalysisSpecialist"],
            "expected_symbol": "VCB",
            "description": "Simple price query"
        },
    ]

    results = []
    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test['description']} ---")
        print(f"Query: {test['query']}")

        start_time = time.time()

        try:
            # Use multi-agent routing
            routing = await router.route_multi_agent(test["query"], "test_user")
            elapsed = time.time() - start_time

            # Get agents from tasks
            agents_routed = [t.specialist for t in routing.tasks]
            symbols_extracted = []

            # Extract symbols from params
            for task in routing.tasks:
                if hasattr(task, 'params'):
                    if "symbol" in task.params:
                        symbols_extracted.append(task.params["symbol"])
                    if "symbols" in task.params:
                        symbols_extracted.extend(task.params["symbols"])

            print(f"  Routed to: {agents_routed}")
            print(f"  Symbols: {symbols_extracted}")
            print(f"  Mode: {'multi-agent' if routing.is_multi_agent else 'single-agent'} ({routing.execution_mode})")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Reasoning: {routing.reasoning[:80]}...")

            # Check expectations
            status = "PASS"
            issues = []

            # Check minimum agents
            min_agents = test.get("min_agents", 1)
            if len(agents_routed) < min_agents:
                status = "FAIL"
                issues.append(f"Expected at least {min_agents} agents, got {len(agents_routed)}")

            # Check expected agents
            expected_agents = test.get("expected_agents", [])
            for exp_agent in expected_agents:
                if exp_agent not in agents_routed:
                    if status == "PASS":
                        status = "PARTIAL"
                    issues.append(f"Missing {exp_agent}")

            # Check expected symbol
            expected_symbol = test.get("expected_symbol")
            if expected_symbol and expected_symbol not in symbols_extracted:
                if status == "PASS":
                    status = "PARTIAL"
                issues.append(f"Symbol {expected_symbol} not extracted")

            # Check expected symbols (for comparison)
            expected_symbols = test.get("expected_symbols", [])
            for exp_sym in expected_symbols:
                if exp_sym not in symbols_extracted:
                    if status == "PASS":
                        status = "PARTIAL"
                    issues.append(f"Symbol {exp_sym} not extracted")

            if issues:
                print(f"  Issues: {', '.join(issues)}")

            print(f"  Result: {status}")
            results.append((test['description'], status, elapsed))

            if status == "PASS":
                passed += 1
            else:
                failed += 1

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  ERROR: {str(e)[:100]}")
            results.append((test['description'], "ERROR", elapsed))
            failed += 1

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    for desc, status, elapsed in results:
        icon = "✓" if status == "PASS" else "○" if status == "PARTIAL" else "✗"
        print(f"  {icon} {desc}: {status} ({elapsed:.2f}s)")

    print(f"\n{'='*80}")
    print(f"OVERALL: {passed}/{len(test_cases)} tests passed ({failed} failed)")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_routing())
