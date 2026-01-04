"""
Complete Example - Full Hybrid System Demo

Demonstrates full functionality with all modes and features.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from hybrid_system.orchestrator import HybridOrchestrator


async def main():
    """Main demo function"""

    print("="*60)
    print("🚀 HYBRID SYSTEM - Complete Demo")
    print("="*60)
    print()

    # Get MCP server path
    mcp_server_path = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "ai_agent_mcp", "mcp_server", "server.py"
    )

    print(f"MCP Server Path: {mcp_server_path}")
    print()

    # Initialize orchestrator
    print("📡 Initializing Hybrid Orchestrator...")
    orchestrator = HybridOrchestrator(server_script_path=mcp_server_path)

    try:
        await orchestrator.initialize()
        print("✅ Orchestrator ready!\n")

        # Demo queries covering different patterns
        demos = [
            {
                "title": "Simple Price Query (DIRECT MODE expected)",
                "query": "Giá VCB?",
                "user_id": "demo_user"
            },
            {
                "title": "Complex Analysis (AGENT MODE expected)",
                "query": "Phân tích cổ phiếu VCB",
                "user_id": "demo_user"
            },
            {
                "title": "Comparison Query (AGENT MODE expected)",
                "query": "So sánh VCB với FPT",
                "user_id": "demo_user"
            },
        ]

        for i, demo in enumerate(demos, 1):
            print(f"\n{'='*60}")
            print(f"Demo {i}: {demo['title']}")
            print(f"{'='*60}")
            print(f"Query: {demo['query']}\n")

            async for event in orchestrator.process_query(
                user_query=demo["query"],
                user_id=demo["user_id"],
                mode="auto"  # Let AI decide
            ):
                if event["type"] == "status":
                    print(f"📍 {event['data']}")

                elif event["type"] == "routing_decision":
                    data = event["data"]
                    print(f"\n🧠 AI Router Decision:")
                    print(f"   Mode: {data['mode'].upper()}")
                    print(f"   Confidence: {data['confidence']:.2f}")
                    print(f"   Complexity: {data['complexity']:.2f}")
                    print(f"   Reasoning: {data['reasoning']}")
                    print(f"   Estimated Time: {data['estimated_time']:.1f}s")
                    print(f"   Routing Time: {data['routing_time']:.3f}s")
                    if data['suggested_tools']:
                        print(f"   Suggested Tools: {', '.join(data['suggested_tools'])}")
                    print()

                elif event["type"] == "chunk":
                    # Print response (truncate if too long for demo)
                    chunk = event["data"]
                    if len(chunk) > 500:
                        print(chunk[:500] + "...\n[truncated for demo]")
                    else:
                        print(chunk)

                elif event["type"] == "complete":
                    data = event["data"]
                    print(f"\n✅ Completed in {data['elapsed_time']:.2f}s")
                    if data.get('time_saved'):
                        print(f"   Time saved vs estimate: {data['time_saved']:.2f}s")

                elif event["type"] == "error":
                    print(f"\n❌ Error: {event['data']['error']}")

            # Small delay between demos
            await asyncio.sleep(1)

        # Show comprehensive metrics
        print(f"\n\n{'='*60}")
        print("📊 SYSTEM METRICS")
        print(f"{'='*60}\n")

        metrics = orchestrator.get_metrics()

        print(f"Query Statistics:")
        print(f"  Total Queries: {metrics['total_queries']}")
        print(f"  Agent Mode: {metrics['agent_mode_count']} ({metrics['agent_mode_percentage']:.1f}%)")
        print(f"  Direct Mode: {metrics['direct_mode_count']}")
        print(f"  Total Time Saved: {metrics['total_time_saved']:.2f}s")
        print(f"  Avg Routing Time: {metrics['avg_routing_time']:.3f}s")

        print(f"\nMCP Client:")
        print(f"  Total Requests: {metrics['total_requests']}")
        print(f"  Cache Hits: {metrics['cache_hits']}")
        print(f"  Cache Hit Rate: {metrics['cache_hit_rate']}")
        print(f"  Avg Response Time: {metrics['avg_response_time']}")
        print(f"  Circuit Breaker: {metrics['circuit_breaker_status']}")

        print(f"\nDirect Executor:")
        exec_stats = metrics['direct_executor_stats']
        print(f"  Total Executions: {exec_stats['total_executions']}")
        print(f"  Success Rate: {exec_stats['success_rate']}")
        if exec_stats['by_pattern']:
            print(f"  Pattern Usage:")
            for pattern, count in exec_stats['by_pattern'].items():
                print(f"    - {pattern}: {count}")

        # Show routing analysis
        print(f"\n{'='*60}")
        print("🧠 ROUTING ANALYSIS")
        print(f"{'='*60}\n")

        analysis = orchestrator.get_routing_analysis()
        if "message" not in analysis:
            print(f"Total Decisions: {analysis['total_decisions']}")
            print(f"Avg Confidence: {analysis['avg_confidence']:.2f}")
            print(f"Avg Complexity: {analysis['avg_complexity']:.2f}")

            print("\nRecent Decisions:")
            for decision in analysis.get('recent_decisions', []):
                print(f"\n  Query: {decision['query']}")
                print(f"  Mode: {decision['mode']}, Confidence: {decision['confidence']:.2f}, Complexity: {decision['complexity']:.2f}")
                print(f"  Reasoning: {decision['reasoning']}")

        print(f"\n{'='*60}")
        print("✅ Demo Complete!")
        print(f"{'='*60}\n")

    finally:
        # Cleanup
        print("🧹 Cleaning up...")
        await orchestrator.cleanup()
        print("✅ Done!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
