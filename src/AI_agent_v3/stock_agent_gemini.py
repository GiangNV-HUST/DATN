"""
Stock Analysis Agent - Gemini Version
Agent sử dụng Google Gemini với MCP Integration
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, List, Optional
import google.generativeai as genai
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GeminiStockAgent:
    """AI Agent với Gemini và MCP Integration"""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        mcp_server_url: str = "http://localhost:5000",
        model_name: str = "gemini-2.5-flash-lite"
    ):
        """
        Khởi tạo Gemini Agent

        Args:
            gemini_api_key: API key cho Google Gemini (nếu None, lấy từ env)
            mcp_server_url: URL của MCP server
            model_name: Tên model Gemini (gemini-2.5-flash-lite)
        """
        self.gemini_api_key = gemini_api_key or Config.GEMINI_API_KEY
        self.mcp_server_url = mcp_server_url
        self.model_name = model_name

        # Configure Gemini
        genai.configure(api_key=self.gemini_api_key)

        # Initialize model với function calling
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=self._get_system_prompt()
        )

        self.mcp_tools = []
        self.gemini_tools = []  # Tools ở format Gemini
        self.conversation_history = []

        logger.info("✅ Gemini Stock Agent initialized")
        logger.info(f"🤖 Model: {model_name}")
        logger.info(f"🔗 MCP Server: {mcp_server_url}")

    async def discover_tools(self) -> List[Dict[str, Any]]:
        """
        Discover tools từ MCP server và convert sang Gemini format

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
                            # Convert to Gemini format
                            self.gemini_tools = self._convert_to_gemini_tools(self.mcp_tools)

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

    def _convert_to_gemini_tools(self, mcp_tools: List[Dict]) -> List:
        """
        Convert MCP tool schemas sang Gemini function declarations

        Args:
            mcp_tools: List tool schemas từ MCP

        Returns:
            List Gemini function declarations
        """
        gemini_functions = []

        for tool in mcp_tools:
            # Gemini function declaration format
            function_decl = genai.protos.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        prop_name: genai.protos.Schema(
                            type=self._map_type_to_gemini(prop_schema.get("type", "string")),
                            description=prop_schema.get("description", "")
                        )
                        for prop_name, prop_schema in tool["input_schema"]["properties"].items()
                    },
                    required=tool["input_schema"].get("required", [])
                )
            )
            gemini_functions.append(function_decl)

        return [genai.protos.Tool(function_declarations=gemini_functions)]

    def _map_type_to_gemini(self, json_type: str) -> genai.protos.Type:
        """Map JSON schema type to Gemini type"""
        type_mapping = {
            "string": genai.protos.Type.STRING,
            "number": genai.protos.Type.NUMBER,
            "integer": genai.protos.Type.INTEGER,
            "boolean": genai.protos.Type.BOOLEAN,
            "array": genai.protos.Type.ARRAY,
            "object": genai.protos.Type.OBJECT
        }
        return type_mapping.get(json_type, genai.protos.Type.STRING)

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
        Chat với Gemini agent, tự động gọi MCP tools khi cần

        Args:
            user_message: Tin nhắn từ user
            max_iterations: Số lần tối đa cho phép gọi tools

        Returns:
            Câu trả lời cuối cùng
        """
        # Start chat session với tools
        chat = self.model.start_chat(
            history=self.conversation_history,
            enable_automatic_function_calling=False  # Manual control
        )

        iteration = 0
        current_message = user_message

        while iteration < max_iterations:
            try:
                # Send message với tools
                response = chat.send_message(
                    current_message,
                    tools=self.gemini_tools if self.gemini_tools else None
                )

                logger.info(f"🤖 Gemini response parts: {len(response.parts)}")

                # Check for function calls
                function_calls = []
                text_response = []

                for part in response.parts:
                    if part.function_call:
                        function_calls.append(part.function_call)
                    elif part.text:
                        text_response.append(part.text)

                # Nếu không có function calls, trả về text response
                if not function_calls:
                    final_text = "".join(text_response)

                    # Update history
                    self.conversation_history = chat.history

                    return final_text if final_text else "❌ Không có response"

                # Execute function calls
                logger.info(f"🔧 Gemini wants to call {len(function_calls)} function(s)")

                function_responses = []
                for fc in function_calls:
                    tool_name = fc.name
                    tool_args = dict(fc.args)

                    logger.info(f"   - {tool_name}({tool_args})")

                    # Call MCP tool
                    result = await self.call_mcp_tool(tool_name, tool_args)

                    # Format response for Gemini
                    function_responses.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=tool_name,
                                response={"result": result}
                            )
                        )
                    )

                # Send function results back to Gemini
                current_message = function_responses
                iteration += 1

            except Exception as e:
                logger.error(f"❌ Error in chat loop: {e}", exc_info=True)
                raise Exception(f"Không thể trả lời: {str(e)}")

        # Max iterations reached
        return "❌ Đã vượt quá số lần gọi tools cho phép. Vui lòng thử lại với câu hỏi đơn giản hơn."

    def _get_system_prompt(self) -> str:
        """System prompt cho agent"""
        return """Bạn là AI Stock Analysis Agent chuyên phân tích cổ phiếu Việt Nam.

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
    """Demo Gemini agent"""
    print("\n" + "="*60)
    print("🧪 TESTING GEMINI STOCK AGENT - MCP Integration")
    print("="*60 + "\n")

    # Khởi tạo agent
    agent = GeminiStockAgent(
        mcp_server_url="http://localhost:5000",
        model_name="gemini-2.5-flash-lite"  # hoặc "gemini-1.5-pro"
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
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"❓ User: {query}")
        print(f"{'='*60}\n")

        response = await agent.chat_with_tools(query)
        print(f"🤖 Gemini: {response}\n")

        # Clear history between queries
        agent.clear_history()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Stopped by user")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
