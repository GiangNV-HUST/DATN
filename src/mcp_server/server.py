"""
MCP Server for Stock Market Tools
Provides tools for stock data, predictions, alerts, and subscriptions via MCP protocol
"""
import sys
import os
import json
from pathlib import Path
import io

# IMPORTANT: Suppress stdout during imports to prevent vnstock welcome messages
# from breaking MCP JSON-RPC protocol
_original_stdout = sys.stdout
_original_stderr = sys.stderr
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()

# IMPORTANT: Add project root to sys.path FIRST, before any other imports
# This allows the script to run directly with absolute imports
project_root = Path(__file__).resolve().parent.parent.parent

# Also check PYTHONPATH env var
pythonpath_env = os.environ.get('PYTHONPATH', '')
if pythonpath_env and pythonpath_env not in sys.path:
    sys.path.insert(0, pythonpath_env)

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
import logging
from typing import Any, Optional
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field

# Import tools - try relative imports first, then absolute
try:
    from .tools.stock_tools import (
        get_stock_data_mcp,
        get_stock_price_prediction_mcp,
        generate_chart_from_data_mcp,
        get_stock_details_from_tcbs_mcp
    )
    from .tools.finance_tools import (
        get_financial_data_mcp
    )
    from .tools.screener_tools import (
        screen_stocks_mcp,
        get_screener_columns_mcp
    )
    from .tools.alert_tools import (
        create_alert_mcp,
        get_user_alerts_mcp,
        delete_alert_mcp
    )
    from .tools.subscription_tools import (
        create_subscription_mcp,
        get_user_subscriptions_mcp,
        delete_subscription_mcp
    )
    # Gemini tools disabled - not using Gemini anymore
    # from .tools.gemini_tools import (
    #     gemini_summarize_mcp,
    #     gemini_search_and_summarize_mcp,
    #     batch_summarize_mcp
    # )
    from .tools.investment_planning_tools import (
        gather_investment_profile,
        calculate_portfolio_allocation,
        generate_entry_strategy,
        generate_risk_management_plan,
        generate_monitoring_plan,
        generate_dca_plan
    )
    from .tools.stock_discovery_tools import (
        discover_stocks_by_profile,
        search_potential_stocks,
        filter_stocks_by_criteria,
        rank_stocks_by_score
    )
    from .tools.tcbs_tools import (
        get_company_overview_mcp,
        get_company_profile_mcp,
        get_financial_ratios_mcp,
        get_income_statement_mcp,
        get_balance_sheet_mcp,
        get_cash_flow_mcp,
        get_price_history_mcp,
        get_intraday_data_mcp,
        get_stock_full_info_mcp
    )
except ImportError:
    # Fallback to absolute imports when running as script
    from src.mcp_server.tools.stock_tools import (
        get_stock_data_mcp,
        get_stock_price_prediction_mcp,
        generate_chart_from_data_mcp,
        get_stock_details_from_tcbs_mcp
    )
    from src.mcp_server.tools.finance_tools import (
        get_financial_data_mcp
    )
    from src.mcp_server.tools.screener_tools import (
        screen_stocks_mcp,
        get_screener_columns_mcp
    )
    from src.mcp_server.tools.alert_tools import (
        create_alert_mcp,
        get_user_alerts_mcp,
        delete_alert_mcp
    )
    from src.mcp_server.tools.subscription_tools import (
        create_subscription_mcp,
        get_user_subscriptions_mcp,
        delete_subscription_mcp
    )
    # Gemini tools disabled - not using Gemini anymore
    # from src.mcp_server.tools.gemini_tools import (
    #     gemini_summarize_mcp,
    #     gemini_search_and_summarize_mcp,
    #     batch_summarize_mcp
    # )
    from src.mcp_server.tools.investment_planning_tools import (
        gather_investment_profile,
        calculate_portfolio_allocation,
        generate_entry_strategy,
        generate_risk_management_plan,
        generate_monitoring_plan,
        generate_dca_plan
    )
    from src.mcp_server.tools.stock_discovery_tools import (
        discover_stocks_by_profile,
        search_potential_stocks,
        filter_stocks_by_criteria,
        rank_stocks_by_score
    )
    from src.mcp_server.tools.tcbs_tools import (
        get_company_overview_mcp,
        get_company_profile_mcp,
        get_financial_ratios_mcp,
        get_income_statement_mcp,
        get_balance_sheet_mcp,
        get_cash_flow_mcp,
        get_price_history_mcp,
        get_intraday_data_mcp,
        get_stock_full_info_mcp
    )

# Restore stdout/stderr after all imports are done
sys.stdout = _original_stdout
sys.stderr = _original_stderr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server instance
app = Server("stock-market-mcp-server")


# Tool schemas using Pydantic
class GetStockDataInput(BaseModel):
    """Input schema for get_stock_data tool"""
    symbols: list[str] = Field(description="List of stock symbols (e.g., ['VCB', 'FPT'])")
    interval: str = Field(default="1D", description="Time interval (default: '1D')")
    lookback_days: Optional[int] = Field(default=None, description="Number of days to look back")
    start_date: Optional[str] = Field(default=None, description="Start date in format 'YYYY-MM-DD'")
    end_date: Optional[str] = Field(default=None, description="End date in format 'YYYY-MM-DD'")
    realtime: bool = Field(default=True, description="If True, try to get realtime/intraday price first (default: True). Set to False for historical data only.")


class GetStockPredictionInput(BaseModel):
    """Input schema for get_stock_price_prediction tool"""
    symbols: list[str] = Field(description="List of stock symbols")
    table_type: str = Field(description="Prediction type: '3d' or '48d'")


class GenerateChartInput(BaseModel):
    """Input schema for generate_chart_from_data tool"""
    symbols: list[str] = Field(description="List of stock symbols")
    interval: str = Field(default="1D", description="Time interval")
    lookback_days: int = Field(default=30, description="Number of days to look back for chart data")
    chart_type: str = Field(default="candlestick", description="Chart type: 'candlestick' or 'line'")


class CreateAlertInput(BaseModel):
    """Input schema for create_alert tool"""
    user_id: str = Field(description="User ID")
    symbol: str = Field(description="Stock symbol")
    alert_type: str = Field(description="Alert type (e.g., 'price', 'ma5')")
    target_value: float = Field(description="Target value for alert")
    condition: str = Field(description="Condition: 'above' or 'below'")


class GetUserAlertsInput(BaseModel):
    """Input schema for get_user_alerts tool"""
    user_id: str = Field(description="User ID")


class DeleteAlertInput(BaseModel):
    """Input schema for delete_alert tool"""
    user_id: str = Field(description="User ID")
    alert_id: int = Field(description="Alert ID to delete")


class CreateSubscriptionInput(BaseModel):
    """Input schema for create_subscription tool"""
    user_id: str = Field(description="User ID")
    symbol: str = Field(description="Stock symbol to subscribe to")


class GetUserSubscriptionsInput(BaseModel):
    """Input schema for get_user_subscriptions tool"""
    user_id: str = Field(description="User ID")


class DeleteSubscriptionInput(BaseModel):
    """Input schema for delete_subscription tool"""
    user_id: str = Field(description="User ID")
    subscription_id: int = Field(description="Subscription ID to delete")


class GeminiSummarizeInput(BaseModel):
    """Input schema for Gemini summarize tool"""
    prompt: str = Field(description="Prompt for summarization")
    data: dict = Field(description="Data to summarize")
    use_search: bool = Field(default=False, description="Whether to use Google Search")


class GeminiSearchInput(BaseModel):
    """Input schema for Gemini search and summarize tool"""
    query: str = Field(description="Search query")
    user_query: str = Field(description="User's question to answer")


class BatchSummarizeInput(BaseModel):
    """Input schema for batch summarize tool"""
    symbols_data: dict = Field(
        description="Dictionary mapping symbols to their data and config. Example: {'VCB': {'data': {...}, 'query': 'Analyze VCB', 'use_search': True}}"
    )
    general_query: str = Field(
        default="",
        description="General query to use if symbol doesn't have specific query"
    )


class GetFinancialDataInput(BaseModel):
    """Input schema for get_financial_data tool"""
    tickers: list[str] = Field(description="List of stock symbols")
    is_balance_sheet: bool = Field(default=False, description="Fetch balance sheet data")
    is_income_statement: bool = Field(default=False, description="Fetch income statement data")
    is_cash_flow: bool = Field(default=False, description="Fetch cash flow data")
    is_financial_ratios: bool = Field(default=False, description="Fetch financial ratios")
    period: str = Field(default="quarterly", description="Period type: 'quarterly' or 'yearly'")
    num_periods: int = Field(default=4, description="Number of periods to fetch")


class ScreenStocksInput(BaseModel):
    """Input schema for screen_stocks tool"""
    conditions: dict = Field(description="Dictionary of column:condition pairs (e.g. {'roe': '>15', 'pe': '<15'})")
    sort_by: str = Field(default="avg_trading_value_20d", description="Column to sort results by")
    ascending: bool = Field(default=False, description="Sort order (False = descending)")
    limit: int = Field(default=20, description="Maximum number of results to return")


# Investment Planning Tool Schemas
class GatherInvestmentProfileInput(BaseModel):
    """Input schema for gather_investment_profile tool"""
    goals: str = Field(default="growth", description="Investment goals: growth, income, preservation, balanced")
    risk_tolerance: str = Field(default="moderate", description="Risk tolerance: conservative, moderate, aggressive")
    timeframe: str = Field(default="medium-term", description="Timeframe: short-term, medium-term, long-term")
    capital: float = Field(default=100_000_000, description="Capital to invest in VND")


class CalculatePortfolioAllocationInput(BaseModel):
    """Input schema for calculate_portfolio_allocation tool"""
    stocks: list[dict] = Field(description="List of stock analysis results with scores/ratings")
    capital: float = Field(description="Total capital to invest")
    risk_tolerance: str = Field(default="moderate", description="Risk tolerance level")


class GenerateEntryStrategyInput(BaseModel):
    """Input schema for generate_entry_strategy tool"""
    stocks: list[dict] = Field(description="List of stocks with technical analysis data")
    timeframe: str = Field(default="medium-term", description="Investment timeframe")


class GenerateRiskManagementPlanInput(BaseModel):
    """Input schema for generate_risk_management_plan tool"""
    stocks: list[dict] = Field(description="List of stocks in portfolio")
    risk_tolerance: str = Field(default="moderate", description="User's risk tolerance")
    market_outlook: str = Field(default="neutral", description="Market outlook: bullish, neutral, bearish")
    industry_outlook: str = Field(default="neutral", description="Industry outlook")


class GenerateMonitoringPlanInput(BaseModel):
    """Input schema for generate_monitoring_plan tool"""
    stocks: list[dict] = Field(description="List of stocks in portfolio")
    timeframe: str = Field(default="medium-term", description="Investment timeframe")


class GenerateDCAPlanInput(BaseModel):
    """Input schema for generate_dca_plan tool"""
    symbol: str = Field(description="Stock symbol (e.g., VCB, FPT)")
    monthly_investment: float = Field(description="Monthly investment amount in VND")
    duration_months: int = Field(default=12, description="Number of months for DCA plan")
    current_price: Optional[float] = Field(default=None, description="Current stock price in VND (optional, auto-fetched if not provided)")
    price_trend: str = Field(default="neutral", description="Expected price trend: bullish, neutral, bearish")
    start_month: Optional[str] = Field(default=None, description="Starting month (e.g., '01/2025'), defaults to current month")


# Stock Discovery Tool Schemas
class DiscoverStocksByProfileInput(BaseModel):
    """Input schema for discover_stocks_by_profile tool"""
    investment_profile: dict = Field(description="Complete user investment profile")
    max_stocks: int = Field(default=5, description="Maximum number of stocks to recommend")


class SearchPotentialStocksInput(BaseModel):
    """Input schema for search_potential_stocks tool"""
    query: str = Field(description="Search query for finding stocks")
    investment_goal: str = Field(default="growth", description="User's investment goal")
    risk_tolerance: str = Field(default="moderate", description="User's risk tolerance")
    timeframe: str = Field(default="medium-term", description="Investment timeframe")
    max_results: int = Field(default=10, description="Maximum results")


class FilterStocksByCriteriaInput(BaseModel):
    """Input schema for filter_stocks_by_criteria tool"""
    symbols: list[str] = Field(description="List of stock symbols to filter")
    criteria: dict = Field(description="Filtering criteria")


class RankStocksByScoreInput(BaseModel):
    """Input schema for rank_stocks_by_score tool"""
    stocks: list[dict] = Field(description="List of stocks with metrics")
    ranking_method: str = Field(default="composite", description="Ranking method: composite, growth, value, momentum")


class GetStockDetailsFromTCBSInput(BaseModel):
    """Input schema for get_stock_details_from_tcbs tool"""
    symbols: list[str] = Field(description="List of stock symbols to get detailed TCBS data for")


# TCBS/VCI API Tool Schemas
class GetCompanyOverviewInput(BaseModel):
    """Input schema for get_company_overview tool"""
    symbol: str = Field(description="Stock symbol (e.g., VCB, FPT)")


class GetCompanyProfileInput(BaseModel):
    """Input schema for get_company_profile tool"""
    symbol: str = Field(description="Stock symbol")


class GetFinancialRatiosInput(BaseModel):
    """Input schema for get_financial_ratios tool"""
    symbol: str = Field(description="Stock symbol")
    period: str = Field(default="quarter", description="Period: 'quarter' or 'year'")
    num_periods: int = Field(default=8, description="Number of periods to fetch")


class GetIncomeStatementInput(BaseModel):
    """Input schema for get_income_statement tool"""
    symbol: str = Field(description="Stock symbol")
    period: str = Field(default="quarter", description="Period: 'quarter' or 'year'")
    num_periods: int = Field(default=4, description="Number of periods to fetch")


class GetBalanceSheetInput(BaseModel):
    """Input schema for get_balance_sheet tool"""
    symbol: str = Field(description="Stock symbol")
    period: str = Field(default="quarter", description="Period: 'quarter' or 'year'")
    num_periods: int = Field(default=4, description="Number of periods to fetch")


class GetCashFlowInput(BaseModel):
    """Input schema for get_cash_flow tool"""
    symbol: str = Field(description="Stock symbol")
    period: str = Field(default="quarter", description="Period: 'quarter' or 'year'")
    num_periods: int = Field(default=4, description="Number of periods to fetch")


class GetPriceHistoryInput(BaseModel):
    """Input schema for get_price_history tool"""
    symbol: str = Field(description="Stock symbol")
    start_date: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD)")
    lookback_days: int = Field(default=30, description="Days to look back if no start_date")


class GetIntradayDataInput(BaseModel):
    """Input schema for get_intraday_data tool"""
    symbol: str = Field(description="Stock symbol")


class GetStockFullInfoInput(BaseModel):
    """Input schema for get_stock_full_info tool"""
    symbol: str = Field(description="Stock symbol")


# Register tools
@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools"""
    return [
        # ==================== PRICE DATA TOOLS ====================
        # Source: Database (stock_prices_1d, stock_prices_1m) + API fallback
        Tool(
            name="get_stock_data",
            description="[DATABASE] Get stock price data with technical indicators (MA, RSI, MACD). Realtime from stock_prices_1m (updated every minute during trading hours). Historical from stock_prices_1d.",
            inputSchema=GetStockDataInput.model_json_schema()
        ),
        Tool(
            name="get_stock_price_prediction",
            description="[DATABASE] Get ML model predictions for stock prices (3-day or 48-day forecasts). Data from stock_prices_3d_predict and stock_prices_48d_predict tables.",
            inputSchema=GetStockPredictionInput.model_json_schema()
        ),
        Tool(
            name="generate_chart_from_data",
            description="[DATABASE] Generate stock charts using FastChartGenerator with template caching. First call ~1.5s, subsequent calls ~0.3-0.5s. Supports 'candlestick' and 'line' chart types.",
            inputSchema=GenerateChartInput.model_json_schema()
        ),
        Tool(
            name="get_stock_details_from_tcbs",
            description="[API] Get 70+ fields from TCBS screener: fundamentals, technicals, growth metrics. Best for comprehensive stock analysis.",
            inputSchema=GetStockDetailsFromTCBSInput.model_json_schema()
        ),
        # ==================== USER DATA TOOLS ====================
        # Source: Database (alerts, subscribe tables)
        Tool(
            name="create_alert",
            description="[DATABASE] Create a price alert for a stock. Stored in alerts table.",
            inputSchema=CreateAlertInput.model_json_schema()
        ),
        Tool(
            name="get_user_alerts",
            description="[DATABASE] Get all active alerts for a user.",
            inputSchema=GetUserAlertsInput.model_json_schema()
        ),
        Tool(
            name="delete_alert",
            description="[DATABASE] Delete/deactivate a specific alert.",
            inputSchema=DeleteAlertInput.model_json_schema()
        ),
        Tool(
            name="create_subscription",
            description="[DATABASE] Subscribe user to a stock symbol for daily updates.",
            inputSchema=CreateSubscriptionInput.model_json_schema()
        ),
        Tool(
            name="get_user_subscriptions",
            description="[DATABASE] Get all subscriptions for a user.",
            inputSchema=GetUserSubscriptionsInput.model_json_schema()
        ),
        Tool(
            name="delete_subscription",
            description="[DATABASE] Delete a subscription.",
            inputSchema=DeleteSubscriptionInput.model_json_schema()
        ),
        # ==================== FINANCIAL DATA TOOLS ====================
        # Source: API (VCI) primary, Database fallback
        Tool(
            name="get_financial_data",
            description="[API+DB] Get financial statements (balance sheet, income statement, cash flow, ratios). Primary: VCI API, Fallback: Database cache.",
            inputSchema=GetFinancialDataInput.model_json_schema()
        ),
        # ==================== SCREENER TOOLS ====================
        # Source: TCBS API primary, Database fallback
        Tool(
            name="screen_stocks",
            description="[API+DB] Screen Vietnamese stocks with 80+ columns (ROE, PE, RSI, MA, etc). Primary: TCBS API, Fallback: Database.",
            inputSchema=ScreenStocksInput.model_json_schema()
        ),
        Tool(
            name="get_screener_columns",
            description="[STATIC] Get list of available columns and operators for stock screening.",
            inputSchema={}
        ),
        # ==================== INVESTMENT PLANNING TOOLS ====================
        # Source: Logic/Calculation (no external data needed)
        Tool(
            name="gather_investment_profile",
            description="[LOGIC] Structure user investment profile: goals, risk tolerance, timeframe, capital.",
            inputSchema=GatherInvestmentProfileInput.model_json_schema()
        ),
        Tool(
            name="calculate_portfolio_allocation",
            description="[LOGIC] Calculate portfolio allocation based on stock analysis and risk tolerance.",
            inputSchema=CalculatePortfolioAllocationInput.model_json_schema()
        ),
        Tool(
            name="generate_entry_strategy",
            description="[LOGIC] Generate entry strategy: price points, timing, position sizing.",
            inputSchema=GenerateEntryStrategyInput.model_json_schema()
        ),
        Tool(
            name="generate_risk_management_plan",
            description="[LOGIC] Generate risk management: stop-loss, take-profit, position limits.",
            inputSchema=GenerateRiskManagementPlanInput.model_json_schema()
        ),
        Tool(
            name="generate_monitoring_plan",
            description="[LOGIC] Generate monitoring plan with key metrics to watch.",
            inputSchema=GenerateMonitoringPlanInput.model_json_schema()
        ),
        Tool(
            name="generate_dca_plan",
            description="[LOGIC] Generate DCA plan with monthly breakdown, projections. For periodic investment queries.",
            inputSchema=GenerateDCAPlanInput.model_json_schema()
        ),
        # ==================== STOCK DISCOVERY TOOLS ====================
        # Source: Logic + API for data
        Tool(
            name="discover_stocks_by_profile",
            description="[LOGIC+API] Discover stocks matching user investment profile.",
            inputSchema=DiscoverStocksByProfileInput.model_json_schema()
        ),
        Tool(
            name="search_potential_stocks",
            description="[LOGIC+API] Search potential stocks using criteria and web search.",
            inputSchema=SearchPotentialStocksInput.model_json_schema()
        ),
        Tool(
            name="filter_stocks_by_criteria",
            description="[LOGIC+API] Filter stocks by quantitative criteria (market cap, PE, ROE).",
            inputSchema=FilterStocksByCriteriaInput.model_json_schema()
        ),
        Tool(
            name="rank_stocks_by_score",
            description="[LOGIC] Rank stocks by composite score (growth, value, momentum).",
            inputSchema=RankStocksByScoreInput.model_json_schema()
        ),
        # ==================== VCI API TOOLS (Direct API calls) ====================
        # Source: VCI API - Always fetches latest data
        Tool(
            name="get_company_overview",
            description="[API] Get company overview: industry, market cap, shares from VCI.",
            inputSchema=GetCompanyOverviewInput.model_json_schema()
        ),
        Tool(
            name="get_company_profile",
            description="[API] Get detailed company profile from VCI.",
            inputSchema=GetCompanyProfileInput.model_json_schema()
        ),
        Tool(
            name="get_financial_ratios",
            description="[API] Get financial ratios (ROE, ROA, PE, PB) from VCI. Use for quick ratio lookup.",
            inputSchema=GetFinancialRatiosInput.model_json_schema()
        ),
        Tool(
            name="get_income_statement",
            description="[API] Get income statement (revenue, profit) from VCI. Single ticker quick lookup.",
            inputSchema=GetIncomeStatementInput.model_json_schema()
        ),
        Tool(
            name="get_balance_sheet",
            description="[API] Get balance sheet (assets, liabilities) from VCI. Single ticker quick lookup.",
            inputSchema=GetBalanceSheetInput.model_json_schema()
        ),
        Tool(
            name="get_cash_flow",
            description="[API] Get cash flow statement from VCI. Single ticker quick lookup.",
            inputSchema=GetCashFlowInput.model_json_schema()
        ),
        Tool(
            name="get_price_history",
            description="[API] Get historical OHLCV from VCI. Use for flexible date ranges not in database.",
            inputSchema=GetPriceHistoryInput.model_json_schema()
        ),
        Tool(
            name="get_intraday_data",
            description="[API] Get today's intraday trading data from VCI. Real-time tick data.",
            inputSchema=GetIntradayDataInput.model_json_schema()
        ),
        Tool(
            name="get_stock_full_info",
            description="[API] Get comprehensive info: overview + ratios + price history combined.",
            inputSchema=GetStockFullInfoInput.model_json_schema()
        ),
    ]


# Handle tool calls
@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool execution"""
    logger.info(f"Tool called: {name} with arguments: {arguments}")

    try:
        # Stock data tools
        if name == "get_stock_data":
            result = await get_stock_data_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "get_stock_price_prediction":
            result = await get_stock_price_prediction_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "generate_chart_from_data":
            result = await generate_chart_from_data_mcp(**arguments)

            # Return ImageContent for each generated chart
            contents = []
            if result.get("status") in ["success", "partial_success"]:
                for symbol, chart_data in result.get("results", {}).items():
                    if chart_data.get("status") == "success" and chart_data.get("chart_path"):
                        chart_path = chart_data["chart_path"]
                        try:
                            import base64
                            with open(chart_path, "rb") as f:
                                image_data = base64.standard_b64encode(f.read()).decode("utf-8")
                            contents.append(ImageContent(
                                type="image",
                                data=image_data,
                                mimeType="image/png"
                            ))
                            contents.append(TextContent(
                                type="text",
                                text=f"Chart for {symbol} generated successfully."
                            ))
                        except Exception as e:
                            contents.append(TextContent(
                                type="text",
                                text=f"Error reading chart for {symbol}: {str(e)}"
                            ))
                    else:
                        contents.append(TextContent(
                            type="text",
                            text=f"Failed to generate chart for {symbol}: {chart_data.get('message', 'Unknown error')}"
                        ))
            else:
                contents.append(TextContent(type="text", text=str(result)))

            return contents if contents else [TextContent(type="text", text=str(result))]

        elif name == "get_stock_details_from_tcbs":
            result = await get_stock_details_from_tcbs_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        # Alert tools
        elif name == "create_alert":
            result = await create_alert_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "get_user_alerts":
            result = await get_user_alerts_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "delete_alert":
            result = await delete_alert_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        # Subscription tools
        elif name == "create_subscription":
            result = await create_subscription_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "get_user_subscriptions":
            result = await get_user_subscriptions_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "delete_subscription":
            result = await delete_subscription_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        # Gemini AI tools - DISABLED (not using Gemini anymore)
        # elif name == "gemini_summarize":
        #     result = await gemini_summarize_mcp(**arguments)
        #     return [TextContent(type="text", text=str(result))]

        # elif name == "gemini_search_and_summarize":
        #     result = await gemini_search_and_summarize_mcp(**arguments)
        #     return [TextContent(type="text", text=str(result))]

        # elif name == "batch_summarize":
        #     result = await batch_summarize_mcp(**arguments)
        #     return [TextContent(type="text", text=str(result))]

        # Financial data tools
        elif name == "get_financial_data":
            result = await get_financial_data_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        # Screener tools
        elif name == "screen_stocks":
            result = await screen_stocks_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "get_screener_columns":
            result = await get_screener_columns_mcp()
            return [TextContent(type="text", text=str(result))]

        # Investment Planning tools
        elif name == "gather_investment_profile":
            result = await gather_investment_profile(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "calculate_portfolio_allocation":
            result = await calculate_portfolio_allocation(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "generate_entry_strategy":
            result = await generate_entry_strategy(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "generate_risk_management_plan":
            result = await generate_risk_management_plan(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "generate_monitoring_plan":
            result = await generate_monitoring_plan(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "generate_dca_plan":
            result = await generate_dca_plan(**arguments)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        # Stock Discovery tools
        elif name == "discover_stocks_by_profile":
            result = await discover_stocks_by_profile(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "search_potential_stocks":
            result = await search_potential_stocks(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "filter_stocks_by_criteria":
            result = await filter_stocks_by_criteria(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "rank_stocks_by_score":
            result = await rank_stocks_by_score(**arguments)
            return [TextContent(type="text", text=str(result))]

        # TCBS/VCI API Tools
        elif name == "get_company_overview":
            result = await get_company_overview_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "get_company_profile":
            result = await get_company_profile_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "get_financial_ratios":
            result = await get_financial_ratios_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "get_income_statement":
            result = await get_income_statement_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "get_balance_sheet":
            result = await get_balance_sheet_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "get_cash_flow":
            result = await get_cash_flow_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "get_price_history":
            result = await get_price_history_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "get_intraday_data":
            result = await get_intraday_data_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "get_stock_full_info":
            result = await get_stock_full_info_mcp(**arguments)
            return [TextContent(type="text", text=str(result))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        logger.info("Stock Market MCP Server starting...")
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
