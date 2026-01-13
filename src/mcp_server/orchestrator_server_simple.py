"""
Simple MCP Server for Claude Desktop - Direct Tool Access
Provides direct access to stock market tools without multi-agent complexity
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
pythonpath_env = os.environ.get('PYTHONPATH', '')
if pythonpath_env and pythonpath_env not in sys.path:
    sys.path.insert(0, pythonpath_env)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
import logging
import json
from typing import Any, Optional
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field

# Import stock tools directly
try:
    from src.mcp_server.tools.stock_tools import (
        get_stock_data_mcp,
        get_stock_price_prediction_mcp,
        get_stock_details_from_tcbs_mcp
    )
    from src.mcp_server.tools.finance_tools import get_financial_data_mcp
    from src.mcp_server.tools.screener_tools import screen_stocks_mcp, get_screener_columns_mcp
    from src.mcp_server.tools.alert_tools import create_alert_mcp, get_user_alerts_mcp, delete_alert_mcp
    from src.mcp_server.tools.subscription_tools import create_subscription_mcp, get_user_subscriptions_mcp, delete_subscription_mcp
except ImportError as e:
    logging.error(f"Failed to import tools: {e}")
    raise

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server instance
app = Server("stock-market-simple-server")


# Tool schemas
class GetStockDataInput(BaseModel):
    """Get stock price data"""
    symbols: list[str] = Field(description="List of stock symbols (e.g., ['VCB', 'HPG'])")
    lookback_days: int = Field(default=30, description="Number of days to look back")


class GetStockPredictionInput(BaseModel):
    """Get stock price prediction"""
    symbols: list[str] = Field(description="List of stock ticker symbols (e.g., ['VCB', 'HPG'])")
    table_type: str = Field(default="3d", description="Prediction type: '3d' (3 days) or '48d' (48 days)")


class GetStockDetailsInput(BaseModel):
    """Get detailed stock information from TCBS"""
    symbols: list[str] = Field(description="List of stock ticker symbols (e.g., ['VCB', 'HPG'])")


class ScreenStocksInput(BaseModel):
    """Screen stocks by criteria"""
    filters: dict = Field(description="Filter criteria (e.g., {'roe': {'min': 15}, 'sector': 'Ngân hàng'})")
    limit: int = Field(default=20, description="Maximum number of results")


class GetFinancialDataInput(BaseModel):
    """Get financial data"""
    ticker: str = Field(description="Stock ticker symbol")
    report_type: str = Field(default="IncomeStatement", description="Type of report")
    period_type: str = Field(default="quarter", description="Period type (quarter/year)")


# Register tools
@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools"""
    return [
        Tool(
            name="get_stock_data",
            description="Lấy dữ liệu giá cổ phiếu lịch sử. Dùng để xem giá, volume, các chỉ báo kỹ thuật (MA, RSI, MACD, Bollinger Bands)",
            inputSchema=GetStockDataInput.model_json_schema()
        ),
        Tool(
            name="get_stock_prediction",
            description="Dự đoán giá cổ phiếu bằng AI. Sử dụng table_type='3d' cho dự đoán 3 ngày hoặc '48d' cho 48 ngày. Ensemble model (LSTM + ARIMA + XGBoost)",
            inputSchema=GetStockPredictionInput.model_json_schema()
        ),
        Tool(
            name="get_stock_details",
            description="Lấy thông tin chi tiết nhiều cổ phiếu từ TCBS: PE, PB, ROE, ROA, thông tin doanh nghiệp",
            inputSchema=GetStockDetailsInput.model_json_schema()
        ),
        Tool(
            name="screen_stocks",
            description="Lọc cổ phiếu theo tiêu chí: ROE, PE, sector, market_cap, v.v.",
            inputSchema=ScreenStocksInput.model_json_schema()
        ),
        Tool(
            name="get_financial_data",
            description="Lấy báo cáo tài chính: IncomeStatement, BalanceSheet, CashFlow",
            inputSchema=GetFinancialDataInput.model_json_schema()
        ),
    ]


# Handle tool calls
@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool execution"""
    logger.info(f"Tool called: {name} with arguments: {arguments}")

    try:
        if name == "get_stock_data":
            symbols = arguments.get("symbols", [])
            lookback_days = arguments.get("lookback_days", 30)

            result = await get_stock_data_mcp(symbols=symbols, lookback_days=lookback_days)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "get_stock_prediction":
            symbols = arguments.get("symbols", [])
            table_type = arguments.get("table_type", "3d")

            result = await get_stock_price_prediction_mcp(symbols=symbols, table_type=table_type)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "get_stock_details":
            symbols = arguments.get("symbols", [])

            result = await get_stock_details_from_tcbs_mcp(symbols=symbols)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "screen_stocks":
            filters = arguments.get("filters", {})
            limit = arguments.get("limit", 20)

            result = await screen_stocks_mcp(filters=filters, limit=limit)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "get_financial_data":
            ticker = arguments.get("ticker")
            report_type = arguments.get("report_type", "IncomeStatement")
            period_type = arguments.get("period_type", "quarter")

            result = await get_financial_data_mcp(
                ticker=ticker,
                report_type=report_type,
                period_type=period_type
            )
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        error_response = {
            "error": str(e),
            "tool": name,
            "type": type(e).__name__
        }
        return [TextContent(type="text", text=json.dumps(error_response, ensure_ascii=False, indent=2))]


async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        logger.info("Stock Market Simple MCP Server starting...")
        logger.info("Direct access to stock tools without multi-agent complexity")
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
