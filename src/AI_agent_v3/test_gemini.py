"""
Test script cho Gemini Stock Agent
Chạy để test Gemini agent trước khi dùng với Discord bot
"""

import asyncio
from stock_agent_gemini import GeminiStockAgent


async def main():
    print("\n" + "="*70)
    print("🧪 TESTING GEMINI STOCK AGENT")
    print("="*70 + "\n")

    # Khởi tạo agent
    print("🔧 Initializing Gemini agent...")
    agent = GeminiStockAgent(
        mcp_server_url="http://localhost:5000",
        model_name="gemini-2.0-flash-exp"  # Hoặc: "gemini-1.5-pro", "gemini-1.5-flash"
    )
    print("✅ Agent initialized\n")

    # Discover tools
    print("📡 Discovering tools from MCP server...")
    tools = await agent.discover_tools()

    if not tools:
        print("\n❌ ERROR: No tools discovered!")
        print("Make sure MCP server is running:")
        print("   python src/AI_agent_v3/mcp_server/stock_mcp_server.py")
        return

    print(f"✅ Discovered {len(tools)} tools:")
    for tool in tools:
        print(f"   - {tool['name']}")
    print()

    # Test queries
    test_queries = [
        {
            "query": "VCB giá bao nhiêu?",
            "description": "Test get_latest_price tool"
        },
        {
            "query": "Phân tích RSI của VCB",
            "description": "Test technical analysis"
        },
        # Uncomment để test thêm:
        # {
        #     "query": "VCB sẽ tăng hay giảm?",
        #     "description": "Test get_predictions tool"
        # },
        # {
        #     "query": "Tìm cổ phiếu RSI dưới 30",
        #     "description": "Test search_stocks tool"
        # }
    ]

    for i, test in enumerate(test_queries, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}/{len(test_queries)}: {test['description']}")
        print(f"{'='*70}")
        print(f"❓ User: {test['query']}\n")

        try:
            # Send message
            response = await agent.chat_with_tools(test['query'])

            # Print response
            print(f"🤖 Gemini Response:")
            print("-" * 70)
            print(response)
            print("-" * 70)

            # Clear history giữa các queries
            agent.clear_history()

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*70}")
    print("✅ Testing completed!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
