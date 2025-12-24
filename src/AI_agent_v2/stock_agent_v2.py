"""
Stock Analysis AI Agent V2 - With Function Calling
Agent tự động gọi tools thông qua Gemini Function Calling API
"""

import google.generativeai as genai
import json
import logging
from typing import Dict, Any, List, Optional
from src.config import Config
from src.AI_agent.database_tools import DatabaseTools

logger = logging.getLogger(__name__)


class StockAnalysisAgentV2:
    """AI Agent V2 với Gemini Function Calling - AI tự quyết định tools"""

    def __init__(self):
        """Khởi tạo agent với Function Calling"""
        # Configure Gemini
        genai.configure(api_key=Config.GEMINI_API_KEY)

        # Database tools
        self.db_tools = DatabaseTools()

        # Define tools cho Gemini
        self.tools = self._define_tools()

        # Model với Function Calling
        self.model = genai.GenerativeModel(
            "gemini-2.5-flash-lite",
            tools=self.tools
        )

        # Chat session cho conversation
        self.chat = None

        # System instruction
        self.system_instruction = """
        Bạn là một chuyên gia phân tích chứng khoán Việt Nam với khả năng sử dụng tools.

        Khi được hỏi về cổ phiếu:
        1. Tự động gọi tools cần thiết để lấy data
        2. Phân tích dữ liệu kỹ thuật (RSI, MA, MACD, Volume)
        3. Đưa ra nhận xét và khuyến nghị rõ ràng
        4. Format đẹp với emoji để dễ đọc

        Tools có sẵn:
        - get_latest_price: Lấy giá và chỉ báo mới nhất của 1 cổ phiếu
        - get_price_history: Lấy lịch sử giá nhiều ngày
        - get_predictions: Lấy dự đoán 3 ngày tới
        - search_stocks: Tìm cổ phiếu theo tiêu chí (RSI, giá, volume)

        HÃY TỰ ĐỘNG GỌI TOOLS KHI CẦN!
        """

        logger.info("✅ Stock Analysis Agent V2 (Function Calling) initialized")

    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define tools schema cho Gemini Function Calling"""
        return [
            {
                "name": "get_latest_price",
                "description": "Lấy giá hiện tại và các chỉ báo kỹ thuật mới nhất của 1 cổ phiếu (close, open, high, low, volume, RSI, MA5, MA20, MACD)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {
                            "type": "string",
                            "description": "Mã cổ phiếu (VD: VCB, VNM, FPT)"
                        }
                    },
                    "required": ["ticker"]
                }
            },
            {
                "name": "get_price_history",
                "description": "Lấy lịch sử giá của cổ phiếu trong N ngày gần nhất để phân tích xu hướng",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {
                            "type": "string",
                            "description": "Mã cổ phiếu"
                        },
                        "days": {
                            "type": "integer",
                            "description": "Số ngày lịch sử cần lấy (mặc định 10)",
                            "default": 10
                        }
                    },
                    "required": ["ticker"]
                }
            },
            {
                "name": "get_predictions",
                "description": "Lấy dự đoán giá 3 ngày tới của cổ phiếu từ mô hình ML",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {
                            "type": "string",
                            "description": "Mã cổ phiếu"
                        }
                    },
                    "required": ["ticker"]
                }
            },
            {
                "name": "search_stocks",
                "description": "Tìm kiếm cổ phiếu theo tiêu chí kỹ thuật (RSI quá mua/quá bán, giá thấp/cao, volume lớn). Trả về danh sách cổ phiếu phù hợp.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "rsi_below": {
                            "type": "integer",
                            "description": "Tìm cổ phiếu có RSI dưới ngưỡng này (VD: 30 = oversold)"
                        },
                        "rsi_above": {
                            "type": "integer",
                            "description": "Tìm cổ phiếu có RSI trên ngưỡng này (VD: 70 = overbought)"
                        },
                        "price_below": {
                            "type": "number",
                            "description": "Tìm cổ phiếu có giá dưới mức này"
                        },
                        "price_above": {
                            "type": "number",
                            "description": "Tìm cổ phiếu có giá trên mức này"
                        }
                    }
                }
            }
        ]

    def _execute_function(self, function_name: str, args: Dict[str, Any]) -> Any:
        """Execute function call và trả về kết quả"""
        try:
            if function_name == "get_latest_price":
                result = self.db_tools.get_latest_price(args["ticker"])
                return result if result else {"error": f"Không tìm thấy dữ liệu cho {args['ticker']}"}

            elif function_name == "get_price_history":
                days = args.get("days", 10)
                result = self.db_tools.get_price_history(args["ticker"], days=days)
                return result if result else []

            elif function_name == "get_predictions":
                result = self.db_tools.get_predictions(args["ticker"])
                return result if result else {"error": "Không có dự đoán"}

            elif function_name == "search_stocks":
                criteria = {}
                if "rsi_below" in args:
                    criteria["rsi_below"] = args["rsi_below"]
                if "rsi_above" in args:
                    criteria["rsi_above"] = args["rsi_above"]
                if "price_below" in args:
                    criteria["price_below"] = args["price_below"]
                if "price_above" in args:
                    criteria["price_above"] = args["price_above"]

                result = self.db_tools.search_stocks_by_criteria(criteria)
                return result if result else []

            else:
                return {"error": f"Unknown function: {function_name}"}

        except Exception as e:
            logger.error(f"Error executing {function_name}: {e}")
            return {"error": str(e)}

    def chat_with_tools(self, message: str, max_iterations: int = 5) -> str:
        """
        Chat với AI, tự động xử lý function calling

        Args:
            message: Tin nhắn từ user
            max_iterations: Số lần tối đa cho phép AI gọi tools (tránh loop)

        Returns:
            str: Câu trả lời cuối cùng
        """
        try:
            # Khởi tạo chat session mới
            self.chat = self.model.start_chat(enable_automatic_function_calling=False)

            # Gửi message
            response = self.chat.send_message(message)

            iteration = 0
            while iteration < max_iterations:
                # Kiểm tra xem có function call không
                if not response.candidates[0].content.parts:
                    break

                # Lấy part đầu tiên
                part = response.candidates[0].content.parts[0]

                # Nếu không phải function call → trả lời xong
                if not hasattr(part, 'function_call') or not part.function_call:
                    break

                # Extract function call
                function_call = part.function_call
                function_name = function_call.name
                function_args = dict(function_call.args)

                logger.info(f"🔧 AI calls: {function_name}({function_args})")

                # Execute function
                function_result = self._execute_function(function_name, function_args)

                logger.info(f"✅ Function result: {json.dumps(function_result, ensure_ascii=False)[:200]}")

                # Gửi kết quả về cho AI
                response = self.chat.send_message(
                    genai.protos.Content(
                        parts=[
                            genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=function_name,
                                    response={"result": function_result}
                                )
                            )
                        ]
                    )
                )

                iteration += 1

            # Lấy response text cuối cùng
            if response.text:
                return response.text
            else:
                return "❌ Không thể tạo response. Vui lòng thử lại."

        except Exception as e:
            logger.error(f"Error in chat_with_tools: {e}", exc_info=True)
            error_msg = str(e)
            if "quota" in error_msg.lower() or "429" in error_msg:
                raise Exception("⚠️ API đã vượt quota. Vui lòng thử lại sau hoặc liên hệ admin.")
            raise Exception(f"Không thể trả lời: {str(e)}")

    def analyze_stock(self, ticker: str) -> str:
        """
        Phân tích cổ phiếu - AI tự gọi tools

        Args:
            ticker: Mã cổ phiếu

        Returns:
            str: Phân tích chi tiết
        """
        message = f"Hãy phân tích toàn diện cổ phiếu {ticker}. Hãy tự động lấy dữ liệu cần thiết (giá hiện tại, lịch sử, dự đoán) và đưa ra nhận xét."
        return self.chat_with_tools(message)

    def answer_question(self, question: str) -> str:
        """
        Trả lời câu hỏi - AI tự quyết định cần gọi tool nào

        Args:
            question: Câu hỏi từ user

        Returns:
            str: Câu trả lời
        """
        return self.chat_with_tools(question)

    def find_opportunities(self, criteria_text: str) -> str:
        """
        Tìm cơ hội đầu tư - AI tự hiểu và gọi search_stocks

        Args:
            criteria_text: Mô tả tiêu chí (VD: "tìm cổ phiếu RSI dưới 30")

        Returns:
            str: Danh sách cổ phiếu
        """
        message = f"Hãy tìm kiếm cổ phiếu theo tiêu chí sau: {criteria_text}"
        return self.chat_with_tools(message)

    def __del__(self):
        """Cleanup"""
        if hasattr(self, "db_tools"):
            self.db_tools.close()
