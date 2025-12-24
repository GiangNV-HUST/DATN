"""
Stock Analysis Agent V3 - With MCP Integration
Agent kết nối với MCP Server để sử dụng tools phân tán
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, List, Optional
from anthropic import Anthropic
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StockAgentV3:
    """AI Agent V3 với MCP Integration"""

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        mcp_server_url: str = "http://localhost:5000"
    ):
        """
        Khởi tạo Agent V3

        Args:
            anthropic_api_key: API key cho Anthropic Claude (nếu None, lấy từ env)
            mcp_server_url: URL của MCP server
        """
        self.anthropic_api_key = anthropic_api_key or Config.GEMINI_API_KEY  # Sẽ dùng Anthropic key thực tế
        self.mcp_server_url = mcp_server_url
        self.client = Anthropic(api_key=self.anthropic_api_key)
        self.model = "claude-sonnet-4-5-20250929"  # Claude Sonnet 4.5

        self.mcp_tools = []
        self.conversation_history = []

        logger.info("✅ Stock Agent V3 initialized")
        logger.info(f"🔗 MCP Server: {mcp_server_url}")

    async def discover_tools(self) -> List[Dict[str, Any]]:
        """
        Discover tools từ MCP server

        Returns:
            List các tool schemas
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.mcp_server_url}/tools/schema") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("success"):
                            self.mcp_tools = data["schemas"]
                            logger.info(f"🔧 Discovered {len(self.mcp_tools)} tools from MCP server")
                            for tool in self.mcp_tools:
                                logger.info(f"   - {tool['name']}: {tool['description'][:50]}...")
                            return self.mcp_tools
                        else:
                            logger.error(f"Failed to get schemas: {data.get('error')}")
                            return []
                    else:
                        logger.error(f"MCP server returned status {resp.status}")
                        return []
        except Exception as e:
            logger.error(f"❌ Failed to discover tools: {e}")
            return []

    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gọi một tool trên MCP server

        Args:
            tool_name: Tên tool
            arguments: Arguments cho tool

        Returns:
            Kết quả từ tool
        """
        try:
            logger.info(f"🔧 Calling MCP tool: {tool_name}({arguments})")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.mcp_server_url}/tools/call",
                    json={"tool": tool_name, "arguments": arguments}
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        logger.info(f"✅ Tool result: {json.dumps(result, ensure_ascii=False)[:200]}...")
                        return result
                    else:
                        error = await resp.text()
                        logger.error(f"MCP tool call failed: {error}")
                        return {
                            "success": False,
                            "error": f"HTTP {resp.status}: {error}"
                        }
        except Exception as e:
            logger.error(f"❌ Error calling MCP tool: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def chat_with_tools(self, user_message: str, max_iterations: int = 10) -> str:
        """
        Chat với AI agent, tự động gọi MCP tools khi cần

        Args:
            user_message: Tin nhắn từ user
            max_iterations: Số lần tối đa cho phép gọi tools

        Returns:
            Câu trả lời cuối cùng
        """
        # Thêm message vào history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        iteration = 0
        while iteration < max_iterations:
            try:
                # Gọi Claude API với tools
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=self._get_system_prompt(),
                    tools=self.mcp_tools,
                    messages=self.conversation_history
                )

                logger.info(f"🤖 Claude response stop_reason: {response.stop_reason}")

                # Kiểm tra stop reason
                if response.stop_reason == "end_turn":
                    # AI đã trả lời xong, không cần gọi tools
                    final_text = self._extract_text_from_response(response)

                    # Thêm assistant response vào history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": response.content
                    })

                    return final_text

                elif response.stop_reason == "tool_use":
                    # AI muốn gọi tools
                    # Thêm assistant message với tool_use vào history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": response.content
                    })

                    # Execute tools
                    tool_results = await self._execute_tool_uses(response.content)

                    # Thêm tool results vào history
                    self.conversation_history.append({
                        "role": "user",
                        "content": tool_results
                    })

                    iteration += 1

                else:
                    # Các stop reasons khác
                    logger.warning(f"Unexpected stop_reason: {response.stop_reason}")
                    return self._extract_text_from_response(response)

            except Exception as e:
                logger.error(f"❌ Error in chat loop: {e}", exc_info=True)
                raise Exception(f"Không thể trả lời: {str(e)}")

        # Max iterations reached
        return "❌ Đã vượt quá số lần gọi tools cho phép. Vui lòng thử lại với câu hỏi đơn giản hơn."

    async def _execute_tool_uses(self, content_blocks: List) -> List[Dict[str, Any]]:
        """
        Execute tất cả tool uses trong response

        Args:
            content_blocks: List các content blocks từ Claude response

        Returns:
            List tool results
        """
        tool_results = []

        for block in content_blocks:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                tool_use_id = block.id

                logger.info(f"🔧 Executing tool: {tool_name}")

                # Gọi MCP tool
                result = await self.call_mcp_tool(tool_name, tool_input)

                # Format result cho Claude
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

        return tool_results

    def _extract_text_from_response(self, response) -> str:
        """Extract text từ Claude response"""
        text_parts = []
        for block in response.content:
            if hasattr(block, 'text'):
                text_parts.append(block.text)
        return "\n".join(text_parts) if text_parts else "❌ Không có response text"

    def _get_system_prompt(self) -> str:
        """System prompt cho agent"""
        return """Bạn là AI Stock Analysis Agent V3 chuyên phân tích cổ phiếu Việt Nam.

Bạn có quyền truy cập các MCP tools để lấy dữ liệu thực:
1. get_latest_price - Lấy giá và chỉ báo kỹ thuật mới nhất
2. get_price_history - Lấy lịch sử giá để phân tích xu hướng
3. get_predictions - Lấy dự đoán giá từ mô hình ML
4. search_stocks - Tìm cổ phiếu theo tiêu chí kỹ thuật

Hướng dẫn:
- Khi người dùng hỏi về cổ phiếu, hãy SỬ DỤNG TOOLS để lấy dữ liệu thực
- Phân tích dữ liệu chi tiết, giải thích ý nghĩa các chỉ báo
- Đưa ra nhận xét và khuyến nghị dựa trên dữ liệu
- Format câu trả lời rõ ràng, dễ hiểu với emoji

Lưu ý: Phân tích chỉ mang tính tham khảo, không phải lời khuyên đầu tư."""

    def clear_history(self):
        """Xóa conversation history"""
        self.conversation_history = []
        logger.info("🧹 Conversation history cleared")

    def analyze_stock(self, ticker: str) -> str:
        """
        Phân tích cổ phiếu (sync wrapper)

        Args:
            ticker: Mã cổ phiếu

        Returns:
            Phân tích chi tiết
        """
        return asyncio.run(self.chat_with_tools(
            f"Hãy phân tích toàn diện cổ phiếu {ticker}. "
            f"Lấy giá hiện tại, lịch sử, và dự đoán để đưa ra nhận xét chi tiết."
        ))

    def answer_question(self, question: str) -> str:
        """
        Trả lời câu hỏi (sync wrapper)

        Args:
            question: Câu hỏi từ user

        Returns:
            Câu trả lời
        """
        return asyncio.run(self.chat_with_tools(question))


async def main():
    """Demo agent"""
    print("\n" + "="*60)
    print("🧪 TESTING STOCK AGENT V3 - MCP Integration")
    print("="*60 + "\n")

    # Khởi tạo agent
    agent = StockAgentV3(
        mcp_server_url="http://localhost:5000"
    )

    # Discover tools từ MCP server
    print("📡 Discovering tools from MCP server...")
    tools = await agent.discover_tools()

    if not tools:
        print("❌ No tools discovered. Make sure MCP server is running!")
        print("   Run: python src/AI_agent_v3/mcp_server/stock_mcp_server.py")
        return

    print(f"✅ Discovered {len(tools)} tools\n")

    # Test queries
    test_queries = [
        "VCB giá bao nhiêu?",
        # "So sánh VCB và TCB về RSI",
        # "Tìm cổ phiếu RSI dưới 30"
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"❓ User: {query}")
        print(f"{'='*60}\n")

        response = await agent.chat_with_tools(query)
        print(f"🤖 Agent: {response}\n")

        # Clear history between queries
        agent.clear_history()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Stopped by user")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
