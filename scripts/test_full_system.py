"""
Comprehensive System Test for Multi-Agent Stock Analysis
Tests all aspects: routing, execution, data flow, error handling
"""

import asyncio
import sys
import os
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from src.ai_agent_hybrid.hybrid_system.orchestrator.multi_agent_orchestrator import MultiAgentOrchestrator
from src.ai_agent_hybrid.hybrid_system.orchestrator.specialist_router import SpecialistRouter


class SystemTester:
    def __init__(self):
        self.results = {
            "routing": [],
            "single_agent": [],
            "multi_agent_sequential": [],
            "multi_agent_parallel": [],
            "error_handling": [],
            "data_flow": []
        }
        self.orchestrator = None
        self.router = None

    async def initialize(self):
        """Initialize orchestrator and router"""
        print("Initializing system...")
        self.orchestrator = MultiAgentOrchestrator(use_direct_client=True)
        await self.orchestrator.initialize()
        self.router = SpecialistRouter(use_cache=False)  # No cache for accurate testing
        print("System initialized!\n")

    async def test_routing_accuracy(self):
        """Test 1: Routing Logic Accuracy"""
        print("="*80)
        print("TEST 1: ROUTING LOGIC ACCURACY")
        print("="*80)

        test_cases = [
            # Single agent queries
            {"query": "Giá VCB hôm nay", "expected_agents": ["AnalysisSpecialist"], "type": "single"},
            {"query": "Top 10 cổ phiếu PE thấp nhất", "expected_agents": ["ScreenerSpecialist"], "type": "single"},
            {"query": "Tạo cảnh báo VCB vượt 80000", "expected_agents": ["AlertManager"], "type": "single"},
            {"query": "VN-Index hôm nay thế nào", "expected_agents": ["MarketContextSpecialist"], "type": "single"},
            {"query": "So sánh VCB và TCB", "expected_agents": ["ComparisonSpecialist"], "type": "single"},
            {"query": "Tôi có 500 triệu muốn đầu tư", "expected_agents": ["InvestmentPlanner"], "type": "single"},

            # Multi-agent queries
            {"query": "Phân tích HPG và cho tôi kế hoạch đầu tư 300 triệu",
             "expected_agents": ["AnalysisSpecialist", "InvestmentPlanner"], "type": "multi"},
            {"query": "Lọc top 5 cổ phiếu ngân hàng PE thấp rồi phân tích chi tiết",
             "expected_agents": ["ScreenerSpecialist", "AnalysisSpecialist"], "type": "multi"},
            {"query": "Đánh giá thị trường và đề xuất cổ phiếu tiềm năng với 1 tỷ",
             "expected_agents": ["MarketContextSpecialist", "ScreenerSpecialist", "InvestmentPlanner"], "type": "multi"},

            # Company name recognition
            {"query": "Phân tích Vietcombank", "expected_symbol": "VCB", "type": "symbol"},
            {"query": "Giá Hòa Phát", "expected_symbol": "HPG", "type": "symbol"},
            {"query": "So sánh Techcombank và ACB", "expected_symbols": ["TCB", "ACB"], "type": "symbols"},
        ]

        passed = 0
        for i, test in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] {test['query'][:50]}...")

            try:
                routing = await self.router.route_multi_agent(test["query"], "test_user")
                agents = [t.specialist for t in routing.tasks]
                symbols = []
                for t in routing.tasks:
                    if hasattr(t, 'params'):
                        symbols.extend(t.params.get("symbols", []))
                        if t.params.get("symbol"):
                            symbols.append(t.params["symbol"])

                # Check expectations
                status = "PASS"
                issues = []

                if test["type"] == "single":
                    if not all(exp in agents for exp in test["expected_agents"]):
                        status = "FAIL"
                        issues.append(f"Expected {test['expected_agents']}, got {agents}")
                elif test["type"] == "multi":
                    missing = [exp for exp in test["expected_agents"] if exp not in agents]
                    if missing:
                        status = "PARTIAL"
                        issues.append(f"Missing: {missing}")
                elif test["type"] == "symbol":
                    if test["expected_symbol"] not in symbols:
                        status = "FAIL"
                        issues.append(f"Symbol {test['expected_symbol']} not found in {symbols}")
                elif test["type"] == "symbols":
                    missing = [s for s in test["expected_symbols"] if s not in symbols]
                    if missing:
                        status = "FAIL"
                        issues.append(f"Symbols {missing} not found in {symbols}")

                if status == "PASS":
                    passed += 1
                    print(f"   ✓ PASS - Agents: {agents}")
                else:
                    print(f"   ✗ {status} - {issues}")

                self.results["routing"].append({
                    "query": test["query"],
                    "status": status,
                    "agents": agents,
                    "symbols": symbols
                })

            except Exception as e:
                print(f"   ✗ ERROR: {str(e)[:80]}")
                self.results["routing"].append({"query": test["query"], "status": "ERROR", "error": str(e)})

        print(f"\nRouting Test: {passed}/{len(test_cases)} passed")
        return passed, len(test_cases)

    async def test_single_agent_execution(self):
        """Test 2: Single Agent Execution"""
        print("\n" + "="*80)
        print("TEST 2: SINGLE AGENT EXECUTION")
        print("="*80)

        test_cases = [
            {"query": "Giá VCB", "min_response_length": 100},
            {"query": "Top 5 cổ phiếu ROE cao nhất", "min_response_length": 50},
            {"query": "So sánh FPT và VNM", "min_response_length": 100},
        ]

        passed = 0
        for i, test in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] {test['query']}")

            start_time = time.time()
            response_chunks = []
            events_received = []

            try:
                async for event in self.orchestrator.process_query(test["query"], user_id="test_single"):
                    event_type = event.get("type", "")
                    events_received.append(event_type)

                    if event_type == "chunk":
                        chunk = event.get("data", "")
                        if isinstance(chunk, str):
                            response_chunks.append(chunk)
                    elif event_type == "routing_decision":
                        tasks = event.get("data", {}).get("tasks", [])
                        print(f"   Routed to: {[t['specialist'] for t in tasks]}")

                elapsed = time.time() - start_time
                full_response = "".join(response_chunks)

                # Check quality
                has_response = len(full_response) >= test["min_response_length"]
                has_routing = "routing_decision" in events_received

                if has_response and has_routing:
                    passed += 1
                    print(f"   ✓ PASS - {len(full_response)} chars, {elapsed:.1f}s")
                else:
                    print(f"   ✗ FAIL - Response: {len(full_response)} chars (min: {test['min_response_length']})")

                self.results["single_agent"].append({
                    "query": test["query"],
                    "status": "PASS" if has_response else "FAIL",
                    "response_length": len(full_response),
                    "time": elapsed
                })

            except Exception as e:
                print(f"   ✗ ERROR: {str(e)[:80]}")
                self.results["single_agent"].append({"query": test["query"], "status": "ERROR", "error": str(e)})

        print(f"\nSingle Agent Test: {passed}/{len(test_cases)} passed")
        return passed, len(test_cases)

    async def test_multi_agent_sequential(self):
        """Test 3: Multi-Agent Sequential Execution"""
        print("\n" + "="*80)
        print("TEST 3: MULTI-AGENT SEQUENTIAL EXECUTION")
        print("="*80)

        test_cases = [
            {
                "query": "Lọc top 3 cổ phiếu ngân hàng PE thấp và phân tích chi tiết",
                "expected_flow": ["ScreenerSpecialist", "AnalysisSpecialist"],
                "check_data_passing": True
            },
            {
                "query": "Phân tích VCB và lập kế hoạch đầu tư 200 triệu",
                "expected_flow": ["AnalysisSpecialist", "InvestmentPlanner"],
                "check_data_passing": True
            },
        ]

        passed = 0
        for i, test in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] {test['query'][:60]}...")

            start_time = time.time()
            agents_executed = []
            task_results = {}

            try:
                async for event in self.orchestrator.process_query(test["query"], user_id="test_seq"):
                    event_type = event.get("type", "")

                    if event_type == "routing_decision":
                        data = event.get("data", {})
                        mode = data.get("execution_mode", "unknown")
                        tasks = data.get("tasks", [])
                        print(f"   Mode: {mode}, Tasks: {len(tasks)}")
                        for t in tasks:
                            print(f"      - {t['specialist']}.{t['method']}")

                    elif event_type == "task_complete":
                        data = event.get("data", {})
                        specialist = data.get("specialist", "")
                        result = data.get("result", "")
                        agents_executed.append(specialist)
                        task_results[specialist] = result[:200]
                        print(f"   Completed: {specialist} ({len(result)} chars)")

                    elif event_type == "status":
                        print(f"   Status: {event.get('data', '')}")

                elapsed = time.time() - start_time

                # Check execution order
                flow_correct = True
                for j, expected in enumerate(test["expected_flow"]):
                    if j < len(agents_executed):
                        if agents_executed[j] != expected:
                            flow_correct = False
                    else:
                        flow_correct = False

                # Check data was passed between agents
                data_passed = True
                if test["check_data_passing"] and len(task_results) >= 2:
                    # Second agent should have received first agent's context
                    # This is implicit - we check if both produced meaningful results
                    for specialist, result in task_results.items():
                        if len(result) < 50:
                            data_passed = False

                status = "PASS" if flow_correct and data_passed else "PARTIAL" if data_passed else "FAIL"
                if status == "PASS":
                    passed += 1

                print(f"   Result: {status} - Flow: {agents_executed}, Time: {elapsed:.1f}s")

                self.results["multi_agent_sequential"].append({
                    "query": test["query"],
                    "status": status,
                    "agents_executed": agents_executed,
                    "time": elapsed
                })

            except Exception as e:
                print(f"   ✗ ERROR: {str(e)[:80]}")
                self.results["multi_agent_sequential"].append({
                    "query": test["query"], "status": "ERROR", "error": str(e)
                })

        print(f"\nSequential Multi-Agent Test: {passed}/{len(test_cases)} passed")
        return passed, len(test_cases)

    async def test_multi_agent_parallel(self):
        """Test 4: Multi-Agent Parallel Execution"""
        print("\n" + "="*80)
        print("TEST 4: MULTI-AGENT PARALLEL EXECUTION")
        print("="*80)

        # Note: Current system mostly uses sequential, but let's test comparison which could be parallel
        test_cases = [
            {
                "query": "So sánh chi tiết VCB, TCB và ACB",
                "expected_agents": ["ComparisonSpecialist"],
                "description": "Multi-stock comparison"
            },
        ]

        passed = 0
        for i, test in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] {test['description']}")
            print(f"   Query: {test['query']}")

            start_time = time.time()
            response_length = 0
            agents_used = []

            try:
                async for event in self.orchestrator.process_query(test["query"], user_id="test_parallel"):
                    event_type = event.get("type", "")

                    if event_type == "routing_decision":
                        data = event.get("data", {})
                        mode = data.get("execution_mode", "unknown")
                        print(f"   Execution mode: {mode}")
                        for t in data.get("tasks", []):
                            agents_used.append(t["specialist"])

                    elif event_type == "chunk":
                        chunk = event.get("data", "")
                        if isinstance(chunk, str):
                            response_length += len(chunk)

                elapsed = time.time() - start_time

                # Check if expected agents were used
                agents_match = all(exp in agents_used for exp in test["expected_agents"])
                has_response = response_length > 100

                status = "PASS" if agents_match and has_response else "FAIL"
                if status == "PASS":
                    passed += 1

                print(f"   Result: {status} - Agents: {agents_used}, Response: {response_length} chars, Time: {elapsed:.1f}s")

                self.results["multi_agent_parallel"].append({
                    "query": test["query"],
                    "status": status,
                    "agents": agents_used,
                    "response_length": response_length,
                    "time": elapsed
                })

            except Exception as e:
                print(f"   ✗ ERROR: {str(e)[:80]}")
                self.results["multi_agent_parallel"].append({
                    "query": test["query"], "status": "ERROR", "error": str(e)
                })

        print(f"\nParallel Multi-Agent Test: {passed}/{len(test_cases)} passed")
        return passed, len(test_cases)

    async def test_error_handling(self):
        """Test 5: Error Handling"""
        print("\n" + "="*80)
        print("TEST 5: ERROR HANDLING")
        print("="*80)

        test_cases = [
            {"query": "Phân tích ZZZZZ", "description": "Invalid symbol", "should_not_crash": True},
            {"query": "", "description": "Empty query", "should_not_crash": True},
            {"query": "abc", "description": "Ambiguous short query", "should_not_crash": True},
            {"query": "!@#$%^&*()", "description": "Special characters only", "should_not_crash": True},
        ]

        passed = 0
        for i, test in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] {test['description']}")

            crashed = False
            got_response = False
            error_message = None

            try:
                async for event in self.orchestrator.process_query(test["query"], user_id="test_error"):
                    event_type = event.get("type", "")
                    if event_type == "error":
                        error_message = event.get("data", {}).get("error", "")
                    elif event_type in ["chunk", "complete"]:
                        got_response = True

            except Exception as e:
                crashed = True
                error_message = str(e)

            # Check if handled gracefully
            handled_well = not crashed and (got_response or error_message)

            if test["should_not_crash"] and not crashed:
                passed += 1
                status = "PASS"
            else:
                status = "FAIL"

            print(f"   Result: {status} - Crashed: {crashed}, Got response: {got_response}")
            if error_message:
                print(f"   Error: {error_message[:80]}")

            self.results["error_handling"].append({
                "query": test["query"],
                "description": test["description"],
                "status": status,
                "crashed": crashed,
                "got_response": got_response
            })

        print(f"\nError Handling Test: {passed}/{len(test_cases)} passed")
        return passed, len(test_cases)

    async def test_data_flow(self):
        """Test 6: Data Flow Between Agents"""
        print("\n" + "="*80)
        print("TEST 6: DATA FLOW VERIFICATION")
        print("="*80)

        # Test that data actually flows between sequential agents
        test_query = "Phân tích FPT chi tiết rồi lập kế hoạch đầu tư 100 triệu"
        print(f"\nQuery: {test_query}")

        agent_outputs = {}

        try:
            async for event in self.orchestrator.process_query(test_query, user_id="test_flow"):
                event_type = event.get("type", "")

                if event_type == "routing_decision":
                    tasks = event.get("data", {}).get("tasks", [])
                    print(f"   Tasks planned: {len(tasks)}")
                    for t in tasks:
                        deps = t.get("depends_on", [])
                        print(f"      {t['specialist']} (depends on: {deps})")

                elif event_type == "task_complete":
                    data = event.get("data", {})
                    specialist = data.get("specialist", "")
                    result = data.get("result", "")
                    agent_outputs[specialist] = result
                    print(f"   {specialist} completed: {len(result)} chars")

            # Verify data flow
            print("\n   Data Flow Analysis:")

            # Check if InvestmentPlanner received context from AnalysisSpecialist
            if "AnalysisSpecialist" in agent_outputs and "InvestmentPlanner" in agent_outputs:
                analysis_output = agent_outputs["AnalysisSpecialist"]
                investment_output = agent_outputs["InvestmentPlanner"]

                # Check if investment plan mentions FPT (from analysis)
                fpt_mentioned_in_plan = "FPT" in investment_output.upper()

                print(f"      Analysis output contains FPT data: {'Yes' if 'FPT' in analysis_output.upper() else 'No'}")
                print(f"      Investment plan mentions FPT: {'Yes' if fpt_mentioned_in_plan else 'No'}")

                if fpt_mentioned_in_plan:
                    print("   ✓ PASS - Data successfully flowed between agents")
                    status = "PASS"
                else:
                    print("   ○ PARTIAL - Agents executed but data flow unclear")
                    status = "PARTIAL"
            else:
                print("   ✗ FAIL - Not all expected agents executed")
                status = "FAIL"

            self.results["data_flow"].append({
                "query": test_query,
                "status": status,
                "agents_completed": list(agent_outputs.keys())
            })

            return 1 if status == "PASS" else 0, 1

        except Exception as e:
            print(f"   ✗ ERROR: {str(e)[:80]}")
            self.results["data_flow"].append({"query": test_query, "status": "ERROR", "error": str(e)})
            return 0, 1

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("FINAL TEST SUMMARY")
        print("="*80)

        total_passed = 0
        total_tests = 0

        categories = [
            ("Routing Logic", "routing"),
            ("Single Agent", "single_agent"),
            ("Multi-Agent Sequential", "multi_agent_sequential"),
            ("Multi-Agent Parallel", "multi_agent_parallel"),
            ("Error Handling", "error_handling"),
            ("Data Flow", "data_flow")
        ]

        for name, key in categories:
            results = self.results[key]
            passed = sum(1 for r in results if r.get("status") == "PASS")
            total = len(results)
            total_passed += passed
            total_tests += total

            icon = "✓" if passed == total else "○" if passed > 0 else "✗"
            print(f"\n{icon} {name}: {passed}/{total}")

            for r in results:
                status = r.get("status", "UNKNOWN")
                query = r.get("query", r.get("description", ""))[:40]
                status_icon = "✓" if status == "PASS" else "○" if status == "PARTIAL" else "✗"
                print(f"   {status_icon} {query}...")

        print(f"\n{'='*80}")
        percentage = (total_passed / total_tests * 100) if total_tests > 0 else 0
        print(f"OVERALL: {total_passed}/{total_tests} tests passed ({percentage:.1f}%)")
        print("="*80)

        return total_passed, total_tests


async def main():
    tester = SystemTester()
    await tester.initialize()

    # Run all tests
    await tester.test_routing_accuracy()
    await tester.test_single_agent_execution()
    await tester.test_multi_agent_sequential()
    await tester.test_multi_agent_parallel()
    await tester.test_error_handling()
    await tester.test_data_flow()

    # Print summary
    passed, total = tester.print_summary()

    return passed, total


if __name__ == "__main__":
    asyncio.run(main())
