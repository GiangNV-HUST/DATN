"""
Basic Example - Hybrid System Usage

Demonstrates:
1. Initialize Hybrid Orchestrator
2. Auto-mode routing (AI decides)
3. View routing decisions
4. See metrics
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()


async def main():
    """Main example function"""

    # Import after adding to path
    from hybrid_system.orchestrator import HybridOrchestrator

    print("="*60)
    print("🚀 HYBRID SYSTEM - Basic Example")
    print("="*60)
    print()

    # Get MCP server path
    mcp_server_path = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "ai_agent_mcp", "mcp_server", "server.py"
    )

    # Initialize orchestrator
    print("📡 Initializing Hybrid Orchestrator...")
    orchestrator = HybridOrchestrator(server_script_path=mcp_server_path)

    try:
        await orchestrator.initialize()
        print("✅ Orchestrator ready!\n")

        # Test queries
        test_queries = [
            ("Giá VCB?", "Simple price query - should use DIRECT mode"),
            ("Phân tích VCB", "Analysis query - should use AGENT mode"),
            ("Cảnh báo của tôi", "User alerts - should use DIRECT mode"),
        ]

        for query, description in test_queries:
            print(f"\n{'='*60}")
            print(f"📝 Query: {query}")
            print(f"💡 Expected: {description}")
            print(f"{'='*60}\n")

            async for event in orchestrator.process_query(
                user_query=query,
                user_id="demo_user",
                mode="auto"  # Let AI decide
            ):
                if event["type"] == "status":
                    print(f"📍 {event['data']}")

                elif event["type"] == "routing_decision":
                    data = event["data"]
                    print(f"\n🧠 AI Router Decision:")
                    print(f"   Mode Selected: {data['mode'].upper()}")
                    print(f"   Confidence: {data['confidence']:.2f}")
                    print(f"   Complexity: {data['complexity']:.2f}")
                    print(f"   Reasoning: {data['reasoning']}")
                    print(f"   Estimated Time: {data['estimated_time']:.1f}s")
                    if data['suggested_tools']:
                        print(f"   Suggested Tools: {', '.join(data['suggested_tools'])}")
                    print()

                elif event["type"] == "chunk":
                    print(event["data"])

                elif event["type"] == "complete":
                    data = event["data"]
                    print(f"\n✅ Completed in {data['elapsed_time']:.2f}s")
                    if data.get('time_saved'):
                        print(f"   Time saved: {data['time_saved']:.2f}s")

                elif event["type"] == "error":
                    print(f"\n❌ Error: {event['data']['error']}")

        # Show overall metrics
        print(f"\n{'='*60}")
        print("📊 SYSTEM METRICS")
        print(f"{'='*60}\n")

        metrics = orchestrator.get_metrics()
        print(f"Total Queries: {metrics['total_queries']}")
        print(f"Agent Mode: {metrics['agent_mode_count']} ({metrics['agent_mode_percentage']:.1f}%)")
        print(f"Direct Mode: {metrics['direct_mode_count']}")
        print(f"Cache Hit Rate: {metrics['cache_hit_rate']}")
        print(f"Avg Response Time: {metrics['avg_response_time']}")
        print(f"Circuit Breaker: {metrics['circuit_breaker_status']}")

        # Show routing analysis
        print(f"\n{'='*60}")
        print("🧠 ROUTING ANALYSIS")
        print(f"{'='*60}\n")

        analysis = orchestrator.get_routing_analysis()
        if "message" not in analysis:
            print(f"Total Decisions: {analysis['total_decisions']}")
            print(f"Avg Confidence: {analysis['avg_confidence']:.2f}")
            print(f"Avg Complexity: {analysis['avg_complexity']:.2f}")
            print(f"Avg Routing Time: {analysis['avg_routing_time']:.3f}s")

            print("\nRecent Decisions:")
            for decision in analysis.get('recent_decisions', []):
                print(f"  • {decision['query']}")
                print(f"    Mode: {decision['mode']}, Confidence: {decision['confidence']:.2f}")
                print(f"    {decision['reasoning']}\n")

    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
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
