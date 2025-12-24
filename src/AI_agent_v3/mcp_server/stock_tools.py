"""
Stock Analysis Tools for MCP Server
Định nghĩa các tools để agent có thể sử dụng
"""

import logging
import sys
import os
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.AI_agent.database_tools import DatabaseTools

logger = logging.getLogger(__name__)


class StockToolsRegistry:
    """Registry quản lý tất cả stock analysis tools"""

    def __init__(self):
        self.db_tools = DatabaseTools()
        logger.info("✅ Stock Tools Registry initialized")

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Trả về schemas của tất cả tools"""
        return [
            {
                "name": "get_latest_price",
                "description": "Lấy giá và các chỉ báo kỹ thuật mới nhất của một cổ phiếu (close, open, high, low, volume, RSI, MA5, MA20, MACD)",
                "input_schema": {
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
                "input_schema": {
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
                "input_schema": {
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
                "description": "Tìm kiếm cổ phiếu theo tiêu chí kỹ thuật (RSI quá mua/quá bán, giá thấp/cao, volume lớn)",
                "input_schema": {
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

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute một tool với arguments

        Args:
            tool_name: Tên tool
            arguments: Dict chứa arguments

        Returns:
            Dict chứa kết quả hoặc error
        """
        try:
            logger.info(f"🔧 Executing tool: {tool_name} with args: {arguments}")

            if tool_name == "get_latest_price":
                return await self._handle_get_latest_price(**arguments)

            elif tool_name == "get_price_history":
                return await self._handle_get_price_history(**arguments)

            elif tool_name == "get_predictions":
                return await self._handle_get_predictions(**arguments)

            elif tool_name == "search_stocks":
                return await self._handle_search_stocks(**arguments)

            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }

        except Exception as e:
            logger.error(f"❌ Error executing {tool_name}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def _handle_get_latest_price(self, ticker: str) -> Dict[str, Any]:
        """Handler cho get_latest_price"""
        result = self.db_tools.get_latest_price(ticker)

        if result:
            return {
                "success": True,
                "data": result
            }
        else:
            return {
                "success": False,
                "error": f"Không tìm thấy dữ liệu cho {ticker}"
            }

    async def _handle_get_price_history(self, ticker: str, days: int = 10) -> Dict[str, Any]:
        """Handler cho get_price_history"""
        result = self.db_tools.get_price_history(ticker, days=days)

        if result:
            return {
                "success": True,
                "data": result
            }
        else:
            return {
                "success": False,
                "error": f"Không tìm thấy lịch sử giá cho {ticker}"
            }

    async def _handle_get_predictions(self, ticker: str) -> Dict[str, Any]:
        """Handler cho get_predictions"""
        result = self.db_tools.get_predictions(ticker)

        if result:
            return {
                "success": True,
                "data": result
            }
        else:
            return {
                "success": False,
                "error": f"Không có dự đoán cho {ticker}"
            }

    async def _handle_search_stocks(self, **criteria) -> Dict[str, Any]:
        """Handler cho search_stocks"""
        result = self.db_tools.search_stocks_by_criteria(criteria)

        if result:
            return {
                "success": True,
                "data": result,
                "count": len(result)
            }
        else:
            return {
                "success": True,
                "data": [],
                "count": 0,
                "message": "Không tìm thấy cổ phiếu phù hợp"
            }

    def close(self):
        """Cleanup resources"""
        if hasattr(self, 'db_tools'):
            self.db_tools.close()
