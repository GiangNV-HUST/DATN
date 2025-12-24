"""
So sánh performance giữa Claude và Gemini
Chạy cùng 1 query trên cả 2 models và so sánh kết quả
"""

import asyncio
import time
from stock_agent_v3 import StockAgentV3
from stock_agent_gemini import GeminiStockAgent


async def test_model(agent, model_name: str, query: str):
    """Test một model"""
    print(f"\n{'='*70}")
    print(f"🧪 Testing: {model_name}")
    print(f"{'='*70}")
    print(f"❓ Query: {query}\n")

    start_time = time.time()

    try:
        response = await agent.chat_with_tools(query)
        elapsed = time.time() - start_time

        print(f"✅ {model_name} Response ({elapsed:.2f}s):")
        print("-" * 70)
        print(response)
        print("-" * 70)

        return {
            "model": model_name,
            "success": True,
            "response": response,
            "time": elapsed,
            "error": None
        }

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ {model_name} Error ({elapsed:.2f}s):")
        print(f"   {str(e)}")

        return {
            "model": model_name,
            "success": False,
            "response": None,
            "time": elapsed,
            "error": str(e)
        }


async def compare_models():
    """So sánh Claude vs Gemini"""
    print("\n" + "="*70)
    print("🔬 MODEL COMPARISON: Claude Sonnet 4.5 vs Gemini 2.0 Flash")
    print("="*70 + "\n")

    # Initialize agents
    print("🔧 Initializing agents...")

    claude_agent = StockAgentV3(
        mcp_server_url="http://localhost:5000"
    )
    print("✅ Claude agent initialized")

    gemini_agent = GeminiStockAgent(
        mcp_server_url="http://localhost:5000",
        model_name="gemini-2.0-flash-exp"
    )
    print("✅ Gemini agent initialized\n")

    # Discover tools
    print("📡 Discovering tools...")
    claude_tools = await claude_agent.discover_tools()
    gemini_tools = await gemini_agent.discover_tools()

    if not claude_tools or not gemini_tools:
        print("❌ Error: Could not discover tools from MCP server")
        print("Make sure MCP server is running:")
        print("   python src/AI_agent_v3/mcp_server/stock_mcp_server.py")
        return

    print(f"✅ Both agents discovered {len(claude_tools)} tools\n")

    # Test queries
    test_queries = [
        "VCB giá bao nhiêu?",
        "Phân tích RSI của VNM",
        # Uncomment để test thêm:
        # "So sánh VCB và TCB",
        # "Tìm cổ phiếu RSI dưới 30"
    ]

    results = []

    for i, query in enumerate(test_queries, 1):
        print(f"\n\n{'#'*70}")
        print(f"# QUERY {i}/{len(test_queries)}")
        print(f"{'#'*70}")

        # Test Claude
        claude_result = await test_model(claude_agent, "Claude Sonnet 4.5", query)
        claude_agent.clear_history()

        # Small delay
        await asyncio.sleep(1)

        # Test Gemini
        gemini_result = await test_model(gemini_agent, "Gemini 2.0 Flash", query)
        gemini_agent.clear_history()

        results.append({
            "query": query,
            "claude": claude_result,
            "gemini": gemini_result
        })

    # Summary
    print(f"\n\n{'='*70}")
    print("📊 COMPARISON SUMMARY")
    print(f"{'='*70}\n")

    total_claude_time = 0
    total_gemini_time = 0
    claude_success = 0
    gemini_success = 0

    for i, result in enumerate(results, 1):
        print(f"\n{i}. Query: {result['query']}")
        print("-" * 70)

        # Claude stats
        if result['claude']['success']:
            print(f"   ✅ Claude: {result['claude']['time']:.2f}s")
            total_claude_time += result['claude']['time']
            claude_success += 1
        else:
            print(f"   ❌ Claude: Error - {result['claude']['error']}")

        # Gemini stats
        if result['gemini']['success']:
            print(f"   ✅ Gemini: {result['gemini']['time']:.2f}s")
            total_gemini_time += result['gemini']['time']
            gemini_success += 1
        else:
            print(f"   ❌ Gemini: Error - {result['gemini']['error']}")

        # Winner
        if result['claude']['success'] and result['gemini']['success']:
            if result['claude']['time'] < result['gemini']['time']:
                print(f"   🏆 Winner: Claude (faster by {result['gemini']['time'] - result['claude']['time']:.2f}s)")
            else:
                print(f"   🏆 Winner: Gemini (faster by {result['claude']['time'] - result['gemini']['time']:.2f}s)")

    # Overall stats
    print(f"\n{'='*70}")
    print("📈 OVERALL STATISTICS")
    print(f"{'='*70}\n")

    print(f"Claude Sonnet 4.5:")
    print(f"   Success rate: {claude_success}/{len(results)}")
    if claude_success > 0:
        print(f"   Total time: {total_claude_time:.2f}s")
        print(f"   Average time: {total_claude_time/claude_success:.2f}s")
    print()

    print(f"Gemini 2.0 Flash:")
    print(f"   Success rate: {gemini_success}/{len(results)}")
    if gemini_success > 0:
        print(f"   Total time: {total_gemini_time:.2f}s")
        print(f"   Average time: {total_gemini_time/gemini_success:.2f}s")
    print()

    if claude_success > 0 and gemini_success > 0:
        avg_claude = total_claude_time / claude_success
        avg_gemini = total_gemini_time / gemini_success

        if avg_claude < avg_gemini:
            speedup = ((avg_gemini - avg_claude) / avg_gemini) * 100
            print(f"🏆 Overall Winner: Claude (faster by {speedup:.1f}%)")
        else:
            speedup = ((avg_claude - avg_gemini) / avg_claude) * 100
            print(f"🏆 Overall Winner: Gemini (faster by {speedup:.1f}%)")

    print(f"\n{'='*70}\n")


async def main():
    """Main function"""
    try:
        await compare_models()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Stopped by user")
