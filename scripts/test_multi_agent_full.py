"""
Full Integration Test for Multi-Agent Query Handling

Tests the complete flow from query -> routing -> multi-agent execution -> response
"""

import asyncio
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from ai_agent_hybrid.hybrid_system.orchestrator.multi_agent_orchestrator import MultiAgentOrchestrator


async def test_query(orchestrator, query: str, user_id: str = "test_user"):
    """Test a single query and print results"""
    print(f"\n{'='*70}")
    print(f"QUERY: {query}")
    print('='*70)

    try:
        async for event in orchestrator.process_query(query, user_id, enable_multi_agent=True):
            event_type = event.get("type", "unknown")
            data = event.get("data", {})

            if event_type == "status":
                print(f"\n[STATUS] {data}")

            elif event_type == "routing_decision":
                print(f"\n[ROUTING DECISION]")
                if isinstance(data, dict):
                    is_multi = data.get("is_multi_agent", False)
                    exec_mode = data.get("execution_mode", "single")
                    tasks = data.get("tasks", [])
                    confidence = data.get("confidence", 0)
                    reasoning = data.get("reasoning", "")

                    print(f"  Multi-Agent: {is_multi}")
                    print(f"  Execution Mode: {exec_mode}")
                    print(f"  Confidence: {confidence:.2f}")
                    print(f"  Reasoning: {reasoning[:100]}...")
                    if tasks:
                        print(f"  Tasks:")
                        for t in tasks:
                            print(f"    - {t.get('specialist')} ({t.get('method')}) depends_on={t.get('depends_on')}")
                    else:
                        specialist = data.get("specialist", "Unknown")
                        method = data.get("method", "Unknown")
                        print(f"  Specialist: {specialist}")
                        print(f"  Method: {method}")

            elif event_type == "chunk":
                # Print response chunks (truncate long ones)
                chunk_data = data if isinstance(data, str) else str(data)
                if len(chunk_data) > 500:
                    print(f"\n[RESPONSE CHUNK] {chunk_data[:500]}...")
                else:
                    print(f"\n[RESPONSE CHUNK] {chunk_data}")

            elif event_type == "task_complete":
                if isinstance(data, dict):
                    print(f"\n[TASK COMPLETE] {data.get('specialist')} - Task ID: {data.get('task_id')}")

            elif event_type == "aggregation_complete":
                if isinstance(data, dict):
                    print(f"\n[AGGREGATION] Strategy: {data.get('strategy')}, Tasks: {data.get('num_tasks')}")

            elif event_type == "complete":
                print(f"\n[COMPLETE]")
                if isinstance(data, dict):
                    elapsed = data.get("elapsed_time", 0)
                    mode = data.get("mode_used", "unknown")
                    exec_mode = data.get("execution_mode", "single")
                    specialists = data.get("specialists_used", [data.get("specialist_used", "unknown")])
                    num_agents = data.get("num_agents", 1)

                    print(f"  Elapsed Time: {elapsed:.2f}s")
                    print(f"  Mode: {mode}")
                    print(f"  Execution Mode: {exec_mode}")
                    print(f"  Specialists Used: {specialists}")
                    print(f"  Number of Agents: {num_agents}")

            elif event_type == "error":
                print(f"\n[ERROR] {data}")

    except Exception as e:
        print(f"\n[EXCEPTION] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """Run full integration tests"""
    print("\n" + "="*70)
    print("MULTI-AGENT FULL INTEGRATION TEST")
    print("="*70)

    # Initialize orchestrator
    print("\nInitializing MultiAgentOrchestrator...")
    orchestrator = MultiAgentOrchestrator(use_direct_client=True, routing_mode="ai")

    try:
        await orchestrator.initialize()
        print("Orchestrator initialized successfully!")

        # Test queries - mix of single and multi-agent
        test_queries = [
            # Single agent queries
            "Gia VCB hom nay",  # AnalysisSpecialist only

            # Multi-agent: Market -> Discovery (Sequential/Parallel)
            "VN-Index hom nay the nao? Goi y co phieu dang mua",

            # Multi-agent: Analyze -> Compare (Sequential)
            "Phan tich VCB va TCB, so sanh xem cai nao tot hon",
        ]

        for query in test_queries:
            await test_query(orchestrator, query)
            print("\n" + "-"*70)

        # Print final metrics
        print("\n" + "="*70)
        print("FINAL METRICS")
        print("="*70)
        metrics = orchestrator.get_metrics()
        print(f"Total Queries: {metrics.get('total_queries', 0)}")
        print(f"Specialist Usage: {metrics.get('specialist_usage', {})}")
        print(f"Avg Routing Time: {metrics.get('avg_routing_time', 0):.3f}s")

    except Exception as e:
        print(f"\nFailed to initialize: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\nCleaning up...")
        await orchestrator.cleanup()
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
